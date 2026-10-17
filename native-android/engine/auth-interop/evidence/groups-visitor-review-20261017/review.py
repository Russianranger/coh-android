#!/usr/bin/env python3
"""Read-only pinned visitor source/receipt review; no corpus execution."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

COMMIT='0ecb84df0d210b5186a337f0cd67449d647c2a0f'
BASE='native-android/engine/replication/'


def extract(source,name):
    match=re.search(r'^[\w \t*]+\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',source,re.M)
    at=source.index('{',match.start())+1;depth=1
    while depth:depth+=(source[at]=='{')-(source[at]=='}');at+=1
    return source[match.start():at]+'\n'


def review(root):
    def blob(path,commit=COMMIT):return subprocess.check_output(['git','-C',str(root),'show',commit+':'+path],timeout=30)
    def digest(data):return hashlib.sha256(data).hexdigest()
    visitor=json.loads(blob(BASE+'evidence/groups-visitor-host.json'))
    inspector=json.loads(blob(BASE+'evidence/groups-visitor-inspector-regression.json'))
    for path,expected in visitor['source_sha256'].items():assert digest(blob(path))==expected
    pins=json.loads(blob(BASE+'groups-source-pins.json'));sources={}
    for name,expected in pins['sha256_lf'].items():
        source=blob('upstream/ouroboros/'+name).replace(b'\r\n',b'\n').decode();assert digest(source.encode())==expected;sources[name]=source
    for name,value in pins['functions'].items():assert digest(extract(sources[value['source']],name).encode())==value['sha256_lf']
    baseline=json.loads(blob(BASE+'evidence/groups-source-oracle-017.json'))
    assert visitor['source_oracle']==inspector['source_oracle']==baseline
    assert baseline['source_pin_sha256']==digest(blob(BASE+'groups-source-pins.json'))
    for mode in ('release','asan','ubsan'):
        assert visitor['checks'][mode]=={'passed':True,'checks':147088,'fixtures':44,'world_authority':False}
        assert inspector['checks'][mode]=={'checks':2473492,'negative':172422,'every_bit_truncations':138722,'sampled_large_truncations':1028,'fuzz_cases':40000,'source_fixtures':44,'allocations':0,'deallocations':0}
    unchanged=['coh_replication.c','coh_replication.h','groups_oracle.py','groups_check.py','tests/test_groups.c','groups-source-pins.json','tests/groups_oracle_harness.c','tests/groups_oracle_shim.h']
    for name in unchanged:assert blob(BASE+name)==blob(BASE+name,COMMIT+'^')
    current=blob(BASE+'coh_groups.c').decode();old=blob(BASE+'coh_groups.c',COMMIT+'^').decode()
    assert extract(current,'coh_rep_groups')==extract(old,'coh_rep_groups')
    return {'schema':'coh-groups-visitor-independent-source-review-v1','reviewed_commit':COMMIT,'approved_for_standalone_observation_scope':True,
            'source_sha256':{BASE+name:digest(blob(BASE+name)) for name in ['coh_groups.c','coh_groups.h','check_groups_visit.py','tests/test_groups_visit.c',*unchanged]},
            'receipt_sha256':{name:digest(blob(BASE+name)) for name in ['evidence/groups-visitor-host.json','evidence/groups-visitor-inspector-regression.json']},
            'original_source_blobs_verified':len(sources),'original_function_pins_verified':len(pins['functions']),
            'prior_inspector_function_body_unchanged':True,'prior_inspector_dependencies_unchanged':True,'source_oracle_receipts_equal_prior_standalone':True,
            'reported_visitor_checks_per_mode':147088,'reported_inspector_checks_per_mode':2473492,'test_modes':['release','asan','ubsan'],
            'tests_rerun_by_reviewer':False,'expensive_corpus_rerun':False,
            'manual_findings':['Complete structural preflight finishes before any event; malformed/unsupported/truncated input produces no callbacks.',
              'Second walk uses the same bounded grammar; event spans retain exact input and representation with exclusive bit end. File order1..N-1,0 and original definition/root slots preserved.',
              'Pairwise control/input overlap and uintptr range overflow rejected; finite source count/string/work limits still apply to each pass. Caller must account both passes and callback scratch.',
              'Callback refusal stops immediately and preserves reader/inspection; external staged callback data must be discarded by owner on any error.',
              'Callback-local event/span views cannot be retained; input must remain immutable and callback context/opaque allocations must not mutate controls/input. These are trusted caller obligations, not a callback sandbox.',
              'No allocation, graph ownership, generation binding, CRC verification, asset resolution, READY or authoritative publication is introduced.'],
            'remaining_scope':['Live GROUPS/source generation binder is outside this review.','No Android/emulator/Thor or authentic live-server acceptance inferred.'],
            'blocking_findings':[]}


if __name__=='__main__':
    root=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],text=True).strip())
    value=review(root);value['reviewer_script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    Path(__file__).with_name('review.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({'approved':value['approved_for_standalone_observation_scope'],'source_blobs':value['original_source_blobs_verified'],'function_pins':value['original_function_pins_verified'],'tests_rerun':False}))
