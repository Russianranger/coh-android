"""Session/process/identity-bound observations from the opt-in native station bridge."""
import hashlib
import math
import re
import time
import native_character_events as legacy
base = legacy.base
ENVIRONMENT = 'COH_WINE_MONORAIL_SESSION'
REPLY_ENVIRONMENT = 'COH_WINE_MONORAIL_REPLY'
PREFIX = 'COH_ZONING_EVENT_V1 '
PATTERN = re.compile(r'^COH_ZONING_EVENT_V1 session=(?P<session>[0-9a-f]{32}) '
    r'pid=(?P<pid>[1-9][0-9]*) tid=(?P<tid>[1-9][0-9]*) '
    r'sequence=(?P<sequence>[1-9][0-9]*) kind=(?P<kind>ready|position|station_request|station_departure) '
    r'utc_ms=(?P<utc_ms>[1-9][0-9]*) map_id=(?P<map_id>1|5|101) db_id=(?P<db_id>1) '
    r'auth_id=(?P<auth_id>[1-9][0-9]*) name=THORHERO account=COHLOCAL '
    r'peer=127\.0\.0\.1:(?P<port>[0-9]+) request=(?P<request>[0-9]+) target=(?P<target>0|1|5) '
    r'position=<(?P<x>' + legacy.NUMBER + '),(?P<y>' + legacy.NUMBER + '),(?P<z>' + legacy.NUMBER + r')>$')

def records(console, *, session, progress, launch_utc_ms, now_utc_ms, db_id, auth_id, map_id):
    base.require(type(console) is str and len(console.encode()) <= 16*1024*1024,
        'Monorail console exceeded bound')
    base.require(type(session) is str and re.fullmatch(r'[0-9a-f]{32}', session)
        and type(launch_utc_ms) is int and type(now_utc_ms) is int and launch_utc_ms <= now_utc_ms
        and type(db_id) is int and db_id == 1 and type(auth_id) is int and auth_id > 0
        and type(map_id) is int and map_id in (1,5,101) and isinstance(progress,dict)
        and progress.get('available') is True
        and type(progress.get('windows_pid')) is int and progress['windows_pid'] > 0
        and type(progress.get('main_thread_id')) is int and progress['main_thread_id'] > 0,
        'Monorail observer launch identity missing')
    values=[]; previous=0; previous_time=launch_utc_ms-1000; pending=None
    for line in console[:console.rfind('\n')+1].splitlines():
        if PREFIX.rstrip() not in line: continue
        match=PATTERN.fullmatch(line)
        base.require(match is not None,'Malformed native monorail event')
        row={k:int(match[k]) for k in ('pid','tid','sequence','utc_ms','map_id','db_id','auth_id','port','request','target')}
        base.require(match['session']==session and row['pid']==progress['windows_pid']
            and row['tid']==progress['main_thread_id'] and row['map_id']==map_id
            and row['db_id']==db_id and row['auth_id']==auth_id
            and row['sequence']==previous+1 and row['sequence']<=0xffffffff
            and previous_time<=row['utc_ms']<=now_utc_ms+1000,
            'Monorail event differs from current owned launch')
        kind=match['kind']; position=[float(match[k]) for k in ('x','y','z')]
        base.require(all(math.isfinite(p) and abs(p)<=1000000 for p in position)
            and ((kind=='ready' and 1<=row['port']<=65535 and position==[0,0,0])
                 or (kind!='ready' and row['port']==0 and (kind=='position' or position==[0,0,0]))),
            'Invalid monorail event fields')
        if kind=='station_request':
            base.require(row['request']==row['sequence'] and (map_id,row['target']) in ((1,5),(5,1)),
                'Unsupported native station request')
            pending=(row['request'],row['target'])
        elif kind=='station_departure':
            base.require(pending==(row['request'],row['target']),'Station departure lacks exact preceding request')
            pending=None
        row.update(format=1,kind=kind,session_id=session,name='THORHERO',account='COHLOCAL',position=position,
            windows_pid=row['pid'],main_thread_id=row['tid'],
            log_timestamp=time.strftime('%y%m%d %H:%M:%S',time.localtime(row['utc_ms']/1000)),
            line_sha256=hashlib.sha256(line.encode()).hexdigest(),log_route='immediate_owned_mapserver_console',
            source='current_owned_mapserver_monorail_'+kind)
        values.append(row);previous=row['sequence'];previous_time=row['utc_ms']
        base.require(len(values)<=legacy.EVENT_LIMIT,'Monorail native event count exceeded bound')
    return values

latest_ready=legacy.latest_ready
positions_after_ready=legacy.positions_after_ready

def reply(record):
    base.require(isinstance(record,dict) and record.get('kind')=='station_request'
        and re.fullmatch(r'[0-9a-f]{32}',str(record.get('session_id','')))
        and all(type(record.get(k)) is int and record[k]>0 for k in ('pid','request','target'))
        and (record.get('map_id'),record['target']) in ((1,5),(5,1)), 'Invalid monorail reply identity')
    return ('COH_MONORAIL_REPLY_V1 session={session_id} pid={pid} request={request} target={target} ready=1\n').format(**record)

def console_events(owned):
    """Decode only complete new event lines, never rescan the growing server log."""
    output=owned['process'].output
    offset=owned.get('monorail_scan_offset',0)
    base.require(len(output)>=offset,'Owned monorail console was truncated')
    chunk=owned.get('monorail_scan_tail',b'')+bytes(output[offset:])
    owned['monorail_scan_offset']=len(output)
    last=chunk.rfind(b'\n')
    complete=chunk[:last+1] if last>=0 else b''
    tail=chunk[last+1:] if last>=0 else chunk
    # A non-event logging line may legitimately be long. Preserve only enough
    # trailing bytes to recognize a split prefix; event lines remain bounded.
    base.require(PREFIX.encode() not in tail or len(tail)<=2048,'Oversized native monorail event')
    owned['monorail_scan_tail']=tail[-2048:]
    lines=owned.setdefault('monorail_event_lines',[])
    for raw in complete.splitlines():
        if PREFIX.rstrip().encode() in raw:
            base.require(len(raw)<=2048,'Oversized native monorail event')
            lines.append(raw.decode('ascii'))
    base.require(len(lines)<=legacy.EVENT_LIMIT,'Native monorail event count exceeded bound')
    return '\n'.join(lines)+'\n'
