"""Original full attribute wire functions with explicit gameplay/dictionary shells."""
from pathlib import Path
import ctypes as C,hashlib,importlib.util,json,re,sys,subprocess,types,ast
HERE=Path(__file__).resolve().parent
EXTRA=['Common/entity/character_attribs.h','Common/entity/character_net.c','libs/UtilitiesLib/src/network/net_packetutil.c','Common/entity/entity_enum.h']
def sha(x):return hashlib.sha256(x).hexdigest()
def build(root,work):
 provider=HERE.parent/'character-outer-20261017'
 paths=ast.literal_eval(next(x.value for x in ast.parse((provider/'qualify_outer.py').read_bytes()).body if isinstance(x,ast.Assign)and any(isinstance(v,ast.Name)and v.id=='PATHS'for v in x.targets)))
 deps=[HERE/'oracle.py',HERE/'adapters.h',HERE/'wrapper.h',HERE/'ordered-rows.json',root/'native-android/tools/protocol_fixture/prepare.py',provider/'qualify_outer.py',provider/'independent.py']+[root/'upstream/ouroboros'/p for p in paths+EXTRA]
 start={str(p.relative_to(root)):sha(p.read_bytes())for p in deps}
 if (HERE/'source-pins.json').exists() and json.loads((HERE/'source-pins.json').read_text())!=start:raise ValueError('pre-import identity changed')
 def checked(name,path):
  body=path.read_bytes()
  if sha(body)!=start[str(path.relative_to(root))]:raise ValueError('checked helper changed')
  module=types.ModuleType(name);module.__file__=str(path);sys.modules[name]=module;exec(compile(body,str(path),'exec'),module.__dict__);return module
 checked('independent',provider/'independent.py');q=checked('attribute_outer_source',provider/'qualify_outer.py');q.ROOT=root
 # q.generate dynamically reads PREAMBLE; use admitted source bytes directly,
 # never a cached project pyc or an unpinned import loader.
 class Loader:
  def __init__(self,path):self.path=Path(path)
  def exec_module(self,module):module.__dict__.update(checked('attribute_bit_source',self.path).__dict__)
 q.importlib=types.SimpleNamespace(util=types.SimpleNamespace(spec_from_file_location=lambda name,path:types.SimpleNamespace(loader=Loader(path)),module_from_spec=lambda spec:types.ModuleType('attribute_bits')))

 src={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in q.PATHS+EXTRA};code,functions,_=q.generate(src);code=re.sub(r'\bEntity\b','OuterEntity',code)
 # PREAMBLE carries an unsupported pktSendBitsAuto stub; replace it with whole
 # original Auto producer/consumer below, retaining its exact source bins.
 code=re.sub(r'static void pktSendBitsAuto\([^\n]+\n','',code)
 attr=src['Common/entity/attrib_description.c'];h=src['Common/entity/attrib_description.h']
 code+=re.search(r'^#define MAX_COMBAT_STATS[^\n]+',h,re.M).group()+'\n'
 code+=re.search(r'typedef struct CharacterAttributes\s*\{.*?\}\s*CharacterAttributes;',src[EXTRA[0]],re.S).group()+'\n'
 code+=re.search(r'typedef enum EntType\s*\{.*?\}\s*EntType;',src[EXTRA[3]],re.S).group()+'\n'
 code+=(HERE/'adapters.h').read_text()
 code+=re.search(r'typedef enum AttribSource\s*\{.*?\}\s*AttribSource;',h,re.S).group()+'\n'+re.search(r'typedef struct AttribContributer\s*\{.*?\}\s*AttribContributer;',h,re.S).group()+'\n'
 for p,names in [(EXTRA[2],['pktSendBitsAuto','pktGetBitsAuto']),(EXTRA[1],['basepower_Send','basepower_Receive']),('Common/entity/attrib_description.c',['sendAllMatchingMods','sendAttribDescription','getAllMatchingMods','receiveAttribDescription'])]:
  for n in names:
   b=q.extract(src[p],n);functions[n]={'source':p,'sha256_lf':sha(b.encode())}
   if n=='getAllMatchingMods':code+='#define malloc fixture_contributor_allocate\n'
   code+=b
   if n=='getAllMatchingMods':code+='\n#undef malloc\n'
 rows=json.loads((HERE/'ordered-rows.json').read_text());assert rows['row_count']==69 and rows['category_count']==7
 init=[]
 for i,row in enumerate(rows['ordered_sender_rows']):init.append(f'descriptions[{i}].key={row["lookup_key"]};attrrows[{row["category"]}][{row["row"]}]=descriptions+{i};cats[{row["category"]}].count={row["category_rows"]};')
 code+='static void init_schema(void){memset(descriptions,0,sizeof(descriptions));'+''.join(init)+'for(unsigned i=0;i<7;i++){cats[i].ppAttrib=attrrows[i];catptrs[i]=cats+i;}g_AttribCategoryList.ppCategories=catptrs;}\n'
 code+=(HERE/'wrapper.h').read_text();(work/'full.c').write_text(code)
 subprocess.run(['cc','-std=c99','-O0','-fno-strict-aliasing','-w','-shared','-fPIC','-I'+str(root/'native-android/include'),work/'full.c','-o',work/'full.so'],check=True)
 lib=C.CDLL(str(work/'full.so'));lib.attribute_full.argtypes=[C.c_uint]*3+[C.c_void_p]*5
 assert start=={str(p.relative_to(root)):sha(p.read_bytes())for p in deps}
 return lib,{'source_sha256':start,'whole_functions':functions,'original_sources_sha256_lf':{p:sha(s.encode())for p,s in src.items()},'ordered_schema_sha256':sha((HERE/'ordered-rows.json').read_bytes()),'generated_c_sha256':sha(code.encode())}
