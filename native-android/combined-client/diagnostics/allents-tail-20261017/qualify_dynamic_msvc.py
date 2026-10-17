"""Tiny source-pinned MSVC x86 DynGroupStatus ABI probe; no server builds/services.
Run in an existing VS x86 native-tools environment. Builds only the generated
standalone probe and preserves all output in a new, private directory.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,struct,subprocess
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
SOURCE_PIN='767d55e48fa35261f1428bd542aa6cd3b2b9fa32'
PATHS=['Common/group/groupdyn.h','libs/UtilitiesLib/include/utilitieslib/stdtypes.h']
def sha(raw):return hashlib.sha256(raw).hexdigest()
def source(root,path):return (root/'upstream/ouroboros'/path).read_bytes().decode('utf-8').replace('\r\n','\n')
def generate(texts):
 header,types=[texts[p] for p in PATHS]
 u8=re.search(r'^typedef unsigned char U8;',types,re.M).group(0)
 macros=[re.search(r'^#define '+n+r'[^\n]+',header,re.M).group(0) for n in ['GRPDYN_HP_BITS','GRPDYN_REPAIR_BITS']]
 declaration=re.search(r'typedef struct\s*\{\s*U8\s+hp\s*:.*?\}\s*DynGroupStatus;',header,re.S).group(0)
 fragments={'u8_sha256_lf':sha(u8.encode()),'macros_sha256_lf':sha(('\n'.join(macros)+'\n').encode()),'typedef_sha256_lf':sha(declaration.encode())}
 code='''#include <stdio.h>
#include <string.h>
#if !defined(_MSC_VER) || defined(__clang__) || !defined(_WIN32) || !defined(_M_IX86)
#error This qualification requires actual MSVC targeting Windows x86.
#endif
#ifndef _MSC_BUILD
#define _MSC_BUILD 0
#endif
'''+u8+'\n'+'\n'.join(macros)+'\n#pragma warning(push)\n#pragma warning(disable:4214) /* Original U8 bitfield extension, retained verbatim. */\n'+declaration+'\n#pragma warning(pop)\n'+'''
typedef char require_status_size_1[(sizeof(DynGroupStatus)==1)?1:-1];
typedef char require_pointer_size_4[(sizeof(void*)==4)?1:-1];
int main(void){
 unsigned i;char hex[513];static const char digits[]="0123456789abcdef";
 for(i=0;i<256;i++){
  DynGroupStatus value;unsigned char raw;memset(&value,0,sizeof(value));
  value.hp=(unsigned char)(i&127u);value.repair=(unsigned char)(i>>7);
  memcpy(&raw,&value,1);
  if((unsigned)raw!=i)return 20;
  hex[i*2]=digits[raw>>4];hex[i*2+1]=digits[raw&15u];
  raw=(unsigned char)i;memcpy(&value,&raw,1);
  if((unsigned)value.hp!=(i&127u)||(unsigned)value.repair!=(i>>7))return 21;
 }
 hex[512]=0;
 printf("{\\"passed\\":true,\\"patterns\\":256,\\"reverse_patterns\\":256,\\"status_bytes\\":%u,\\"pointer_bytes\\":%u,\\"msc_ver\\":%u,\\"msc_full_ver\\":%u,\\"msc_build\\":%u,\\"m_ix86\\":%u,\\"native_bytes_hex\\":\\"%s\\"}\\n",(unsigned)sizeof(DynGroupStatus),(unsigned)sizeof(void*),(unsigned)_MSC_VER,(unsigned)_MSC_FULL_VER,(unsigned)_MSC_BUILD,(unsigned)_M_IX86,hex);
 return 0;
}
'''
 return code,fragments

def pe_x86(raw):
 if len(raw)<64 or raw[:2]!=b'MZ':raise ValueError('probe is not PE')
 at=struct.unpack_from('<I',raw,60)[0]
 if at>len(raw)-26 or raw[at:at+4]!=b'PE\0\0' or struct.unpack_from('<H',raw,at+4)[0]!=0x14c or struct.unpack_from('<H',raw,at+24)[0]!=0x10b:raise ValueError('probe is not Windows x86 PE32')
 return True

def validate(result):
 if result.get('passed') is not True or any(type(result.get(k))is not int for k in ['patterns','reverse_patterns','status_bytes','pointer_bytes','msc_ver','msc_full_ver','msc_build','m_ix86']):raise ValueError('compiler/result fields')
 if [result[k] for k in ['patterns','reverse_patterns','status_bytes','pointer_bytes']]!=[256,256,1,4] or result['msc_ver']<1900 or result['msc_full_ver']<result['msc_ver'] or result['m_ix86']<300:raise ValueError('MSVC x86 qualification result')
 if result.get('native_bytes_hex')!=bytes(range(256)).hex():raise ValueError('native bitfield bytes')
 return True

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--cl',default='cl.exe');p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
 texts={n:source(a.source_root,n) for n in PATHS};pins={n:sha(s.encode()) for n,s in texts.items()}
 if pins!=json.loads((HERE/'dynamic-msvc-source-pins.json').read_text()):raise ValueError('original source pins changed')
 code,fragments=generate(texts);a.output.mkdir(parents=True,exist_ok=False);output=a.output.resolve();(output/'probe.c').write_text(code,encoding='utf-8',newline='\n')
 identity={'schema':'coh-dynamic-msvc-x86-layout-v1','source_pin':SOURCE_PIN,'original_source_sha256_lf':pins,'source_fragments':fragments,'generated_c_sha256':sha(code.encode()),'helper_sha256':sha(Path(__file__).read_bytes()),'mapserver_rebuilt':False,'service_or_probe_binaries_rebuilt':False,'live_status_or_world_authority':False}
 if a.prepare_only:
  (output/'prepared.json').write_text(json.dumps({**identity,'prepared':True,'compiled':False,'executed':False,'actual_msvc_qualified':False},indent=2)+'\n');return
 if os.name!='nt' or os.environ.get('VSCMD_ARG_TGT_ARCH','').lower()!='x86':raise ValueError('requires existing Windows VS x86 tools environment')
 compiler=shutil.which(a.cl)
 if not compiler or Path(compiler).name.lower()!='cl.exe':raise ValueError('actual cl.exe unavailable')
 args=[compiler,'/nologo','/Bv','/W4','/WX','/TC','/Od','probe.c','/Fe:probe.exe','/Fo:probe.obj','/link','/MACHINE:X86']
 with (output/'compile.log').open('xb') as log:
  run=subprocess.run(args,cwd=output,stdout=log,stderr=subprocess.STDOUT,timeout=120)
 if run.returncode:raise RuntimeError('MSVC probe compilation failed; preserved compile.log')
 binary=(output/'probe.exe').read_bytes();pe_x86(binary)
 run=subprocess.run([str(output/'probe.exe')],cwd=output,capture_output=True,timeout=30)
 (output/'execution.stdout').write_bytes(run.stdout);(output/'execution.stderr').write_bytes(run.stderr)
 if run.returncode:raise RuntimeError('MSVC probe execution failed; outputs preserved')
 result=json.loads(run.stdout);validate(result)
 if pins!={n:sha(source(a.source_root,n).encode()) for n in PATHS} or sha((output/'probe.c').read_bytes())!=identity['generated_c_sha256']:raise ValueError('source changed')
 receipt={**identity,'passed':True,'compiled':True,'executed':True,'actual_msvc_qualified':True,'actual_compiler_path':compiler,'actual_compiler_sha256':sha(Path(compiler).read_bytes()),'compiler_log_sha256':sha((output/'compile.log').read_bytes()),'probe_pe_sha256':sha(binary),'probe_object_sha256':sha((output/'probe.obj').read_bytes()),'pe_machine':0x14c,'compiler_environment_target':os.environ['VSCMD_ARG_TGT_ARCH'],'result':result}
 (output/'qualification.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':True,'actual_msvc_qualified':True,'pe_machine':0x14c,'patterns':256}))
if __name__=='__main__':main()
