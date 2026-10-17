#!/usr/bin/env python3
"""Bounded normal GROUPS structural traversal against pinned source fixtures."""
from pathlib import Path
import argparse, importlib.util, json, os, subprocess, tempfile, hashlib

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
FIELDS='new_world files present_files defs removed_defs children roots removed_roots properties swaps raw_matrices packed_matrices strings string_bytes work_units max_def_id max_root_id footer_file_count footer_active_roots footer_defs_crc footer_refs_crc'.split()
def run(cmd,**kw):
    p=subprocess.run(cmd,text=True,capture_output=True,**kw)
    if p.returncode:raise RuntimeError(repr(cmd)+'\n'+p.stdout+p.stderr)
    return p
def header(fixtures,path):
    lines=['typedef struct { const char *name; const unsigned char *data; size_t bytes,bits; int compressed; CohStatus status; CohGroupsInspection expected; uint32_t expected_mask; } SourceFixture;\n']
    records=[]
    for index,item in enumerate(fixtures):
        data=bytes.fromhex(item['payload_hex']);bits=item['payload_bits'];mode=item['representation']
        if mode not in ('packed','byte_aligned') or bits>len(data)*8:raise ValueError('invalid source fixture')
        name='source_groups_'+str(index);lines.append('static const unsigned char '+name+'[]={'+','.join(map(str,data or b'\0'))+'};\n')
        expected=item.get('expected',{});unknown=set(expected)-set(FIELDS)-{'prefix_bits','consumed_bits'}
        if unknown:raise ValueError('unknown fixture expectations '+repr(unknown))
        values=[];mask=0
        for bit,key in enumerate(FIELDS):
            if key in expected:mask|=1<<bit
            values.append(str(expected.get(key,0))+'u')
        values+=['0','0']
        records.append('{'+json.dumps(item['name'])+','+name+','+str(len(data))+','+str(bits)+','+str(int(mode=='byte_aligned'))+','+str(item.get('expected_status',0))+',{'+','.join(values)+'},'+str(mask)+'u}')
    if not records:raise ValueError('no original producer fixtures')
    lines.append('static const SourceFixture source_fixtures[]={'+',\n'.join(records)+'};\n')
    lines.append('#define SOURCE_GROUPS_FIXTURES (sizeof(source_fixtures)/sizeof(source_fixtures[0]))\n')
    path.write_text(''.join(lines))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,default=REPO);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--output',type=Path);args=ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='coh-groups-') as d:
        directory=Path(d)
        spec=importlib.util.spec_from_file_location('coh_groups_original_oracle',HERE/'groups_oracle.py')
        oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
        fixtures,source_receipt=oracle.produce_fixtures(args.source_root.resolve(),directory)
        header(fixtures,directory/'groups_fixtures.h')
        modes=[('release',['-O2'])]
        if args.sanitize:modes += [('asan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=undefined','-fno-sanitize-recover=all'])]
        checks={}
        for name,flags in modes:
            binary=directory/name
            run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(directory),'-I'+str(HERE),str(HERE/'coh_replication.c'),str(HERE/'coh_groups.c'),str(HERE/'tests/test_groups_visit.c'),'-lm','-o',str(binary)])
            env=os.environ.copy();env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
            checks[name]=json.loads(run([str(binary)],env=env).stdout)
        proof={'source_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [HERE/'coh_groups.c',HERE/'coh_groups.h',HERE/'tests/test_groups_visit.c',Path(__file__)]},'schema':1,'passed':True,'scope':'allocation-free two-pass source-order event spans of synthetic normal GROUPS messages from pinned original producer; no real captured body','source_oracle':source_receipt,'fixtures':len(fixtures),'checks':checks,'body_max_bytes':4194304,'parser_allocates':False,'normal_scene_wire_grammar':True,'checksum_verified':False,'assets_resolved':False,'transforms_reconstructed':False,'entity_parser':False,'ready_or_character_ack':False,'authoritative_spawn':False,'actual_server_interoperability':False,'android_built':False,'emulator_qualified':False,'thor_accepted':False}
        if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(proof,indent=2)+'\n')
        print(json.dumps(proof,indent=2))
if __name__=='__main__':main()
