"""Offline original costume.bin reader/writer with bounded host memory adapters."""
import ctypes as C,hashlib,importlib.util,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def extract(t,n):
 m=re.search(r'^[^\n{};=()]+?\b'+re.escape(n)+r'\s*\([^;{}]*\)\s*(?://[^\n]*\n\s*)*\{',t,re.M)
 if not m:raise ValueError(n)
 at=m.end();depth=1
 while depth:depth+=(t[at]=='{')-(t[at]=='}');at+=1
 return t[m.start():at]+'\n'
def build(root,work):
 small=module('tree_original_small',HERE/'../costume-inputs/oracle.py');prior=work/'small';prior.mkdir();_,proof=small.build(root,prior);code=(prior/'original.c').read_text();src={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in small.PATHS};header=src['Common/gameData/costume_data.h'];costume=src['Common/gameData/costume_data.c'];token=src['libs/UtilitiesLib/src/utils/tokenstore.c']
 code=code.replace(extract(code,'original_decode'),'').replace(extract(code,'original_result_size'),'')
 old=re.search(r'typedef struct ColorPalette\b.*?}ColorPalette;',code,re.S).group();decl=header[header.index('typedef struct ColorPalette'):header.index('} CostumeMasterList;')+len('} CostumeMasterList;')];code=code.replace(old,decl)
 tables=[]
 for m in re.finditer(r'TokenizerParseInfo\s+(\w+)\s*\[\s*\]\s*=\s*\{.*?\n};',costume,re.S):
  if m.group(1)not in('ParseTailorCost','ParseTailorCostList'):tables.append((m.group(1),m.group()))
 old=re.search(r'TokenizerParseInfo ParseColor\[\].*?TokenizerParseInfo ParseColorPalette\[\].*?\n};',code,re.S).group();code=code.replace(old,'\n'.join(t for n,t in tables))
 code=code.replace('#define TOK_STRUCT(s,m,t)', '#define TOK_STRINGARRAY(s,m) TOK_INDIRECT|TOK_EARRAY|TOK_STRING_X,offsetof(s,m),0\n#define TOK_VEC3(s,m) TOK_FIXED_ARRAY|TOK_F32_X,offsetof(s,m),3\n#define TOK_STRUCT(s,m,t)')
 code=code.replace('size_t offset;','size_t storeoffset;').replace('t[c].offset','t[c].storeoffset')
 code=code.replace('typedef struct{char data[65536];int filesize,curposition;}SimpleBuffer;','typedef struct{char*data;int filesize,curposition,capacity;}SimpleBuffer;').replace('assert(n>=0&&n<=65536);','assert(n>=0&&n<=b->capacity);')
 begin=code.index('typedef struct{int size;void*items[256];}Vec;');end=code.index('int TokenStoreGetStorageType(',begin)
 adapters=(HERE/'storage_adapters.h').read_text();code=code[:begin]+adapters+'\n'+code[end:]
 # Execute whole original TokenStore string/pointer/capacity allocation handlers.
 functions={}
 for n in ('TokenStoreSetString','TokenStoreGetString','TokenStoreGetStringConst','TokenStoreSetCapacity','TokenStoreAlloc','TokenStoreGetPointer','TokenStoreGetPointerConst','TokenStoreGetNumElems'):
  f=extract(token,n);functions[n]=sha(f.encode());code+='\n'+f
 crc=module('tree_crc',HERE/'crc_provider.py');assert {p:sha((root/'upstream/ouroboros'/p).read_text().encode())for p in crc.PATHS}==json.loads((HERE/'source-pins.json').read_text());crc_code,crc_proof=crc.generate(root,src['libs/UtilitiesLib/src/utils/textparser.c'],extract);code+=crc_code
 projection=(HERE/'projection.h').read_text().replace('COH_TABLE_POINTERS',','.join(n for n,t in tables));code+='\n'+projection
 code+='\n'+(HERE/'tree_wrapper.h').read_text()
 # Every previously qualified original grammar function must remain byte-exact.
 for qualified,expected in proof['function_sha256_lf'].items():
  path,name=qualified.rsplit(':',1)
  assert sha(extract(code,name).encode())==expected,(name,'original function changed')
 (work/'original-tree.c').write_text(code);subprocess.run(['cc','-std=gnu99','-O0','-shared','-fPIC','-w','-I'+str((HERE/'../costume-inputs').resolve()),str(work/'original-tree.c'),'-lz','-lcrypto','-o',str(work/'original-tree.so')],check=True)
 return C.CDLL(str(work/'original-tree.so')),{'small_original_provider':proof,'crc_provider':crc_proof,'extra_tokenstore_function_sha256_lf':functions,'full_actual_table_sha256_lf':{n:sha(t.encode())for n,t in tables},'full_actual_declarations_sha256_lf':sha(decl.encode()),'generated_c_sha256':sha(code.encode()),'whole_original_engine_or_win32_abi':False,'preprocessor_or_shared_final_callbacks_executed':False}
