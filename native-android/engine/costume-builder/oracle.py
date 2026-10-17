"""Offline original primary-dictionary builder; ancillary interfaces explicit."""
import ctypes as C,hashlib,importlib.util,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def build(root,work):
 tree=module('full_tree_provider',HERE/'../costume-tree/tree_oracle.py');stash=module('stash_provider',HERE/'../stash32/oracle.py');a=work/'tree';b=work/'stash';a.mkdir();b.mkdir();_,tp=tree.build(root,a);_,sp=stash.build(root,b);code=(a/'original-tree.c').read_text();st=(b/'original.c').read_text().replace('allocations','stash_allocations');code+='\n'+st
 texts={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in ('libs/UtilitiesLib/src/components/StashTable.c','libs/UtilitiesLib/include/utilitieslib/components/StashTable.h','Common/gameData/costume_data.c','Common/entity/costume.h')};functions={};assert {p:tree.sha(t.encode())for p,t in texts.items()}==json.loads((HERE/'source-pins.json').read_text())
 def f(p,n):
  t=tree.extract(texts[p],n);functions[p+':'+n]=tree.sha(t.encode());return t
 sh=texts['libs/UtilitiesLib/include/utilitieslib/components/StashTable.h'];ch=texts['Common/entity/costume.h']
 declarations=re.search(r'#define STASH_DEEP_COPY_KEY_NAMES_BIT.*?} StashTableMode;',sh,re.S).group()+'\n'+re.search(r'typedef enum BodyType\s*\{.*?} BodyType;',ch,re.S).group()
 code+='\n'+declarations+'\n'+(HERE/'adapters.h').read_text().split('/* WHOLE_SOURCE_INSERTION */')[0]
 sc='libs/UtilitiesLib/src/components/StashTable.c';co='Common/gameData/costume_data.c'
 code+='\n'+''.join(f(sc,n)for n in ('stashSetMode','getKeyLength','stashTableCreateEx','stashTableCreateWithStringKeysEx','stashTableCreateIntEx'))
 code+='\n#define stashAddPointer source_stashAddPointer\n'+f(sc,'stashAddPointer')+'\n#undef stashAddPointer\n'
 code+='\n'+(HERE/'adapters.h').read_text().split('/* WHOLE_SOURCE_INSERTION */')[1]
 code+='\n'+f(sc,'stashAddPointerConst')+'\n#define stashIntAddInt source_stashIntAddInt\n'+f(sc,'stashIntAddInt')+'\n#undef stashIntAddInt\nstatic bool stashIntAddInt(StashTable p,int key,int value,bool overwrite){assert(p==costume_PaletteTable&&!overwrite);if(trace_mode)trace_integer((U32)key);return source_stashIntAddInt(p,key,value,overwrite);}'+'\n'+f(sc,'stashIntAddIntConst')
 code+='\n'+''.join(f(co,n)for n in ('costumePrefixFromGender','costumeBodyTypeFromGender','addPaletteToTables','s_addKeys','isRestrictedPart','costume_fillExtraData','costume_initHashTable'))
 code+='\n'+(HERE/'wrapper.h').read_text();(work/'builder.c').write_text(code)
 subprocess.run(['cc','-std=gnu99','-O0','-shared','-fPIC','-w','-I'+str(HERE/'../costume-inputs'),work/'builder.c','-lz','-lcrypto','-o',work/'builder.so'],check=True)
 return C.CDLL(str(work/'builder.so')),{'tree':tp,'stash':sp,'additional_whole_function_sha256_lf':functions,'source_sha256_lf':{p:tree.sha(t.encode())for p,t in texts.items()},'declarations_sha256':tree.sha(declarations.encode()),'generated_c_sha256':tree.sha(code.encode()),'ancillary_interfaces':'reward/tagged/geodata effects stubbed and explicitly excluded; primary constructor/add/find/hash/resize are original whole functions','Win32_ABI_executed':False,'source_ub4':'uint32_t','original_hash_sanitized':False}
