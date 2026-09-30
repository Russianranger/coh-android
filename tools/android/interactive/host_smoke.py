#!/usr/bin/env python3
"""Exercise real client menu input through the exact APK and private RFB."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, platform, secrets, shutil
import re, signal, socket, stat, struct, subprocess, sys, time, zipfile, zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m
assets_tool=load('interactive_client_assets_host',Path(__file__).with_name('prepare_assets.py'))
apk_tool=load('interactive_client_apk_host',Path(__file__).with_name('build_apk.py'))
transport=load('accepted_presentation_transport_host',ROOT/'tools/android/presentation/host_smoke.py')
require,digest=assets_tool.require,assets_tool.digest
WIDTH,HEIGHT=800,600
MAX_WIDTH,MAX_HEIGHT=1024,768
DESKTOP_SIZE=-223


def extract_apk_assets(apk,output,build_report,commit):
    report=assets_tool.read_json(build_report)
    require(report.get('repository_commit')==commit and report.get('application_id')==apk_tool.APP_ID
            and report.get('version_name')==apk_tool.VERSION_NAME and report.get('signature_verified') is True
            and report.get('payload_bytes_verified') is True
            and {'bytes':report.get('bytes'),'sha256':report.get('sha256')}==apk_tool.file_pin(apk),
            'Exact client APK receipt differs')
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        sources=apk_tool.java_sources(ROOT/'android/interactive/src/main',Path(tmp))
    require(report.get('java_sources')=={p.relative_to(ROOT).as_posix():apk_tool.file_pin(p) for p in sources},
            'APK Java source bytes differ')
    require(report.get('native_launcher_source')=={'android/native/client-launcher.c':apk_tool.file_pin(ROOT/'android/native/client-launcher.c')},
            'APK native launcher source differs')
    apk_tool.verify_packaged_payloads(apk,report['payloads'])
    require(not output.exists(),'Fresh extraction required');output.mkdir(parents=True)
    runtime,imports=output/'runtime',output/'atlas';runtime.mkdir();imports.mkdir()
    with zipfile.ZipFile(apk) as archive:
        for name,pin in report['payloads'].items():
            if not name.startswith('assets/'):continue
            require(name.startswith(('assets/runtime/','assets/atlas/')),'Unexpected asset prefix')
            target=(runtime if name.startswith('assets/runtime/') else imports)/Path(name).name
            require(name.count('/')==2 and target.name not in ('.','..'),'Unsafe asset path')
            with archive.open(name) as source,target.open('xb') as dest:shutil.copyfileobj(source,dest,1024*1024)
    manifest=assets_tool.verify_device_assets(runtime,repository_commit=commit)
    apk_tool.verify_import_package(imports)
    return manifest,runtime,imports


def import_game_data(imports,archive,work,evidence):
    contract=apk_tool.verify_import_package(imports)
    require(apk_tool.file_pin(archive)=={'bytes':contract['asset.archive.bytes'],'sha256':contract['asset.archive.sha256']},
            'Reviewed game asset ZIP differs')
    classes=work/'import-classes';classes.mkdir()
    core=ROOT/'android/atlas/src/main/java/io/github/russianranger/cohatlas/AtlasAssetImporter.java'
    host=ROOT/'tools/android/atlas/java/io/github/russianranger/cohatlas/HostImport.java'
    with (evidence/'host-import.log').open('w') as log:
        subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','--release','8','-d',str(classes),str(core),str(host)],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=120)
        subprocess.run(['java','-Xmx512m','-cp',str(classes),'io.github.russianranger.cohatlas.HostImport',
                        str(imports),str(archive),str(work/'imported'),str(evidence/'import-summary.properties')],
                       check=True,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
    properties={line.split('=',1)[0]:line.split('=',1)[1] for line in (evidence/'import-summary.properties').read_text().splitlines() if '=' in line}
    require(properties.get('status')=='passed' and properties.get('repository.commit')==apk_tool.IMPORT_COMMIT
            and properties.get('count')==str(contract['total.count']) and properties.get('bytes')==str(contract['total.bytes']),
            'Host Java import receipt differs')
    data=Path(properties['data.directory']).resolve()
    require(data.name=='data' and (work/'imported') in data.parents,'Imported data escaped private destination')
    return data


def save_png(path,pixels,width=WIDTH,height=HEIGHT):
    # Raw RFB is little-endian BGRX; encode a bounded RGB PNG without Pillow.
    require(0<width<=MAX_WIDTH and 0<height<=MAX_HEIGHT and len(pixels)==width*height*4,
            'Invalid bounded PNG framebuffer')
    rows=bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            offset=(y*width+x)*4;rows.extend((pixels[offset+2],pixels[offset+1],pixels[offset]))
    def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    data=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(rows,6))+chunk(b'IEND',b'')
    path.write_bytes(data)


def client_rfb_handshake(connection):
    desktop=transport.rfb_handshake(connection)
    # Keep the accepted shared transport unchanged. The actual client can issue
    # a fullscreen mode event, so advertise the same bounded resize as Android.
    connection.sendall(struct.pack('!BBHii',2,0,2,0,DESKTOP_SIZE))
    return desktop


class ClientFramebuffer:
    def __init__(self):
        self.generation=0
        self.resize(WIDTH,HEIGHT)

    def resize(self,width,height):
        require(0<width<=MAX_WIDTH and 0<height<=MAX_HEIGHT,'RFB framebuffer size exceeds bounds')
        self.width,self.height=width,height
        self.pixels=bytearray(width*height*4)
        self.generation+=1
        self.fresh=False
        self.updates=0

    def read_update(self,connection):
        count=struct.unpack_from('!H',transport.recv_exact(connection,3),1)[0]
        require(count<=1024,'Invalid RFB rectangle count')
        changed=resized=False
        for index in range(count):
            x,y,w,h,encoding=struct.unpack('!HHHHi',transport.recv_exact(connection,12))
            if encoding==DESKTOP_SIZE:
                require(x==0 and y==0 and index==count-1,'Invalid RFB desktop-size rectangle')
                self.resize(w,h)
                changed=False # Discard every old-size rectangle in this update.
                resized=True
            else:
                require(encoding==0 and w>0 and h>0 and x+w<=self.width and y+h<=self.height,
                        'Invalid RFB rectangle')
                # Row reads retain the accepted transport's read bound even at
                # the Android maximum 1024x768 intermediate desktop size.
                for row in range(h):
                    start=((y+row)*self.width+x)*4
                    self.pixels[start:start+w*4]=transport.recv_exact(connection,w*4)
                changed=True
        if changed:
            self.fresh=True
            self.updates+=1
        return changed,resized


class ClientEvents:
    """Read only complete, bounded guest event lines from this host invocation."""
    def __init__(self,path,session):
        self.path,self.session=path,session
        self.offset=0
        self.pending=b''
        self.generation=0
        self.client_pid=None
        self.active=self.terminal=False

    def poll(self):
        with self.path.open('rb') as source:
            source.seek(self.offset)
            data=source.read(131072)
        self.offset+=len(data)
        require(self.offset<=2*1024*1024,'Host guest-event stream exceeds bound')
        lines=(self.pending+data).split(b'\n')
        self.pending=lines.pop()
        require(len(self.pending)<=65536,'Host guest-event line exceeds bound')
        for line in lines:
            require(len(line)<=65536,'Host guest-event line exceeds bound')
            try:event=json.loads(line)
            except (ValueError,UnicodeDecodeError):continue
            if not isinstance(event,dict):continue
            if event.get('type')=='client_interaction_ready' and event.get('session_id')==self.session:
                pid=event.get('client_pid')
                require(type(pid) is int and pid>0,'Invalid startup event client PID')
                require(not self.terminal,'Startup event followed terminal completion')
                self.client_pid=pid
                self.generation+=1
                self.active=True
            elif event.get('type')=='stage' and event.get('stage')=='actual_client_interaction' and event.get('status')=='passed':
                require(self.client_pid is not None,'Client completion preceded readiness event')
                self.active=False
                self.terminal=True


def pointer_click(connection,x,y):
    require(type(x) is int and type(y) is int and 0<=x<WIDTH and 0<=y<HEIGHT,
            'Host interaction pointer is outside the actual client viewport')
    connection.sendall(struct.pack('!BBHH',5,1,x,y))
    time.sleep(.12)
    connection.sendall(struct.pack('!BBHH',5,0,x,y))


def type_test_marker(connection):
    # This literal is a visible, non-secret transport fixture, never credentials.
    for key in 'COHINPUT':
        connection.sendall(struct.pack('!BBHI',4,1,0,ord(key)))
        time.sleep(.03)
        connection.sendall(struct.pack('!BBHI',4,0,0,ord(key)))
        time.sleep(.03)


def write_finish_request(path,session,pid):
    require(re.fullmatch(r'[0-9a-f]{32}',session) and type(pid) is int and pid>0,
            'Host finish request has no exact client identity')
    require(path.parent.is_dir() and not path.parent.is_symlink() and not path.exists() and not path.is_symlink(),
            'Host finish request destination is not fresh and private')
    value={'format':1,'session_id':session,'client_pid':pid,'action':'finish_interaction'}
    payload=(json.dumps(value,sort_keys=True)+'\n').encode()
    temporary=path.with_name(path.name+'.tmp-'+secrets.token_hex(8))
    try:
        with temporary.open('xb') as output:
            os.chmod(temporary,0o600);output.write(payload);output.flush();os.fsync(output.fileno())
        os.replace(temporary,path)
    finally:temporary.unlink(missing_ok=True)
    return dict(value,bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())


class MenuInteraction:
    """Fixed non-login script; observed UI effects require separate visual review."""
    def __init__(self,session,evidence,finish_path):
        self.session,self.evidence,self.finish_path=session,evidence,finish_path
        self.ready_at=None
        self.action=0
        self.last_action_at=0
        self.watermark=0
        self.result={'scope':'host_rfb_pointer_keyboard_delivery','input_effect_verified':False,
                     'script_completed':False,'test_marker':'COHINPUT','steps':[],'screenshots':[]}

    def capture(self,label,frame,events,sequence,now):
        path=self.evidence/(label+'.png');save_png(path,frame.pixels)
        self.result['screenshots'].append({'file':path.name,'png_sha256':digest(path),
            'frame_sha256':hashlib.sha256(frame.pixels).hexdigest(),'frame_sequence':sequence,
            'frame_generation':frame.generation,'session_id':self.session,'client_pid':events.client_pid,
            'width':WIDTH,'height':HEIGHT,'elapsed_since_ready':round(now-self.ready_at,3)})

    def on_frame(self,connection,frame,events,sequence,captures,now):
        if self.ready_at is None:self.ready_at=now
        if len(captures)<3 or (frame.width,frame.height)!=(WIDTH,HEIGHT):return
        if self.action and (now-self.last_action_at<1 or sequence<=self.watermark):return
        if self.action==0:
            self.capture('interaction-before-input',frame,events,sequence,now)
            pointer_click(connection,400,403) # Cancel the first-start graphics prompt.
            name='cancel_graphics_prompt';self.action=1
        elif self.action==1:
            self.capture('interaction-after-cancel',frame,events,sequence,now)
            pointer_click(connection,625,240)
            type_test_marker(connection)
            name='type_visible_test_marker';self.action=2
        elif self.action==2:
            self.capture('interaction-after-text',frame,events,sequence,now)
            pointer_click(connection,635,430)
            name='open_login_settings';self.action=3
        elif self.action==3:
            self.capture('interaction-settings',frame,events,sequence,now)
            self.result['script_completed']=True
            self.action=4
            return
        else:
            if now-self.ready_at>=30 and 'finish_request' not in self.result:
                self.result['finish_request']=write_finish_request(self.finish_path,self.session,events.client_pid)
            return
        self.watermark=sequence;self.last_action_at=time.monotonic()
        self.result['steps'].append({'action':name,'session_id':self.session,'client_pid':events.client_pid,
            'after_frame_sequence':sequence,'elapsed_since_ready':round(now-self.ready_at,3)})


def observe_rfb(connection,session,process,deadline,evidence,event_path,finish_path):
    desktop=client_rfb_handshake(connection);frame=ClientFramebuffer()
    updates=0;fingerprints=[];snapshots=[];last_capture=0;terminal=None;started=time.monotonic()
    resizes=[];events=ClientEvents(event_path,session);captures=[];event_generation=0
    pending_request=False;request_generation=0;failure=None
    interaction=MenuInteraction(session,evidence,finish_path)
    while process.poll() is None and time.monotonic()<deadline:
        try:
            events.poll()
            if events.generation!=event_generation:
                captures=[];event_generation=events.generation
                require(event_generation==1,'Unexpected repeated interaction readiness')
            if not pending_request:
                connection.sendall(struct.pack('!BBHHHH',3,0,0,0,frame.width,frame.height))
                request_generation=events.generation if events.active else 0
                pending_request=True
            kind=transport.recv_exact(connection,1)[0]
            if kind==2:continue
            if kind==3:
                header=transport.recv_exact(connection,7);size=struct.unpack_from('!I',header,3)[0]
                require(size<=4096,'Oversized cut text');transport.recv_exact(connection,size);continue
            require(kind==0,'Unexpected RFB message')
            changed,resized=frame.read_update(connection)
            pending_request=False
            events.poll()
            if events.generation!=event_generation:
                captures=[];event_generation=events.generation
                require(event_generation==1,'Unexpected repeated interaction readiness')
            if resized:
                require(len(resizes)<64,'RFB desktop-size event count exceeds bound')
                resizes.append({'width':frame.width,'height':frame.height,'generation':frame.generation,
                                'elapsed_seconds':round(time.monotonic()-started,3)})
                if not events.terminal:captures=[]
            if not changed:continue
            updates+=1;sha=hashlib.sha256(frame.pixels).hexdigest()
            if sha not in fingerprints and len(fingerprints)<2000:fingerprints.append(sha)
            now=time.monotonic()
            if (events.active and request_generation==events.generation and request_generation>0
                    and (frame.width,frame.height)==(WIDTH,HEIGHT) and len(captures)<3
                    and (not captures or now-started-captures[-1]['elapsed_seconds']>=1)):
                colors=set()
                for offset in range(0,len(frame.pixels),4):
                    colors.add(bytes(frame.pixels[offset:offset+3]))
                    if len(colors)>=8:break
                if len(colors)>=8:
                    name=f'client-startup-external-{len(captures):03d}.png'
                    save_png(evidence/name,frame.pixels)
                    captures.append({'file':name,'elapsed_seconds':now-started,'frame_sha256':sha,
                        'png_sha256':digest(evidence/name),'session_id':session,'client_pid':events.client_pid,
                        'width':WIDTH,'height':HEIGHT,'distinct_colors_capped':len(colors),
                        'frame_sequence':updates,'frame_generation':frame.generation,
                        'event_generation':events.generation})
            if events.active and request_generation==events.generation and request_generation>0:
                interaction.on_frame(connection,frame,events,updates,captures,now)
            if now-last_capture>=20 and len(snapshots)<60:
                name=f'client-frame-{len(snapshots):03d}.png';save_png(evidence/name,frame.pixels,frame.width,frame.height)
                snapshots.append({'file':name,'elapsed_seconds':round(now-started,3),'frame_sha256':sha,
                                  'width':frame.width,'height':frame.height,'generation':frame.generation});last_capture=now
            time.sleep(0.5)
        except (EOFError,BrokenPipeError,ConnectionResetError) as error:
            terminal=type(error).__name__
            # X closes during ordinary guest cleanup; event output may arrive
            # just after the socket EOF. Match the Android two-second allowance.
            terminal_deadline=min(deadline,time.monotonic()+2)
            while not events.terminal and time.monotonic()<terminal_deadline:
                events.poll()
                if not events.terminal:time.sleep(.05)
            if not events.terminal:failure='Private RFB transport ended before client startup observation completed'
            break
    events.poll()
    if frame.fresh:save_png(evidence/'client-frame-final.png',frame.pixels,frame.width,frame.height)
    return {'scope':'host_external_unix_rfb_actual_client_interaction','desktop':desktop,'session_id':session,'updates':updates,
            'distinct_frame_sha256':fingerprints,'snapshots':snapshots,'terminal_transport':terminal,
            'desktop_size_events':resizes,'final_frame':{'width':frame.width,'height':frame.height,
                'generation':frame.generation,'fresh_after_resize':frame.fresh,'updates_after_resize':frame.updates},
            'post_startup_captures':captures,'client_pid':events.client_pid,'terminal_event_observed':events.terminal,
            'failure':failure,
            'interaction_script':interaction.result,
            'connected_outside_proot':True,'android_surface_validated':False,'gameplay_validated':False}


def make_command(work,assets,proot,session,data,startup_timeout_seconds=900):
    require(type(startup_timeout_seconds) is int and 120<=startup_timeout_seconds<=900,
            "Host client startup timeout must be 120 to 900 seconds")
    command,env=transport.make_command(work,assets,proot,session)
    command[command.index('/opt/coh/presentation_diagnostic.py')]='/opt/coh/client_interactive_diagnostic.py'
    where=command.index('--duration-seconds');del command[where:where+2]
    (work/'rootfs/game-import').mkdir()
    where=command.index('-w');command[where:where]=['-b',str(data.parent)+':/game-import']
    command+=['--game-data','/game-import/data','--startup-timeout-seconds',str(startup_timeout_seconds),'--observation-seconds','30','--interaction-seconds','180']
    if '--timeout-seconds' in command:
        command[command.index('--timeout-seconds')+1]='1800'
    else:
        command+=['--timeout-seconds','1800']
    return command,env


def validate_report(report,session,manifest=None):
    require(report.get('scope')=='actual_client_interaction_guest' and report.get('session_id')==session,'Wrong client session report')
    require(report.get('diagnostic_mode')=='actual_client_interaction'
            and report.get('interaction_session_completed') is True and report.get('input_effect_verified') is False
            and report.get('interaction_completion_reason') in ('finish_requested','interaction_timeout')
            and 30<=report.get('observation_seconds',0)<=190
            and 0<=report.get('startup_elapsed_seconds',-1)<=900,
            'Interactive session evidence or bounds differ')
    require(report.get('passed') is True and report.get('status')=='passed' and report.get('failures')==[], 'Actual client startup did not complete')
    require(report.get('cleanup_complete') is True and report.get('wine_process_cleanup',{}).get('complete') is True
            and report.get('wine_process_cleanup',{}).get('remaining')==0
            and report.get('wine_process_cleanup',{}).get('inspection_failures')==0,'Client cleanup incomplete')
    require(report.get('postgres_started') is False and report.get('gameplay_validated') is False,'Unexpected server/gameplay claim')
    require(report.get('server_started') is False and report.get('client_process_started') is True
            and report.get('startup_observed') is True and report.get('renderer_initialized') is True
            and report.get('all_data_loaded') is True and report.get('client_main_loop_reached') is True
            and report.get('client_window_observed') is True and report.get('observation_seconds',0)>=30,
            'Actual client renderer, main loop, window or live observation evidence missing')
    launch=report.get('client_launch',{})
    require(launch.get('session_id')==session and type(launch.get('pid')) is int and launch['pid']>0,
            'Actual client process session differs')
    stages=report.get('stages',[])
    require([s.get('stage') for s in stages]==['client_inputs','client_private_data','presentation_display',
            'wine_initialization','win32_runtime_dll','actual_client_startup','actual_client_interaction']
            and all(s.get('status')=='passed' for s in stages),'Client startup stages incomplete')
    children=report.get('processes',[])
    require(len(children)>=5 and all(type(c.get('exit_code')) is int and c.get('input_closed') is True
            and c.get('output_capture_closed') is True for c in children),'Client owned children did not close')
    execution=report.get('cleanup_execution',{})
    require(execution.get('diagnostic_initialized') is True and execution.get('wine_started') is True
            and execution.get('owned_child_count')==len(children),'Client cleanup ownership record differs')
    for label in ('actual-coh-client','runtime-probe','private-presentation-x'):
        matching=[child for child in children if child.get('label')==label]
        require(len(matching)==1,'Missing or duplicate required client child: '+label)
        if label=='runtime-probe':require(matching[0]['exit_code']==0,'Runtime prerequisite failed')
    require(report.get('cleanup',{}).get('wine_prefix_stopped') is True
            and report.get('cleanup',{}).get('owned_processes_reaped') is True
            and report.get('presentation_socket_removed') is True,'Client display ownership cleanup incomplete')
    if manifest is not None:
        expected={name:manifest['files'][name]['sha256'] for name in assets_tool.PROBE_FILES}
        require(report.get('asset_sha256')==expected,'Client guest input hashes differ')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('apk','build-report','proot','work','evidence','archive'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--repository-commit',required=True)
    parser.add_argument('--startup-timeout-seconds',type=int,default=900,choices=range(120,901),metavar='120..900',
                        help='Host-only actual client startup bound; observation and acceptance are unchanged')
    args=parser.parse_args()
    require(platform.machine().lower() in ('aarch64','arm64'),'Native ARM64 Linux required')
    require(not args.work.exists(),'Fresh private smoke work required')
    args.work=args.work.resolve();args.proot=args.proot.resolve();args.evidence=args.evidence.resolve()
    args.work.mkdir(parents=True);args.evidence.mkdir(parents=True,exist_ok=True)
    manifest,assets,imports=extract_apk_assets(args.apk,args.work/'apk-assets',args.build_report,args.repository_commit)
    data=import_game_data(imports,args.archive.resolve(),args.work,args.evidence)
    session=secrets.token_hex(16);command,env=make_command(args.work,assets,args.proot,session,data,args.startup_timeout_seconds)
    start=time.monotonic();deadline=start+1860;observer=None;failure=None;process=None
    with (args.evidence/'host-client.log').open('w') as log:
        try:
            process=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            socket_path=args.work/'socket/view.sock'
            while not socket_path.exists():
                require(process.poll() is None and time.monotonic()<deadline,'Guest exited before display socket');time.sleep(0.1)
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
                connection.settimeout(90);connection.connect(str(socket_path))
                observer=observe_rfb(connection,session,process,deadline,args.evidence,args.evidence/'host-client.log',args.work/'state/interaction-finish.json')
            require(observer['failure'] is None,observer['failure'] or 'External client observer failed')
            code=process.wait(timeout=max(1,deadline-time.monotonic()))
            require(code==0,'Client guest exited unsuccessfully')
            report=json.loads((args.work/'state/latest-report.json').read_text());validate_report(report,session,manifest)
            require(observer['failure'] is None and observer['terminal_event_observed'] is True,
                    observer['failure'] or 'Missing external-observer terminal event')
            require(observer['updates']>=2 and len(observer['distinct_frame_sha256'])>=2,'Actual client did not change the display')
            captures=observer['post_startup_captures']
            require(observer['client_pid']==report['client_launch']['pid'] and len(captures)==3
                    and all(c['width']==WIDTH and c['height']==HEIGHT
                            and c['frame_generation']==captures[0]['frame_generation']
                            and c['event_generation']==captures[0]['event_generation'] for c in captures)
                    and captures[-1]['elapsed_seconds']-captures[0]['elapsed_seconds']>=2,
                    'Missing three session-bound fresh external startup frames')
            script=observer['interaction_script']
            require(script['script_completed'] is True and len(script['steps'])==3
                    and len(script['screenshots'])==4 and script.get('finish_request',{}).get('client_pid')==observer['client_pid']
                    and report['interaction_completion_reason']=='finish_requested',
                    'Host menu input script or its session-bound completion did not finish')
            require(not socket_path.exists(),'Private RFB socket survived cleanup')
        except Exception as error:
            failure={'type':type(error).__name__,'message':str(error)};raise
        finally:
            if process is not None and process.poll() is None:
                (args.work/'state/stop-request').write_text('stop\n')
                try:process.wait(timeout=35)
                except subprocess.TimeoutExpired:
                    process.send_signal(signal.SIGQUIT)
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            for name in ('latest-report.json','report.zip'):
                source=args.work/'state'/name
                if source.is_file():shutil.copyfile(source,args.evidence/name)
            result={'format':1,'status':'failed' if failure else 'passed','scope':'exact_apk_actual_client_interaction_native_arm64',
                    'repository_commit':args.repository_commit,'apk_sha256':digest(args.apk),
                    'runtime_manifest_sha256':digest(assets/'runtime-manifest.json'),'import_donor':apk_tool.import_donor(),
                    'session_id':session,'startup_timeout_seconds':args.startup_timeout_seconds,
                    'external_observer':observer,'failure':failure,'elapsed_seconds':round(time.monotonic()-start,3),
                    'android_execution_validated':False,'android_surface_validated':False,'gameplay_validated':False}
            (args.evidence/'host-client-report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
