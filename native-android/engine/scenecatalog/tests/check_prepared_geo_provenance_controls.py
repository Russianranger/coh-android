#!/usr/bin/env python3
"""Offline mutation controls for the read-only prepared GEO provenance witness."""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

path=Path(__file__).resolve().parents[1]/'check_prepared_geo_provenance.py'
spec=importlib.util.spec_from_file_location('prepared_geo_provenance',path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p=argparse.ArgumentParser()
for name in ('source-root','evidence','candidates','visual-manifest','body-directory','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();baseline=m.inspect(a);checks=1

def refuse(args,code):
    global checks
    try:m.inspect(args)
    except ValueError as e:
        assert str(e)==code,(str(e),code);checks+=1
    else:raise AssertionError('unexpected witness')

with tempfile.TemporaryDirectory(prefix='coh-geo-route-controls-') as td:
    td=Path(td)
    for field,code in [('candidates','CANDIDATE_PIN'),('visual_manifest','VISUAL_PIN')]:
        bad=td/field;bad.write_text('{}');fields=vars(a).copy();fields[field]=bad;refuse(SimpleNamespace(**fields),code)
    # A changed actual fixture/receipt cannot preserve the sealed digest.
    for rel,code in [('control-fixture.json','FIXTURE_PIN'),('capture/capture-receipt.json','CAPTURE_RECEIPT_PIN')]:
        target=td/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_text('{}')
        fields=vars(a).copy();fields['evidence']=td
        if rel.startswith('capture/'):
            (td/'control-fixture.json').write_bytes((a.evidence/'control-fixture.json').read_bytes())
        refuse(SimpleNamespace(**fields),code)
    fields=vars(a).copy();fields['body_directory']=td;refuse(SimpleNamespace(**fields),'BODY_SIZE')
    # Changes in underlying original/donor source cannot use old review hashes.
    original=m.blob
    with patch.object(m,'blob',side_effect=lambda root,rev,name: original(root,rev,name)+b'x' if rev==m.REV else original(root,rev,name)):
        refuse(a,'ORIGINAL_SOURCE_PIN')
    with patch.object(m,'blob',side_effect=lambda root,rev,name: original(root,rev,name)+b'x' if rev==m.DONOR else original(root,rev,name)):
        refuse(a,'DONOR_SOURCE_PIN')
result={'passed':True,'checks':checks,'body_count':baseline['body_count'],'body_bytes':baseline['body_bytes'],'script_sha256':m.sha(path.read_bytes()),'control_script_sha256':m.sha(Path(__file__).read_bytes()),'assets_admitted':False,'world_authority':False}
with a.output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(result))
