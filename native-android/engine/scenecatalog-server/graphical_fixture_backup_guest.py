#!/usr/bin/env python3
"""Full snapshot of the freshly graphically created diagnostic fixture only.

Invoked by a separate PRoot client with the exact running APK's filesystem
binds, guest identity and environment; SQL uses its owned Unix socket. This does not
initialize a database, insert identities, stop servers, or change game data.
The owner withholds its ordinary finish request until this helper has exited.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, selectors, stat, subprocess, sys, time
from pathlib import Path

MAX_DUMP = 512*1024**2
MAX_TABLES = 4096
SECONDS = 240
STAGES=('INPUTS','PROFILE','PG_TOOLS','SNAPSHOT','CHARACTER','TABLES','DUMP','ARCHIVE','PUBLISH','RECEIPT','COMPLETE')
FAILURES=frozenset(('NONE','PRIVATE_REGULAR_FILE','JSON_OBJECT','SQL_IDENTIFIER','SAVE_REQUEST',
    'OWNED_POSTMASTER','SNAPSHOT_CONNECTION_EXITED','SNAPSHOT_QUERY_TIMEOUT','SNAPSHOT_CONNECTION_EOF',
    'SNAPSHOT_QUERY_BOUND','SNAPSHOT_CLOSE','BACKUP_DEADLINE','PG_TOOL_FAILED','PRIVATE_BACKUP_DIRECTORY',
    'FRESH_BACKUP','PROFILE_NOT_INITIALIZED','PROFILE_CREDENTIALS','POSTGRES_MAJOR','PG_TOOL_VERSION',
    'LIVE_DATABASE_IDENTITY','FRESH_GRAPHICAL_CHARACTER','TABLE_INVENTORY','TABLE_ROW_COUNT','CUSTOM_ARCHIVE',
    'ARCHIVE_VERSION','FULL_ARCHIVE_LIST','ARCHIVE_IDENTIFIER_SCOPE','FULL_TABLE_DATA_COVERAGE','SNAPSHOT_LOST',
    'DUMP_COPY_IDENTITY','DUMP_COPY_SIZE','PUBLICATION_PROBE','BACKUP_DEPENDENCY_FAILED'))
class Refused(ValueError): pass
def require(value, code):
    if not value: raise Refused(code)
def regular(path, maximum):
    info=path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and not info.st_mode&0o077
            and 0<info.st_size<=maximum, 'PRIVATE_REGULAR_FILE')
    return path
def object_file(path, maximum=16384):
    regular(path, maximum); value=json.loads(path.read_bytes())
    require(type(value) is dict, 'JSON_OBJECT'); return value
def file_pin(path):
    regular(path,MAX_DUMP)
    with path.open('rb') as stream: digest=hashlib.file_digest(stream,'sha256').hexdigest()
    return {'bytes':path.stat().st_size,'sha256':digest}
def publish_regular(partial,final,expected,diagnostic=None):
    # Actual PRoot --link2symlink represents link() with host symlinks while
    # faking guest lstat. The owner must observe a real single-link file outside
    # PRoot, so publish with an exclusive bounded byte copy, never a hard link.
    descriptor=None;stream=None;owned=False
    diagnostic={} if diagnostic is None else diagnostic
    try:
        require(file_pin(partial)==expected,'DUMP_COPY_IDENTITY')
        descriptor=os.open(final,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600);owned=True
        stream=os.fdopen(descriptor,'wb');descriptor=None;total=0
        with partial.open('rb') as incoming:
            while block:=incoming.read(65536):
                total+=len(block);require(total<=expected['bytes']<=MAX_DUMP,'DUMP_COPY_SIZE');stream.write(block)
        require(total==expected['bytes'],'DUMP_COPY_SIZE')
        stream.flush();os.fsync(stream.fileno());stream.close();stream=None
        require(file_pin(final)==expected and file_pin(partial)==expected,'DUMP_COPY_IDENTITY')
    except BaseException:
        if stream is not None:
            try:stream.close()
            except BaseException:diagnostic['rollback_complete']=False
        if descriptor is not None:
            try:os.close(descriptor)
            except OSError:diagnostic['rollback_complete']=False
        if owned:
            try:final.unlink()
            except OSError:diagnostic['rollback_complete']=False
        raise
def publication_probe(state=Path('/state')):
    # Leaves one tiny regular final for the host's real lstat/hash check. The
    # host owns rollback. This creates no profile/database/server/identity.
    directory=state/'graphical-fixture-publication-probe';directory.mkdir(mode=0o700)
    partial=directory/'fixture.pgdump.partial';final=directory/'fixture.pgdump'
    with partial.open('xb') as output:
        os.chmod(partial,0o600);output.write(b'COH_FIXTURE_REGULAR_PUBLICATION_PROBE_V1\n')
        output.flush();os.fsync(output.fileno())
    expected=file_pin(partial);publish_regular(partial,final,expected);partial.unlink()
    require(file_pin(final)==expected,'PUBLICATION_PROBE')
    return {'passed':True,'regular_publication_probe':True}
def identifier(name):
    require(type(name) is str and 0<len(name)<=63 and '\x00' not in name, 'SQL_IDENTIFIER')
    return '"'+name.replace('"','""')+'"'
def request_identity(value):
    require(set(value)=={'schema','session_id','client_pid','character_id','account','character_name'}
            and value['schema']=='coh-graphical-fixture-backup-request-v1'
            and re.fullmatch('[0-9a-f]{32}',value.get('session_id','')) is not None
            and all(type(value.get(key)) is int and 0<value[key]<=2147483647 for key in ('client_pid','character_id'))
            and value['account']=='COHLOCAL' and value['character_name']=='THORHERO', 'SAVE_REQUEST')
    return value
def postmaster_port(raw,pgdata,socket):
    lines=raw.splitlines()
    # PostgreSQL src/include/utils/pidfile.h pads all PM_STATUS values to eight
    # characters; its actual READY value is "ready   ", not the word "ready".
    require(len(lines)>=8 and lines[0].isdigit() and int(lines[0])>0 and lines[1]==str(pgdata)
            and lines[3].isdigit() and 1024<=int(lines[3])<=65535 and lines[4]==str(socket)
            and lines[5]=='127.0.0.1' and lines[7]=='ready   ','OWNED_POSTMASTER')
    return int(lines[3])

class Snapshot:
    """One actual read-only psql transaction stays open during pg_dump."""
    def __init__(self, command, environment, deadline):
        self.deadline=deadline
        self.process=subprocess.Popen(command,env=environment,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                      stderr=subprocess.DEVNULL,bufsize=0)
        self.pending=b''; self.selector=selectors.DefaultSelector()
        self.selector.register(self.process.stdout,selectors.EVENT_READ)
    def query(self, sql):
        require(self.process.poll() is None,'SNAPSHOT_CONNECTION_EXITED')
        self.process.stdin.write((sql+'\n').encode());self.process.stdin.flush()
        end=min(self.deadline,time.monotonic()+30)
        while b'\n' not in self.pending:
            require(time.monotonic()<end,'SNAPSHOT_QUERY_TIMEOUT')
            if not self.selector.select(max(0,min(.2,end-time.monotonic()))): continue
            data=os.read(self.process.stdout.fileno(),65536)
            require(data,'SNAPSHOT_CONNECTION_EOF');self.pending+=data
            require(len(self.pending)<=8*1024**2,'SNAPSHOT_QUERY_BOUND')
        line,self.pending=self.pending.split(b'\n',1)
        return json.loads(line)
    def close(self):
        failures=[]
        try:
            if self.process.poll() is None:
                self.process.stdin.write(b'ROLLBACK;\n\\q\n');self.process.stdin.flush()
                self.process.stdin.close();self.process.wait(timeout=5)
        except (OSError,subprocess.SubprocessError):
            failures.append('SNAPSHOT_CLOSE')
            self.process.kill();self.process.wait(timeout=5)
        finally:
            for handle in (self.process.stdin,self.process.stdout):
                try: handle.close()
                except OSError: failures.append('SNAPSHOT_FD_CLOSE')
            self.selector.close()
        require(self.process.returncode==0 and not failures,'SNAPSHOT_CLOSE')

def tool(command,environment,deadline,limit=8*1024**2):
    remaining=min(180,deadline-time.monotonic());require(remaining>0,'BACKUP_DEADLINE')
    result=subprocess.run(command,env=environment,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL,timeout=remaining)
    require(result.returncode==0 and len(result.stdout)<=limit,'PG_TOOL_FAILED')
    return result.stdout

def capture(state=Path('/state'),pgbin=Path('/opt/coh/pgsql/bin'),diagnostic=None):
    diagnostic={} if diagnostic is None else diagnostic
    diagnostic['rollback_complete']=True
    def advance(value):
        require(value in STAGES,'BACKUP_DEPENDENCY_FAILED');diagnostic['stage']=value
    advance('INPUTS')
    os.umask(0o077);deadline=time.monotonic()+SECONDS
    directory=state/'graphical-fixture-backup'
    require(directory.is_dir() and not directory.is_symlink() and not directory.stat().st_mode&0o077,
            'PRIVATE_BACKUP_DIRECTORY')
    request=request_identity(object_file(directory/'request.json'))
    for name in ('fixture.pgdump','fixture.pgdump.partial','backup.json'):
        require(not (directory/name).exists() and not (directory/name).is_symlink(),'FRESH_BACKUP')
    advance('PROFILE');profile=state/'diagnostic/android-local-login';pgdata=profile/'pgdata';socket=profile/'socket'
    sys.path.insert(0,'/opt/coh')
    import local_login_server as local
    marker=local.profile_record(profile/'profile.json')
    require(marker['initialized'] is True,'PROFILE_NOT_INITIALIZED')
    credentials=object_file(profile/'credentials.json',4096)
    require(set(credentials)=={'cohdiag_admin','cohtest'} and all(type(value) is str and
            re.fullmatch('[0-9a-f]{64}',value) for value in credentials.values()),'PROFILE_CREDENTIALS')
    # PostgreSQL writes this owned file itself: obtain the actual chosen port.
    pidfile=pgdata/'postmaster.pid';regular(pidfile,4096);port=postmaster_port(pidfile.read_text(),pgdata,socket)
    require((pgdata/'PG_VERSION').read_text().strip()=='18','POSTGRES_MAJOR')
    environment={key:value for key,value in os.environ.items() if not key.startswith('PG')}
    # The diagnostic administrator can read every schema and server setting;
    # pg_dump is database-only and never serializes role/password definitions.
    environment.update(PGPASSWORD=credentials['cohdiag_admin'],PGCONNECT_TIMEOUT='5',PGOPTIONS='-c search_path=dbo,pg_catalog')
    connection=['-h',str(socket),'-p',str(port),'-U','cohdiag_admin','-d',local.DATABASE,'-w']
    advance('PG_TOOLS');dump_version=tool([str(pgbin/'pg_dump'),'--version'],environment,deadline,4096).decode().strip()
    restore_version=tool([str(pgbin/'pg_restore'),'--version'],environment,deadline,4096).decode().strip()
    require(dump_version=='pg_dump (PostgreSQL) 18.6' and restore_version=='pg_restore (PostgreSQL) 18.6','PG_TOOL_VERSION')
    snapshot=None;committed=False;owned=[];partial=directory/'fixture.pgdump.partial';final=directory/'fixture.pgdump'
    try:
        advance('SNAPSHOT')
        snapshot=Snapshot([str(pgbin/'psql'),'-X','-q','-A','-t','-v','ON_ERROR_STOP=1',*connection],environment,deadline)
        info=snapshot.query("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY; SELECT json_build_object('snapshot',pg_export_snapshot(),'database',current_database(),'user',current_user,'server_version_num',current_setting('server_version_num')::int,'data_directory',current_setting('data_directory'),'listen',current_setting('listen_addresses'),'port',current_setting('port')::int,'socket',current_setting('unix_socket_directories'),'fsync',current_setting('fsync'),'synchronous_commit',current_setting('synchronous_commit'),'full_page_writes',current_setting('full_page_writes')); ")
        require(info.get('database')==local.DATABASE and info.get('user')=='cohdiag_admin'
                and info.get('server_version_num')==180006 and type(info['server_version_num']) is int
                and info.get('data_directory')==str(pgdata) and info.get('listen')=='127.0.0.1'
                and info.get('port')==port and info.get('socket')==str(socket)
                and all(info.get(key)=='on' for key in ('fsync','synchronous_commit','full_page_writes'))
                and re.fullmatch('[0-9A-Fa-f]+-[0-9A-Fa-f]+-[0-9]+',info.get('snapshot','')),'LIVE_DATABASE_IDENTITY')
        advance('CHARACTER');who=snapshot.query("SELECT json_build_object('accounts',(SELECT count(*) FROM dbo.shardaccounts),'account',(SELECT authname FROM dbo.shardaccounts LIMIT 1),'auth_id',(SELECT containerid FROM dbo.shardaccounts LIMIT 1),'characters',(SELECT count(*) FROM dbo.ents),'character_id',(SELECT containerid FROM dbo.ents LIMIT 1),'character_name',(SELECT name FROM dbo.ents LIMIT 1),'character_account',(SELECT authname FROM dbo.ents LIMIT 1),'character_auth_id',(SELECT authid FROM dbo.ents LIMIT 1),'map_id',(SELECT staticmapid FROM dbo.ents LIMIT 1));")
        require(all(type(who.get(key)) is int and who[key]>0 for key in ('accounts','auth_id','characters','character_id','character_auth_id','map_id'))
                and who['accounts']==who['characters']==who['map_id']==1
                and who['account']==who['character_account']=='COHLOCAL' and who['character_name']=='THORHERO'
                and who['auth_id']==who['character_auth_id'] and who['character_id']==request['character_id'],'FRESH_GRAPHICAL_CHARACTER')
        advance('TABLES');tables=snapshot.query("SELECT coalesce(json_agg(json_build_array(n.nspname,c.relname) ORDER BY n.nspname,c.relname),'[]') FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind='r' AND n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%' AND n.nspname NOT LIKE 'pg_temp%';")
        require(type(tables) is list and 4<=len(tables)<=MAX_TABLES and all(type(row) is list and len(row)==2 for row in tables),'TABLE_INVENTORY')
        counts=[]
        for schema,table in tables:
            count=snapshot.query('SELECT to_json(count(*)) FROM '+identifier(schema)+'.'+identifier(table)+';')
            require(type(count) is int and 0<=count<=10000000,'TABLE_ROW_COUNT');counts.append({'schema':schema,'table':table,'rows':count})
        advance('DUMP');fd=os.open(partial,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);owned.append(partial);os.close(fd)
        tool([str(pgbin/'pg_dump'),*connection,'--format=custom','--compress=0','--no-owner','--no-privileges',
              '--snapshot='+info['snapshot'],'--file='+str(partial)],environment,deadline,4096)
        pin=file_pin(partial)
        with partial.open('rb') as source:require(source.read(5)==b'PGDMP','CUSTOM_ARCHIVE')
        advance('ARCHIVE');listing=tool([str(pgbin/'pg_restore'),'--list',str(partial)],environment,deadline)
        require(b'Dumped from database version: 18.6' in listing and b'Dumped by pg_dump version: 18.6' in listing,
                'ARCHIVE_VERSION')
        entries=[line for line in listing.splitlines() if line and not line.startswith(b';')]
        require(0<len(entries)<=100000 and any(b' TABLE DATA dbo ents ' in line for line in entries),'FULL_ARCHIVE_LIST')
        # The accepted generated schema uses simple identifiers. Refuse an
        # unfamiliar TOC spelling rather than infer coverage from one table.
        require(all(re.fullmatch('[a-z_][a-z0-9_]*',name) for row in tables for name in row),'ARCHIVE_IDENTIFIER_SCOPE')
        listed={(words[5].decode(),words[6].decode()) for line in entries
                if len(words:=line.split())==8 and words[3:5]==[b'TABLE',b'DATA']}
        require(set(map(tuple,tables))<=listed,'FULL_TABLE_DATA_COVERAGE')
        # The transaction remains live until both full dump and archive listing succeeded.
        require(snapshot.query('SELECT to_json(1);')==1,'SNAPSHOT_LOST');snapshot.close();snapshot=None
        advance('PUBLISH');publish_regular(partial,final,pin,diagnostic);owned.append(final);partial.unlink()
        receipt={'schema':'coh-graphical-fixture-full-backup-v1','passed':True,'request':request,'database':local.DATABASE,
                 'fixture_account':'COHLOCAL','fixture_character':'THORHERO','fixture_identity':who,
                 'full_database_custom_archive':True,'selected_projection_only':False,'dump':pin,
                 'server_version_num':info['server_version_num'],'pg_dump_version':dump_version,
                 'pg_restore_version':restore_version,'archive_list_sha256':hashlib.sha256(listing).hexdigest(),
                 'archive_entries':len(entries),'table_counts':counts,'counts_share_exported_dump_snapshot':True,
                 'all_inventoried_tables_have_archive_data_entries':True,
                 'table_count':len(counts),'rows':sum(row['rows'] for row in counts),
                 'roles_or_role_passwords_dumped':False,'source_or_game_data_modified':False}
        advance('RECEIPT')
        with (directory/'backup.json').open('x') as output:
            owned.append(directory/'backup.json')
            json.dump(receipt,output,indent=2);output.write('\n');output.flush();os.fsync(output.fileno())
        committed=True;advance('COMPLETE')
        return receipt
    finally:
        primary=sys.exc_info()[0] is not None;cleanup_error=None
        if snapshot is not None:
            try:snapshot.close()
            except Exception as error:cleanup_error=error;diagnostic['rollback_complete']=False
        if not committed:
            for path in reversed(owned):
                try:path.unlink(missing_ok=True)
                except OSError as error:
                    diagnostic['rollback_complete']=False
                    if cleanup_error is None:cleanup_error=error
        if not primary and cleanup_error is not None:raise cleanup_error

def main():
    diagnostic={'stage':'INPUTS','rollback_complete':True}
    try:capture(diagnostic=diagnostic);print(json.dumps({'passed':True,'full_database_custom_archive':True,
        'stage':'COMPLETE','failure_code':'NONE','rollback_complete':True}));return 0
    except Exception as error:
        code=str(error) if isinstance(error,Refused) and str(error) in FAILURES else 'BACKUP_DEPENDENCY_FAILED'
        print(json.dumps({'passed':False,'stage':diagnostic['stage'],'failure_code':code,
            'rollback_complete':diagnostic['rollback_complete']}));return 2
if __name__=='__main__':raise SystemExit(main())
