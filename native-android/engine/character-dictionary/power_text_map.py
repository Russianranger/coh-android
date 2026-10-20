#!/usr/bin/env python3
"""Offline source-text CRC labels; never a receiver table or runtime dictionary."""
import argparse,hashlib,json,os,sqlite3,stat,subprocess,tempfile
from pathlib import Path
from power_text_oracle import build

TEXT_ROOT='upstream/i24/data/defs/powers'
FILE_LIMIT=8*1024*1024
FILE_COUNT_LIMIT=8192
POWER_LIMIT=32768
READ_BYTES=16384


def definitions(tokens):
    """Project direct ParsePowerDictionary/ParseBasePower FullName parameters.

    Original tokenizer handles comments, quotes and escaped/multiline strings.
    Nested field values are traversed without retaining their object graph.
    No powerset-generated aliases or name-from-filename rule is invented.
    """
    tokens=iter(tokens)
    def take():
        try:return next(tokens)
        except StopIteration as exc:raise ValueError('truncated Power record') from exc
    for keyword,line,quoted in tokens:
        if quoted or keyword.lower()!=b'power':raise ValueError('unexpected PowerDictionary token')
        name,_,_=take()
        if name in (b'{',b'}') or not name:raise ValueError('missing FullName struct parameter')
        opening,_,opening_quoted=take()
        if opening!=b'{' or opening_quoted:raise ValueError('missing ParseBasePower start')
        depth=1;field_line=None
        while depth:
            token,current,was_quoted=take()
            if not was_quoted and token==b'{':
                depth+=1
                if depth>64:raise ValueError('nested Power record limit')
            elif not was_quoted and token==b'}':depth-=1
            elif depth==1:
                first_on_line=field_line!=current;field_line=current
                if first_on_line and not was_quoted and token.lower()==b'fullname':
                    name,_,_=take()
                    if not name or name in (b'{',b'}'):raise ValueError('invalid explicit FullName')
        yield name,line


def nul_records(stream):
    pending=b''
    while True:
        chunk=stream.read(4096)
        if not chunk:
            if pending:raise ValueError('truncated source tree listing')
            return
        pending+=chunk
        while b'\0' in pending:
            record,pending=pending.split(b'\0',1)
            if len(record)>1024:raise ValueError('source path limit')
            yield record
        if len(pending)>1024:raise ValueError('source path limit')


def tracked_inputs(root):
    """Git byte path order is explicit offline order, not a runtime load claim."""
    process=subprocess.Popen(['git','-C',str(root),'ls-tree','-rz','--long','HEAD','--',TEXT_ROOT],stdout=subprocess.PIPE)
    try:
        for record in nul_records(process.stdout):
            meta,path=record.split(b'\t',1)
            if not path.endswith(b'.powers'):continue
            mode,kind,blob,size=meta.split()
            if mode!=b'100644' or kind!=b'blob':raise ValueError('nonordinary source definition')
            yield path.decode('ascii'),blob.decode('ascii'),int(size)
        if process.wait()!=0:raise ValueError('source tree listing failed')
    finally:
        process.stdout.close()
        if process.poll() is None:process.terminate();process.wait()


def identity(info):return(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)


def source_file(root,path,size,blob):
    if not 0<size<=FILE_LIMIT:raise ValueError('source definition file bound')
    prefix=root
    for part in Path(path).parts:
        prefix=prefix/part
        if prefix.is_symlink():raise ValueError('source path alias')
    fd=os.open(root/path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size!=size:raise ValueError('source definition identity')
        sha=hashlib.sha256();git=hashlib.sha1(b'blob '+str(size).encode()+b'\0');read=0
        while True:
            data=os.read(fd,READ_BYTES)
            if not data:break
            if b'\0' in data:raise ValueError('NUL in source definition')
            read+=len(data)
            if read>size:raise ValueError('source definition grew')
            sha.update(data);git.update(data)
        if read!=size or git.hexdigest()!=blob or identity(os.fstat(fd))!=identity(info):raise ValueError('source content differs from Git')
        os.lseek(fd,0,os.SEEK_SET)
        return fd,identity(info),sha.hexdigest()
    except BaseException:os.close(fd);raise


def build_map(root,output,original,provenance):
    root=Path(root).resolve();output=Path(output).absolute()
    if output.exists() or output.is_symlink():raise ValueError('output already exists')
    if (root/'upstream').resolve() in output.resolve().parents:raise ValueError('output overlaps upstream')
    output.parent.mkdir(parents=True,exist_ok=True)
    fd,temporary=tempfile.mkstemp(prefix='.power-text-',suffix='.sqlite',dir=output.parent);os.close(fd)
    temporary=Path(temporary);database=None
    try:
        database=sqlite3.connect(temporary)
        database.execute('PRAGMA cache_size=-1024');database.execute('PRAGMA temp_store=FILE');database.execute('PRAGMA mmap_size=0')
        database.execute('CREATE TABLE inputs(path TEXT PRIMARY KEY, bytes INTEGER NOT NULL, git_blob TEXT NOT NULL, sha256 TEXT NOT NULL)')
        database.execute('CREATE TABLE powers(crc INTEGER PRIMARY KEY, full_name TEXT NOT NULL, path TEXT NOT NULL, line INTEGER NOT NULL, ordinal INTEGER NOT NULL)')
        database.execute('CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        stats={'schema':'coh-offline-power-text-map-v1','text_source_revision':subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),
               'input_files':0,'input_bytes':0,'declarations':0,'unique_crc':0,'duplicate_crc':0,'distinct_normalized_crc_collisions':0,
               'input_order':'Git tree byte path order, then source token order; first CRC winner',
               'scope':'direct source-text FullName labels only; not a loaded dictionary or generation',
               'runtime_dictionary_supplied':False,'original':provenance,
               'explicit_buffers':{'original_tokenizer_owner_bytes':original.lib.ptm_owner_bytes(),'token_transfer_bytes':12001,'hash_read_bytes':READ_BYTES,'sqlite_cache_kib':1024,'sqlite_mmap_bytes':0},
               'Python_SQLite_allocator_and_file_cache_overhead_included':False}
        for path,blob,size in tracked_inputs(root):
            stats['input_files']+=1
            if stats['input_files']>FILE_COUNT_LIMIT:raise ValueError('source file count bound')
            fd,before,sha=source_file(root,path,size,blob)
            token_stream=original.tokens(fd)
            try:
                for full,line in definitions(token_stream):
                    stats['declarations']+=1
                    if stats['declarations']>POWER_LIMIT:raise ValueError('power record bound')
                    crc=original.crc(full);name=full.decode('ascii')
                    prior=database.execute('SELECT full_name FROM powers WHERE crc=?',(crc,)).fetchone()
                    if prior is None:
                        database.execute('INSERT INTO powers VALUES(?,?,?,?,?)',(crc,name,path,line,stats['declarations']));stats['unique_crc']+=1
                    else:
                        stats['duplicate_crc']+=1
                        normalize=lambda s:s.lower().replace('\\','/')
                        if normalize(prior[0])!=normalize(name):stats['distinct_normalized_crc_collisions']+=1
                if identity(os.fstat(fd))!=before:raise ValueError('source changed during tokenization')
            finally:token_stream.close();os.close(fd)
            database.execute('INSERT INTO inputs VALUES(?,?,?,?)',(path,size,blob,sha));stats['input_bytes']+=size
        if not stats['input_files']:raise ValueError('no tracked power definitions')
        database.execute('INSERT INTO metadata VALUES(?,?)',('summary',json.dumps(stats,separators=(',',':'))))
        database.commit();database.close();database=None
        with temporary.open('rb') as finished:os.fsync(finished.fileno())
        # Publication cannot replace any existing artifact or source path.
        os.link(temporary,output);temporary.unlink()
        return stats
    finally:
        if database is not None:database.close()
        temporary.unlink(missing_ok=True);Path(str(temporary)+'-journal').unlink(missing_ok=True)


def lookup(database,crc):
    if type(crc)is not int or not 0<crc<=0xffffffff:raise ValueError('nonzero uint32 CRC required')
    connection=sqlite3.connect('file:'+str(Path(database).resolve())+'?mode=ro',uri=True)
    try:
        row=connection.execute('SELECT full_name,path,line,ordinal FROM powers WHERE crc=?',(crc,)).fetchone()
        return None if row is None else dict(zip(('full_name','path','line','ordinal'),row))
    finally:connection.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[3]);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--crc',type=lambda s:int(s,0))
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='coh-power-text-original-') as work:
        original,provenance,_=build(args.source_root,Path(work));summary=build_map(args.source_root,args.output,original,provenance)
    result={k:summary[k] for k in ('schema','text_source_revision','input_files','input_bytes','declarations','unique_crc','duplicate_crc','distinct_normalized_crc_collisions')}
    result.update(output=str(args.output),runtime_dictionary_supplied=False)
    if args.crc is not None:result.update(lookup_crc=hex(args.crc),lookup=lookup(args.output,args.crc))
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
