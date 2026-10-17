#!/usr/bin/env python3
"""Qualify immutable authentic cached-header/raw-trick SOURCE INPUTS, not TexBinds."""
import argparse,hashlib,importlib.util,json,os,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def oracle(tex,header,fix):
 a=tex.index('//Get bind->dir_name, and bind->name');b=tex.index('    if (!stashFindElement',a);block=tex[a:b]
 start=header.index('typedef struct {');end=header.index('} TextureFileHeader;',start)+len('} TextureFileHeader;');definition=header[start:end]
 prefix='''#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#define TEX_TGA 1
#define TEX_JPEG 2
#define TEX_DDS 4
typedef unsigned TexOptFlags;typedef float F32;typedef unsigned char U8;
static void strncpyt(char*d,const char*s,int n){assert(n>0&&strlen(s)<(unsigned)n);memcpy(d,s,strlen(s)+1);}
static unsigned fold(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static char*strstri(const char*s,const char*key){for(;*s;s++){unsigned i=0;while(key[i]&&s[i]&&fold((unsigned char)s[i])==fold((unsigned char)key[i]))i++;if(!key[i])return(char*)s;}return NULL;}
'''
 code=prefix+definition+'\n_Static_assert(sizeof(TextureFileHeader)==32,"original cached header size");\n_Static_assert(offsetof(TextureFileHeader,flags)==16&&offsetof(TextureFileHeader,alpha)==28,"original cached offsets");\n'+fix+'\n'
 code+='''void original_cache_name(const char*original,char directory[256],char key[128]){
 char name_buffer[256],buf[1000],*name=name_buffer,*s;const char*basefolder="texture_library";
 struct {char*dirname;unsigned flags;} storage={0},*bind=&storage;
 assert(strlen(original)<sizeof(name_buffer));strcpy(name_buffer,original);
#define allocAddString(s) (strcpy(directory,s),directory)
'''+block+'''\n strcpy(key,s);
#undef allocAddString
}
'''
 return code,hashlib.sha256(block.encode()).hexdigest()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--actual-box',required=True,type=Path);p.add_argument('--actual-bar',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
 if a.output.exists():raise ValueError('Fresh output required')
 pins=json.loads((HERE/'tex-inputs-authentic-pins.json').read_text());boxpin=json.loads((HERE/'sampler-authentic-pins.json').read_text())['payload']
 for path,item in [(a.actual_box,boxpin),(a.actual_bar,pins['bar'])]:
  if path.stat().st_size!=item['bytes'] or sha(path)!=item['sha256']:raise ValueError('Exact actual cached body pin differs')
 original=module('tex_input_original_name',HERE/'check_texname.py');source_pins=json.loads((HERE/'tex-inputs-source-pins.json').read_text())
 for path,h in source_pins['source_sha256'].items():
  if sha(ROOT/path)!=h:raise ValueError('Original source differs '+path)
 rawpin=source_pins['raw_trick_git'];raw_trick=original.run(['git','-C',ROOT,'show','HEAD:'+rawpin['path']])
 if hashlib.sha256(raw_trick).hexdigest()!=rawpin['sha256'] or len(raw_trick)!=rawpin['bytes'] or original.run(['git','-C',ROOT,'rev-parse','HEAD:'+rawpin['path']]).decode().strip()!=rawpin['blob']:raise ValueError('Exact original raw trick source differs')
 tex=(ROOT/'upstream/ouroboros/Game/src/render/tex.c').read_text();header=(ROOT/'upstream/ouroboros/Game/src/render/tex.h').read_text();fix=original.extract(tex,'static int texFixName(');code,block_sha=oracle(tex,header,fix)
 sources=[HERE/'tests/test_tex_inputs.c',HERE/'coh_wr_tex_inputs.c',HERE/'coh_wr_texname_guarded.c',HERE.parent/'assets/coh_asset_loader.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
 deps=[*sources,HERE/'coh_wr_tex_inputs.h',HERE/'coh_wr_texname_guarded.h',HERE/'coh_wr_texname.h',HERE/'check_tex_inputs.py',HERE/'check_texname.py',HERE/'tex-inputs-authentic-pins.json',HERE/'tex-inputs-source-pins.json',HERE/'sampler-authentic-pins.json',HERE/'acquire_tex_inputs.py',HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/src/byte_reader.h',*[ROOT/x for x in source_pins['source_sha256']]]
 hashes={str(x.relative_to(ROOT)):sha(x) for x in deps};results={}
 with tempfile.TemporaryDirectory(prefix='coh-tex-inputs-') as directory:
  t=Path(directory);(t/'original.c').write_text(code);(t/'actual-raw-trick.txt').write_bytes(raw_trick)
  flags=['-std=c11','-Wall','-Wextra','-Werror','-pedantic','-I',ROOT/'native-android/include']
  for mode,extra in [('release',['-O2']),('address',['-O1','-g','-fsanitize=address','-no-pie']),('undefined',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   original.run(['cc',*flags,*extra,*sources,t/'original.c','-Wl,--wrap=calloc','-lz','-lcrypto','-lm','-o',t/mode]);results[mode]=json.loads(original.run([t/mode,a.actual_box,a.actual_bar,t/'actual-raw-trick.txt'],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
 if hashes!={str(x.relative_to(ROOT)):sha(x) for x in deps} or sha(a.actual_box)!=boxpin['sha256'] or sha(a.actual_bar)!=pins['bar']['sha256'] or original.run(['git','-C',ROOT,'show','HEAD:'+rawpin['path']])!=raw_trick:raise ValueError('Inputs changed')
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({'passed':True,'source_revision':original.run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_inputs_unchanged':True,'source_sha256':hashes,'raw_trick_git':rawpin,'unchanged_cache_name_block_sha256_lf':block_sha,'unchanged_original_texFixName_sha256_lf':hashlib.sha256(fix.encode()).hexdigest(),'modes':results,'actual_box_sha256':boxpin['sha256'],'actual_bar_sha256':pins['bar']['sha256'],'basic_texture_created':False,'texbind_created':False,'raw_tricks_parsed':False,'source_generation_established':False,'asset_generation_permit':False,'material_authority':False,'world_authority':False,'android_execution':False},indent=2)+'\n');print(json.dumps({'passed':True,'modes':results}))
if __name__=='__main__':main()
