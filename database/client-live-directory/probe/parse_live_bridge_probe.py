"""Decode bounded raw NT observations; exit/console/custody are extra gates."""
import struct

MAX_BYTES=512*1024
MAX_ROWS=256
MAX_BATCHES=32


def require(value,message):
    if not value:
        raise ValueError(message)


def rows(data):
    require(0<len(data)<=8192,'Invalid NT buffer bytes')
    at=0
    found=[]
    while True:
        require(at+94<=len(data),'Truncated FileBoth prefix')
        nxt=struct.unpack_from('<I',data,at)[0]
        name_bytes=struct.unpack_from('<I',data,at+60)[0]
        require(0<name_bytes<=518 and not name_bytes%2 and at+94+name_bytes<=len(data),'Invalid NT name span')
        name=data[at+94:at+94+name_bytes].decode('utf-16le')
        require(all(32<=ord(c)<127 and c not in '/\\:*?"<>|' for c in name),'Unsupported NT basename')
        found.append({'name':name,'size_low':struct.unpack_from('<I',data,at+40)[0],
                      'write_FILETIME':struct.unpack_from('<Q',data,at+24)[0],
                      'attributes_consumed':struct.unpack_from('<I',data,at+56)[0]&0x17,
                      'record_offset':at,'next_entry_offset':nxt})
        require(len(found)<=MAX_ROWS,'NT row cap exceeded')
        if not nxt:
            break
        require(nxt%8==0 and nxt>=94+name_bytes and at+nxt<len(data),'Invalid NT next-entry span')
        at+=nxt
    return found


def parse(data):
    require(isinstance(data,bytes) and 136<=len(data)<=MAX_BYTES,'Invalid observer packet bound')
    require(data[:8]==b'COHNTB1\0','Unknown observer header')
    version,mode,pid,thread=struct.unpack_from('<IIII',data,8)
    require(version==1 and mode in (1,2) and pid>0 and thread>0,'Invalid observer identity/schema')
    require(not any(data[24:32]) and not any(data[72:96]),'Observer reserved bytes differ')
    inode=struct.unpack_from('<Q',data,32)[0]
    opened,info,path_len,final_len,buffer_cap,row_cap,batch_cap,byte_cap=struct.unpack_from('<IIIIIIII',data,40)
    require((buffer_cap,row_cap,batch_cap,byte_cap)==(8192,MAX_ROWS,MAX_BATCHES,MAX_BYTES),'Observer caps differ')
    require(path_len<1024 and final_len<1033 and 96+path_len+final_len+40<=len(data),'Observer path spans differ')
    path=data[96:96+path_len].decode('ascii')
    final=data[96+path_len:96+path_len+final_len].decode('ascii')
    at=96+path_len+final_len
    batches=[]
    observed=[]
    while data[at:at+8]==b'NTBATCH1':
        require(at+24<=len(data),'Truncated batch envelope')
        number,status,byte_count,row_count=struct.unpack_from('<IIII',data,at+8)
        require(number==len(batches) and status==0 and len(batches)<MAX_BATCHES,'Batch order or status differs')
        require(at+24+byte_count<=len(data),'Truncated batch payload')
        current=rows(data[at+24:at+24+byte_count])
        require(len(current)==row_count and len(observed)+row_count<=MAX_ROWS,'Batch cardinality differs')
        batches.append({'number':number,'status':status,'bytes':byte_count,'rows':current})
        observed.extend(current)
        at+=24+byte_count
    require(at+40==len(data) and data[at:at+8]==b'NTEND1\0\0','Observer footer missing/trailing bytes')
    footer=struct.unpack_from('<IIIIIIII',data,at+8)
    version,complete,batch_count,row_count,last_status,cleanup_failed,total,reserved=footer
    require(version==1 and complete in (0,1) and cleanup_failed in (0,1) and not reserved,'Invalid observer footer')
    require(batch_count==len(batches) and row_count==len(observed) and total==len(data),'Footer cardinality/byte mismatch')
    if complete:
        require(opened==info==0 and inode>0 and final and not cleanup_failed,'Incomplete native handle witness')
        if mode==1:
            require(last_status==0x80000006,'Stock observer lacks exact native EOF')
        else:
            require(not batches and not observed,'Sharing observer unexpectedly enumerated')
    return {'format':1,'mode':mode,'native_pid':pid,'native_thread':thread,'native_inode':inode,
            'native_open_status':opened,'native_info_status':info,'original_path':path,'final_object_path':final,
            'packet_complete':bool(complete),'native_cleanup_failed':bool(cleanup_failed),'last_query_status':last_status,
            'batches':batches,'rows':observed,'outer_native_exit_console_and_custody_required':True,
            'Wine_Android_runtime_authority':False,'provider_authority':False,'publication_allowed':False}
