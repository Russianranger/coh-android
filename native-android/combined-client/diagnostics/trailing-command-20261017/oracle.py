"""Exact original append block and bit helpers; restricted nested command observer."""
from pathlib import Path
import ctypes as C,hashlib,importlib.util,json,re,subprocess
HERE=Path(__file__).resolve().parent
FILES=['MapServer/src/entity/entsend.c','Game/src/clientcomm/clientcomm.c','Common/comm_game.h','libs/UtilitiesLib/include/utilitieslib/network/net_structdefs.h','libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packet.c']
def sha(x):return hashlib.sha256(x).hexdigest()
def extract(text,name):
 m=re.search(r'^[^\n;{}=]+?\b'+name+r'\s*\([^;{}]*\)\s*\{',text,re.M)
 if not m:raise ValueError(name)
 at=m.end();depth=1
 while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[m.start():at]+'\n'
def generate(root):
 t={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in FILES};s=t[FILES[0]];c=t[FILES[1]];bit=t[FILES[4]];net=t[FILES[5]]
 prepath=root/'native-android/tools/protocol_fixture/prepare.py'
 if (HERE/'source-pins.json').exists():
  old=json.loads((HERE/'source-pins.json').read_text())
  if sha(prepath.read_bytes())!=old['prepare_shell_sha256'] or {p:sha(x.encode())for p,x in t.items()}!=old['whole_sources_sha256_lf']:raise ValueError('pre-import source changed')
 sp=importlib.util.spec_from_file_location('framing_bit_shell',prepath);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
 enum=t[FILES[2]].split('typedef enum ServerCommCmd',1)[1].split('}ServerCommCmd',1)[0]
 if '} ServerCommCmd' in enum:enum=enum.split('} ServerCommCmd')[0]
 enum=enum[:enum.rfind('}')+1] if '}' in enum else enum+'}'
 # Complete source enum, not separately hand-numbered command constants.
 enum='typedef enum ServerCommCmd'+enum+' ServerCommCmd;\n'
 assert re.search(r'COMM_MAX_CMD\s*=\s*2\s*,',t[FILES[3]])
 start=s.index('    if (player_ent->entityPacket) {',s.index('void entSendUpdate'))
 stop=s.index('\n    player_ent->entityPacket = pak;',start)
 append=s[start:stop]
 final='pktSendBitsPack(e->entityPacket, 1, 0 );'
 assert final in s and 'xcase SERVER_GAME_CMDS:break;' in c and 'cmd = -1;' in c
 funcs={};code=m.PREAMBLE+'\n#define COMM_MAX_CMD 2\n'+enum
 def add(text,name):
  nonlocal code
  body=extract(text,name);funcs[name]=sha(body.encode());code+=body
 for name in ['initBitStream','bsWriteBits','bsReadBits','bsWriteBitsPack','bsReadBitsPack','bsAlignByte','bsGetCursorBitPosition','bsGetBitLength','bsWriteBitsArray']:add(bit,name)
 code+='static void bsTypedAlignBitsArray(BitStream*b){(void)b;assert(0);}\n'
 for name in ['pktSendBitsPack','pktGetBitsPack','pktSendBitsArray','pktAlignBitsArray']:add(net,name)
 add(c,'receiveByteAlignmentTag')
 code+='''
#define PERFINFO_AUTO_START(a,b) ((void)0)
#define PERFINFO_AUTO_STOP() ((void)0)
typedef struct {Packet*entityPacket;} TailEntity;
static int pktGetOrdered(Packet*p){return p->ordered;}
static void pktSetOrdered(Packet*p,int x){p->ordered=x;}
static void pktFree(Packet*p){(void)p;}
static void append_source(Packet*pak,TailEntity*player_ent){
'''+append+'\n}\nstatic void finish_source(TailEntity*e){'+final+'}\n'
 code+=(HERE/'wrapper.h').read_text()
 pins={'whole_sources_sha256_lf':{p:sha(x.encode())for p,x in t.items()},'whole_functions_sha256_lf':funcs,'append_block_sha256_lf':sha(append.encode()),'final_statement_sha256':sha(final.encode()),'prepare_shell_sha256':sha(prepath.read_bytes())}
 expected=json.loads((HERE/'source-pins.json').read_text()) if (HERE/'source-pins.json').exists() else None
 if expected is not None and expected!=pins:raise ValueError('source changed')
 return code,pins

def build(root,work):
 code,pins=generate(root);path=work/'tail.c';path.write_text(code);subprocess.run(['cc','-std=gnu99','-O0','-w','-fPIC','-shared','-I'+str(root/'native-android/include'),path,'-o',work/'tail.so'],check=True)
 lib=C.CDLL(str(work/'tail.so'));lib.original_tail.argtypes=[C.c_uint]*4+[C.c_void_p]*4
 return lib,pins
