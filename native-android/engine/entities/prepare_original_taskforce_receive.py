#!/usr/bin/env python3
"""Generate whole unchanged taskforce receivers from pinned original sources."""
import argparse,hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def generate(root):
 spec=importlib.util.spec_from_file_location('taskforce_extract',HERE/'prepare_original_costume_receive.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 paths=['Game/src/entity/entrecv.c','Common/entity/costume.c','Common/entity/teamCommon.h'];pins=json.loads((HERE/'source-pins.json').read_text())['sha256_lf'];texts={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in paths}
 for p,t in texts.items():assert hashlib.sha256(t.encode()).hexdigest()==pins[p],p
 funcs=[(paths[1],'NPCcostume_receive'),(paths[0],'entRecieveTaskforceArchitectInfo'),(paths[0],'entReceiveTaskforceParameters')]
 result='/* Whole unchanged pinned original functions; local symbol/storage shims only. */\n'+''.join(m.extract(texts[p],n)for p,n in funcs)
 return result,{'sources_sha256_lf':{p:pins[p]for p in paths},'whole_functions_sha256_lf':{n:hashlib.sha256(m.extract(texts[p],n).encode()).hexdigest()for p,n in funcs},'generated_sha256':hashlib.sha256(result.encode()).hexdigest(),'legacy_shift_sanitizer_scope':'Only unchanged entReceiveTaskforceParameters is no_sanitize("shift"): source signed literal1<<31; adapter primitives remain instrumented.'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--check',action='store_true');a=p.parse_args();text,proof=generate(a.source_root);out=HERE/'original_taskforce_receive.inc'
 if a.check:assert out.read_text()==text
 else:out.write_text(text)
 print(json.dumps(proof))
