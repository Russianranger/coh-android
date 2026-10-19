#!/usr/bin/env python3
"""Extend the existing source exporter with a DISABLED nonshipping body witness.

Fresh external overlay only. Never build, execute, modify or deploy a MapServer.
No generation is accepted: build/profile/run metadata are independently supplied
labels which must later be bound to an actual qualified source process.
"""
import argparse,hashlib,importlib.util,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
PREFIX='upstream/ouroboros/'
BODY='Common/gameData/BodyPart.c'
PARSER='libs/UtilitiesLib/src/utils/textparser.c'
SERVER='MapServer/src/svr/svr_init.c'
BODY_H='Common/gameData/BodyPart.h'
BONES_H='Common/seq/bones.h'
def sha(data):return hashlib.sha256(data).hexdigest()
def load(name):
 spec=importlib.util.spec_from_file_location('body_witness_'+name,HERE/(name+'.py'))
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def once(data,old,new):
 if data.count(old)!=1:raise ValueError('Witness hook changed: '+old[:80])
 return data.replace(old,new,1)
def identities(originals):
 pins=json.loads((HERE/'../body-catalog/struct-clear-source-pins.json').read_text())['files']
 expected={n:pins[PREFIX+n]['sha256']for n in (BODY,PARSER,BODY_H,BONES_H)}
 expected.update(json.loads((HERE/'source-pins.json').read_text()))
 for name,raw in originals.items():
  # Body/parser exact byte pins; older exporter pins are normalized LF.
  value=sha(raw if name in (BODY,PARSER,BODY_H,BONES_H)else raw.replace(b'\r\n',b'\n'))
  if value!=expected[name]:raise ValueError('Source pin '+name)
 return{n:expected[n]for n in originals}
def configuration(meta,source):
 if set(meta)!={'build_sha256','profile_sha256','run_sha256'}:raise ValueError('Metadata keys; no generation may be supplied')
 text='/* Metadata labels, never authenticated runtime identities. */\n'
 for key,value in [('source_sha256',source),*meta.items()]:
  if not isinstance(value,str)or not re.fullmatch('[0-9a-f]{64}',value)or int(value,16)==0:raise ValueError('Identity '+key)
  text+='static const unsigned char coh_body_witness_'+key.removesuffix('_sha256')+'[32]={'+','.join(map(str,bytes.fromhex(value)))+'};\n'
 return text.encode()
def render(originals,meta,costume_meta=None):
 pins=identities(originals)
 required={BODY,PARSER,SERVER,BODY_H,BONES_H}
 if not required.issubset(originals):raise ValueError('Missing source')
 output=load('stage').render({n:originals[n]for n in load('stage').FILES},costume_meta)if costume_meta is not None else {}
 body=originals[BODY].decode().replace('\r\n','\n')
 body=once(body,'void bpReadBodyPartFiles(void)\n{','int GetBodyPartCount(void);\n#include "coh_source_body_witness.inc"\n#include "coh_source_body_witness_sink.inc"\nvoid bpReadBodyPartFiles(void)\n{\n    coh_body_witness_begin(&bodyPartList);')
 call='    ParserLoadFilesShared("SM_BodyParts.bin", "Defs\\\\UI", ".bp", "BodyParts.bin", 0, ParseBodyPartBegin, &bodyPartList, sizeof(bodyPartList), NULL, NULL, ParseBoneNames, NULL, NULL);'
 body=once(body,call,call+'\n    coh_body_witness_end();')
 output[BODY]=body.encode()
 parser=originals[PARSER].decode().replace('\r\n','\n')
 declaration='''/* NONSHIPPING body witness; exact active root filters every event. */
extern void coh_source_body_witness_route(const void*,unsigned,unsigned);
extern void coh_source_body_witness_located(const void*,const char*);
extern int coh_source_body_witness_binary(const void*,int);
'''
 parser=declaration+parser
 parser=once(parser,'        path = fileLocateRead(persistfilepath, buf);','        path = fileLocateRead(persistfilepath, buf);\n        if(path)coh_source_body_witness_located(structptr,path);')
 parser=once(parser,'if (ParserReadBinaryFile(binfile, persistfilepath, pti, structptr, NULL, globaldefines)) {','if (coh_source_body_witness_binary(structptr,ParserReadBinaryFile(binfile, persistfilepath, pti, structptr, NULL, globaldefines))) {')
 parser=once(parser,'    // otherwise, we have to load from text files','    coh_source_body_witness_route(structptr,3,1);\n    // otherwise, we have to load from text files')
 parser=once(parser,'    shared_memory_status = sharedMemoryAcquire(&shared_memory, sharedMemoryName);','    shared_memory_status = sharedMemoryAcquire(&shared_memory, sharedMemoryName);\n    coh_source_body_witness_route(structptr,1,shared_memory_status==SMAR_DataAcquired?1u:shared_memory_status==SMAR_Error?2u:shared_memory_status==SMAR_FirstCaller?3u:4u);')
 # Insert only into this exact original shared function, never another return.
 spec=importlib.util.spec_from_file_location('body_loader',(HERE/'../body-catalog/body_part_loader_provider.py'))
 provider=importlib.util.module_from_spec(spec);spec.loader.exec_module(provider)
 function=provider.extract(parser,'ParserLoadFilesShared')
 suffix='    return ret;\n}'
 changed=once(function,suffix,'    coh_source_body_witness_route(structptr,4,ret?2u:1u);\n'+suffix)
 parser=once(parser,function.rstrip('\n'),changed.rstrip('\n'))
 output[PARSER]=parser.encode()
 server=output.get(SERVER,originals[SERVER]).decode().replace('\r\n','\n')
 server='/* NONSHIPPING body witness observer only. */\nextern int coh_source_body_witness_snapshot_startup(void);\n'+server
 server=once(server,'    loadCostumes();','    loadCostumes();\n    if(coh_source_body_witness_snapshot_startup()!=0) FatalErrorf("Nonshipping body witness failed");')
 output[SERVER]=server.encode()
 source=sha(json.dumps(pins,sort_keys=True,separators=(',',':')).encode())
 output['Common/gameData/coh_body_witness_configuration.inc']=configuration(meta,source)
 for local in ('source_body_witness.inc','source_body_witness_sink.inc'):
  output['Common/gameData/coh_'+local]=(HERE/local).read_bytes()
 return output,{'schema':'coh-nonshipping-body-witness-overlay-v1','source_sha256':{n:sha(b)for n,b in originals.items()},'source_closure_id':source,'metadata':meta,'overlay_sha256':{n:sha(b)for n,b in output.items()},'runtime_executed':False,'server_compiled':False,'runtime_generation_admitted':False,'actor_or_ack_authority':False,'enabled_by_default':False,'source_unchanged':True,'maximum_body_witness_payload_bytes':65536,'stack_reserve_bytes':4096,'allocations':0,'missing_boundary':'Actual instrumented source-process execution, executable/profile/run attestation, coherent selected Map/session and original load-generation owner; exact selected cache bytes/freshness or shared-segment provenance remain independently required.'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--metadata',type=Path,required=True);p.add_argument('--costume-metadata',type=Path);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
 root=args.source_root.resolve();out=args.output.resolve()
 if out.exists()or root==out or root in out.parents:raise ValueError('Fresh external output required')
 names={BODY,PARSER,SERVER,BODY_H,BONES_H}
 if args.costume_metadata:names.update(load('stage').FILES)
 originals={n:(root/n).read_bytes()for n in sorted(names)}
 output,receipt=render(originals,json.loads(args.metadata.read_text()),json.loads(args.costume_metadata.read_text())if args.costume_metadata else None)
 out.mkdir(parents=True)
 for name,data in output.items():target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 (out/'body-witness-overlay.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({'passed':True,'runtime_executed':False,'output':str(out)}))
if __name__=='__main__':main()
