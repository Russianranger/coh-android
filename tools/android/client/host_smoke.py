#!/usr/bin/env python3
"""Run the exact APK's real graphical client, capturing private RFB outside PRoot."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, platform, secrets, shutil
import signal, socket, stat, struct, subprocess, sys, time, zipfile, zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m
assets_tool=load('actual_client_assets_host',Path(__file__).with_name('prepare_assets.py'))
apk_tool=load('actual_client_apk_host',Path(__file__).with_name('build_apk.py'))
transport=load('accepted_presentation_transport_host',ROOT/'tools/android/presentation/host_smoke.py')
require,digest=assets_tool.require,assets_tool.digest
WIDTH,HEIGHT=800,600


def extract_apk_assets(apk,output,build_report,commit):
    report=assets_tool.read_json(build_report)
    require(report.get('repository_commit')==commit and report.get('application_id')==apk_tool.APP_ID
            and report.get('version_name')==apk_tool.VERSION_NAME and report.get('signature_verified') is True
            and report.get('payload_bytes_verified') is True
            and {'bytes':report.get('bytes'),'sha256':report.get('sha256')}==apk_tool.file_pin(apk),
            'Exact client APK receipt differs')
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        sources=apk_tool.java_sources(ROOT/'android/client/src/main',Path(tmp))
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


def save_png(path,pixels):
    # Raw RFB is little-endian BGRX; encode a bounded RGB PNG without Pillow.
    rows=bytearray()
    for y in range(HEIGHT):
        rows.append(0)
        for x in range(WIDTH):
            offset=(y*WIDTH+x)*4;rows.extend((pixels[offset+2],pixels[offset+1],pixels[offset]))
    def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    data=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',WIDTH,HEIGHT,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(rows,6))+chunk(b'IEND',b'')
    path.write_bytes(data)


def observe_rfb(connection,session,process,deadline,evidence):
    desktop=transport.rfb_handshake(connection);pixels=bytearray(WIDTH*HEIGHT*4)
    updates=0;fingerprints=[];snapshots=[];last_capture=0;terminal=None;started=time.monotonic()
    while process.poll() is None and time.monotonic()<deadline:
        try:
            connection.sendall(struct.pack('!BBHHHH',3,0,0,0,WIDTH,HEIGHT))
            kind=transport.recv_exact(connection,1)[0]
            if kind==2:continue
            if kind==3:
                header=transport.recv_exact(connection,7);size=struct.unpack_from('!I',header,3)[0]
                require(size<=4096,'Oversized cut text');transport.recv_exact(connection,size);continue
            require(kind==0,'Unexpected RFB message')
            count=struct.unpack_from('!H',transport.recv_exact(connection,3),1)[0]
            require(0<count<=1024,'Invalid RFB rectangle count')
            for _ in range(count):
                x,y,w,h,encoding=struct.unpack('!HHHHi',transport.recv_exact(connection,12))
                require(encoding==0 and w>0 and h>0 and x+w<=WIDTH and y+h<=HEIGHT,'Invalid RFB rectangle')
                raw=transport.recv_exact(connection,w*h*4)
                for row in range(h):
                    start=((y+row)*WIDTH+x)*4;pixels[start:start+w*4]=raw[row*w*4:(row+1)*w*4]
            updates+=1;sha=hashlib.sha256(pixels).hexdigest()
            if sha not in fingerprints and len(fingerprints)<2000:fingerprints.append(sha)
            now=time.monotonic()
            if now-last_capture>=20 and len(snapshots)<60:
                name=f'client-frame-{len(snapshots):03d}.png';save_png(evidence/name,pixels)
                snapshots.append({'file':name,'elapsed_seconds':round(now-started,3),'frame_sha256':sha});last_capture=now
            time.sleep(0.5)
        except (EOFError,BrokenPipeError,ConnectionResetError) as error:terminal=type(error).__name__;break
    if updates:save_png(evidence/'client-frame-final.png',pixels)
    return {'scope':'host_external_unix_rfb_actual_client','desktop':desktop,'session_id':session,'updates':updates,
            'distinct_frame_sha256':fingerprints,'snapshots':snapshots,'terminal_transport':terminal,
            'connected_outside_proot':True,'android_surface_validated':False,'gameplay_validated':False}


def make_command(work,assets,proot,session,data):
    command,env=transport.make_command(work,assets,proot,session)
    command[command.index('/opt/coh/presentation_diagnostic.py')]='/opt/coh/client_startup_diagnostic.py'
    where=command.index('--duration-seconds');del command[where:where+2]
    (work/'rootfs/game-import').mkdir()
    where=command.index('-w');command[where:where]=['-b',str(data.parent)+':/game-import']
    command+=['--game-data','/game-import/data','--startup-timeout-seconds','900','--observation-seconds','30']
    return command,env


def validate_report(report,session,manifest=None):
    require(report.get('scope')=='actual_client_startup_guest' and report.get('session_id')==session,'Wrong client session report')
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
            'wine_initialization','win32_runtime_dll','actual_client_startup']
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
    parser.add_argument('--repository-commit',required=True);args=parser.parse_args()
    require(platform.machine().lower() in ('aarch64','arm64'),'Native ARM64 Linux required')
    require(not args.work.exists(),'Fresh private smoke work required')
    args.work=args.work.resolve();args.proot=args.proot.resolve();args.evidence=args.evidence.resolve()
    args.work.mkdir(parents=True);args.evidence.mkdir(parents=True,exist_ok=True)
    manifest,assets,imports=extract_apk_assets(args.apk,args.work/'apk-assets',args.build_report,args.repository_commit)
    data=import_game_data(imports,args.archive.resolve(),args.work,args.evidence)
    session=secrets.token_hex(16);command,env=make_command(args.work,assets,args.proot,session,data)
    start=time.monotonic();deadline=start+1830;observer=None;failure=None;process=None
    with (args.evidence/'host-client.log').open('w') as log:
        try:
            process=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            socket_path=args.work/'socket/view.sock'
            while not socket_path.exists():
                require(process.poll() is None and time.monotonic()<deadline,'Guest exited before display socket');time.sleep(0.1)
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
                connection.settimeout(90);connection.connect(str(socket_path))
                observer=observe_rfb(connection,session,process,deadline,args.evidence)
            code=process.wait(timeout=max(1,deadline-time.monotonic()))
            require(code==0,'Client guest exited unsuccessfully')
            report=json.loads((args.work/'state/latest-report.json').read_text());validate_report(report,session,manifest)
            require(observer['updates']>=2 and len(observer['distinct_frame_sha256'])>=2,'Actual client did not change the display')
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
            result={'format':1,'status':'failed' if failure else 'passed','scope':'exact_apk_actual_client_native_arm64',
                    'repository_commit':args.repository_commit,'apk_sha256':digest(args.apk),
                    'runtime_manifest_sha256':digest(assets/'runtime-manifest.json'),'import_donor':apk_tool.import_donor(),
                    'session_id':session,'external_observer':observer,'failure':failure,'elapsed_seconds':round(time.monotonic()-start,3),
                    'android_execution_validated':False,'android_surface_validated':False,'gameplay_validated':False}
            (args.evidence/'host-client-report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
