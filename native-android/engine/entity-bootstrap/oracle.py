"""Whole original DB MAP_CONNECT producer and Queue passthrough fixture oracle."""
import ctypes as C,hashlib,importlib.util,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
PATHS=['DBServer/src/mapxfer.c','DBServer/src/clientcomm.c','DBServer/src/dbdispatch.c','QueueServer/src/QueueServer_Passthrough.c','QueueServer/src/QueueServer.c','Common/comm_backend.h','MapServer/src/container/containercallbacks.c','MapServer/src/dbcomm/dbcontainer.c','MapServer/src/entity/entserver.c','MapServer/src/player/clientEntityLink.c','MapServer/src/player/parseClientInput.c','MapServer/src/svr/svr_tick.c','MapServer/src/entity/entsend.c','Game/src/clientcomm/dbclient.c','Game/src/entity/entrecv.c','libs/UtilitiesLib/include/utilitieslib/network/net_packet_common.h']
def sha(b):return hashlib.sha256(b).hexdigest()
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def build(root,work):
 texts={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in PATHS};assert {p:sha(t.encode())for p,t in texts.items()}==json.loads((HERE/'source-pins.json').read_text());db=module('base_db',HERE/'../dbclient/check.py');tree=module('function_extract',HERE/'../costume-tree/tree_oracle.py');base=work/'base';base.mkdir();_,bp=db.oracle(root,base);code=(base/'oracle.c').read_text();code=code.replace(tree.extract(code,'pktCreateEx'),(HERE/'producer_adapters.h').read_text())
 # Source producer needs callback address on its NetLink in addition to writer's
 # packet fields. This is a fixture layout, not an original NetLink ABI.
 code=code.replace('int compressionAllowed,orderedAllowed;} NetLink;', 'int compressionAllowed,orderedAllowed;struct{struct{union{U32 S_addr;}S_un;}sin_addr;}addr;} NetLink;')
 pre='static int pktSendGetBitsPak(Packet*,Packet*,int);\n'
 bitpath='libs/UtilitiesLib/src/components/BitStream.c';netpath='libs/UtilitiesLib/src/network/net_packet.c'
 bits=(root/'upstream/ouroboros'/bitpath).read_text();net=(root/'upstream/ouroboros'/netpath).read_text();funcs={}
 for path,n in[(bitpath,'bsReadBitsPack'),(netpath,'pktGetBitsPack'),(PATHS[-1],'pktSendGetBitsPak'),(PATHS[0],'sendLoginInfoToGameClient'),(PATHS[3],'passdbOrMapConnect')]:
  text=tree.extract(bits if path==bitpath else net if path==netpath else texts[path],n);funcs[path+':'+n]=sha(text.encode());pre+=text+'\n'
 code+=pre+(HERE/'producer_wrapper.h').read_text();(work/'producer.c').write_text(code);subprocess.run(['cc','-std=gnu99','-O0','-fwrapv','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),work/'producer.c','-lz','-o',work/'producer.so'],check=True)
 return C.CDLL(str(work/'producer.so')),{'base_bit_request_source_pins':bp,'source_sha256_lf':{p:sha(t.encode())for p,t in texts.items()},'whole_executed_function_sha256_lf':funcs,'generated_c_sha256':sha(code.encode()),'source_model':'Whole sendLoginInfoToGameClient and queue passdbOrMapConnect execute; fixture container/IP/account/packet factory shells explicit. Original bit writer/readers execute unsanitized host. No real DB/Map/Auth or Win32 qualification.'}
