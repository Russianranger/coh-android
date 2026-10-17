#!/usr/bin/env python3
"""Render a new isolated nonshipping overlay tree. Never edit source or run server."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
FILES=['Common/gameData/costume_data.c','MapServer/src/svr/svr_init.c','Common/gameComm/initCommon.c']
def sha(b):return hashlib.sha256(b).hexdigest()
def configuration(meta):
 if set(meta)!={'generation','inventory_sha256','profile_sha256','run_sha256'}:raise ValueError('Metadata keys')
 if type(meta['generation'])is not int or not 0<meta['generation']<=0xffffffff:raise ValueError('Generation')
 text='static const U32 coh_costume_export_generation='+str(meta['generation'])+'u;\n'
 for field in ('inventory','profile','run'):
  value=meta[field+'_sha256']
  if not isinstance(value,str)or not re.fullmatch('[0-9a-f]{64}',value)or int(value,16)==0:raise ValueError('Identity '+field)
  text+='static const unsigned char coh_costume_export_'+field+'[32]={'+','.join(str(b)for b in bytes.fromhex(value))+'};\n'
 return text.encode()
def render(originals,meta):
 pins=json.loads((HERE/'source-pins.json').read_text())
 for name,data in originals.items():
  if sha(data.replace(b'\r\n',b'\n'))!=pins[name]:raise ValueError('Source pin '+name)
 name=FILES[1];old=b'    loadCostumes();\n    loadPowerCustomizations();';lf=originals[name].replace(b'\r\n',b'\n')
 if lf.count(old)!=1:raise ValueError('Hook')
 hook=b'    loadCostumes();\n    if(coh_source_costume_snapshot_startup()!=0) FatalErrorf("Nonshipping costume export failed");\n    loadPowerCustomizations();'
 output={name:b'/* NONSHIPPING: explicit standalone source dictionary capture. */\nextern int coh_source_costume_snapshot_startup(void);\n'+lf.replace(old,hook)}
 output[FILES[0]]=originals[FILES[0]].replace(b'\r\n',b'\n')+b'\n#if SERVER && !TEST_CLIENT\n#include "coh_source_costume_export.inc"\n#include "coh_source_costume_sink.inc"\n#endif\n'
 output['Common/gameData/coh_source_costume_export.inc']=(HERE/'source_costume_export.inc').read_bytes()
 output['Common/gameData/coh_source_costume_sink.inc']=(HERE/'source_costume_sink.inc').read_bytes()
 output['Common/gameData/coh_costume_export_source_id.inc']=(HERE/'source_id.inc').read_bytes()
 output['Common/gameData/coh_costume_export_configuration.inc']=configuration(meta)
 return output
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--metadata',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 source=a.source_root.resolve();out=a.output.resolve()
 if out.exists()or out==source or source in out.parents:raise ValueError('Fresh external output required')
 originals={name:(source/name).read_bytes()for name in FILES};meta=json.loads(a.metadata.read_text());output=render(originals,meta)
 # This produces overlay files only, NOT a buildable full source tree. Apply only
 # to a separately qualified disposable build; coordinator owns merge decisions.
 out.mkdir(parents=True)
 for name,data in output.items():
  path=out/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
 receipt={'schema':1,'passed':True,'role':'nonshipping_source_costume_dictionary_export_overlay_only','runtime_executed':False,'compiled_original_server':False,'actor_authority':False,'source_snapshot_only':True,'metadata':meta,'source_sha256':{n:sha(b)for n,b in originals.items()},'overlay_sha256':{n:sha(b)for n,b in output.items()},'maximum_output_bytes':4*1024*1024,'hook':'MapServer/src/svr/svr_init.c: immediately after original loadCostumes(), before loadPowerCustomizations()','source_untouched':True}
 (out/'costume-export-overlay.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
