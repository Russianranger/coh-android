#!/usr/bin/env python3
"""Emit unchanged bounded-source receiver functions; no packet-field rewrite."""
import argparse,hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def extract(text,name):
 m=re.search(r'^[^\n{};=()]+?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',text,re.M)
 if not m:raise ValueError(name)
 at=text.index('{',m.start())+1;depth=1
 while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[m.start():at]+'\n'
def generate(root):
 pins=json.loads((HERE/'source-pins.json').read_text())['sha256_lf']
 paths=['Common/entity/costume.c','Common/entity/costume.h','libs/UtilitiesLib/src/network/net_packetutil.c']
 texts={n:(root/'upstream/ouroboros'/n).read_text().replace('\r\n','\n')for n in paths}
 for n,v in texts.items():
  if sha(v.encode())!=pins[n]:raise ValueError('original source mismatch: '+n)
 c,h,u=[texts[n]for n in paths]
 if not re.search(r'#define\s+NUM_SG_COLOR_SLOTS\s+\(6\)',h)or'colorcache[30*4]'not in c or'stringcache[30*4]'not in c:raise ValueError('original constants')
 defs=[re.search(r'typedef enum BodyType\b.*?} BodyType;',h,re.S).group(),re.search(r'typedef struct BodyTypeInfo\b.*?} BodyTypeInfo;',h,re.S).group(),re.search(r'BodyTypeInfo g_BodyTypeInfos\[\]\s*=.*?\n};',c,re.S).group(),extract(c,'getBodyTypeCount')]
 funcs=[(u,'pktGetF'),(u,'pktGetIndexedString'),(u,'pktGetIndexedGeneric'),(c,'getCachedIndexedString'),(c,'getCachedIndexedColor'),(c,'costume_receive')]
 out='/* GENERATED from exact pinned LF source; regenerate with prepare_original_costume_receive.py. */\n'
 out+='#ifdef COH_ORIGINAL_COSTUME_TYPES\n'+'\n'.join(defs)+'\n#else\n'
 out+=extract(u,'pktGetF')+extract(u,'pktGetIndexedString')+extract(u,'pktGetIndexedGeneric')
 out+='#define pktGetIndexedString(p,t) observed_indexed_string((p),(t))\n'
 out+=extract(c,'getCachedIndexedString')+extract(c,'getCachedIndexedColor')
 out+='#define getCachedIndexedString(p) observed_cached_string((p))\n#define getCachedIndexedColor(p) observed_cached_color((p))\n'
 out+=extract(c,'costume_receive')+'#endif\n'
 proof={'schema':'coh-original-costume-receiver-source-v1','source_sha256_lf':{n:pins[n]for n in paths},'unchanged_whole_functions_sha256_lf':{n:sha(extract(t,n).encode())for t,n in funcs+[(c,'getBodyTypeCount')]},'bodytype_definitions_sha256_lf':sha('\n'.join(defs).encode()),'generated_sha256':sha(out.encode()),'wire_consumer':'whole unchanged costume_receive, not a source-order field rewrite','dictionary_capacity_or_slot_content_supplied':False}
 return out,proof
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--check',action='store_true');a=p.parse_args();text,proof=generate(a.source_root)
 for name,data in [('original_costume_receive.inc',text),('original-costume-receive-source.json',json.dumps(proof,indent=2)+'\n')]:
  path=HERE/name
  if a.check:assert path.read_text()==data,name
  else:path.write_text(data)
 print(json.dumps(proof))
if __name__=='__main__':main()
