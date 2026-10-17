"""Observe separately qualified original child writes without editing bodies.

Source function tokens are unchanged under an explicit symbol-rename macro;
fixture-only wrappers observe the original writer cursor before and after calls.
This is not an original enclosing engine execution or actor fixture.
"""
import ctypes as C,hashlib,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
SPECS={
 'base':[(18,'entSendPetInfo','Packet*pak,Entity*e','pak,e','pak'),(19,'entSendAfk','Packet*pak,Entity*e,int flag','pak,e,flag','pak')],
 'costume':[(16,'entSendTaskforceArchitectInfo','Entity*e,Packet*pak','e,pak','pak'),(17,'entSendTaskforceParameters','TaskForce*tf,Packet*pak','tf,pak','pak')],
 'tail':[(20,'entSendOtherSupergroupInfo','Packet*pak,Entity*e,int update,int self','pak,e,update,self','pak'),(21,'entSendLevelingpactInfo','Packet*pak,Entity*e,int update','pak,e,update','pak'),(22,'entSendLogoutUpdate','Packet*pak,Entity*e,int update','pak,e,update','pak')]
}
def extract(text,name):
 m=re.search(r'^[^\n{};]+?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',text,re.M)
 if not m:raise ValueError('missing function '+name)
 pos=text.index('{',m.start())+1;depth=1
 while depth:depth+=(text[pos]=='{')-(text[pos]=='}');pos+=1
 return text[m.start():pos]+'\n'
def instrument(code,kind):
 records=[]
 for ident,name,params,args,pak in SPECS[kind]:
  body=extract(code,name)
  if code.count(body)!=1:raise ValueError('ambiguous source function '+name)
  replacement='#define '+name+' selected_original_'+name+'\n'+body+'#undef '+name+'\n'
  replacement+='static void '+name+'('+params+'){selected_leaf_positions['+str(ident)+'][0]=bsGetCursorBitPosition(&'+pak+'->stream);selected_original_'+name+'('+args+');selected_leaf_positions['+str(ident)+'][1]=bsGetCursorBitPosition(&'+pak+'->stream);}\n'
  code=code.replace(body,replacement);records.append({'id':ident,'function':name,'original_function_sha256_lf':hashlib.sha256(body.encode()).hexdigest()})
 return 'static unsigned selected_leaf_positions[24][2];\n'+code+'\nvoid selected_leaf_bounds(unsigned id,unsigned*out){assert(id<24);out[0]=selected_leaf_positions[id][0];out[1]=selected_leaf_positions[id][1];}\n',records
def build(root,work,kind,source):
 original=Path(source).read_text();code,functions=instrument(original,kind)
 if kind in('base','costume'):
  # Only synthetic fixture wrappers change. Original serializer/consumer bodies
  # stay byte-identical. Replay all bit offsets before declaring relocation.
  for name in(('original_envelope','original_power_custom','original_taskforce')if kind=='costume'else('original_stats','original_target','original_inventory')):
   body=extract(code,name);changed=body;needle='initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);'
   if changed.count(needle)!=1:raise ValueError('fixture writer init changed '+name)
   changed=changed.replace(needle,needle+'if(selected_fixture_prefix)pktSendBits(&p,selected_fixture_prefix,0);')
   needle='p.stream.mode=Read;p.stream.cursor.byte=p.stream.cursor.bit=0;'
   if changed.count(needle)!=(1 if kind=='costume'else 0):raise ValueError('fixture consumer init changed '+name)
   changed=changed.replace(needle,'p.stream.mode=Read;p.stream.cursor.byte=selected_fixture_prefix/8;p.stream.cursor.bit=selected_fixture_prefix%8;')
   code=code.replace(body,changed)
  code='static unsigned selected_fixture_prefix;\n'+code+'\nvoid selected_set_fixture_prefix(unsigned prefix){assert(prefix<8);selected_fixture_prefix=prefix;}\n'
 path=work/(kind+'-leaves.c');path.write_text(code);binary=work/(kind+'-leaves.so')
 subprocess.run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),'-I'+str(HERE/'../entities'),path,'-lm','-Wl,-z,defs','-o',binary],check=True)
 lib=C.CDLL(str(binary));lib.selected_leaf_bounds.argtypes=[C.c_uint,C.c_void_p]
 return lib,{'functions':functions,'generated_input_sha256':hashlib.sha256(original.encode()).hexdigest(),'generated_instrumented_sha256':hashlib.sha256(code.encode()).hexdigest(),'scope':'Original whole named writer bodies symbol-renamed only. Fixture wrappers observe exact child cursor spans and explicitly prepend bit offsets/reset their consumer cursors; original producer functions execute. No change to original serializer/consumer source statements.'}
def span(lib,ident,wire):
 positions=(C.c_uint*2)();lib.selected_leaf_bounds(ident,positions);begin,end=positions
 if end<begin or end>len(wire)*8:raise ValueError('invalid recorded span')
 out=bytearray((end-begin+7)//8)
 for j,i in enumerate(range(begin,end)):out[j//8]|=((wire[i//8]>>(i%8))&1)<<(j%8)
 return bytes(out),end-begin,begin%8
