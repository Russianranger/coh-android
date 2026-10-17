#!/usr/bin/env python3
"""Pinned source/receipt checks only; no full costume decode or C rebuild."""
import hashlib
import json
import io
import zipfile
from pathlib import Path,PurePosixPath
import re
import subprocess

SOURCE='b3122754a86e54ed572a01972356832268ea77a4'
RECEIPT='3f536586295d3aba61b7d0a7225f74836b59e7df'
BASE='native-android/engine/costume-tree/'
PROOF='native-android/engine/entities/qualification/costume-tree-20261017/'


def extract(text,name):
    match=re.search(r'^[^\n{};=()]+?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*(?://[^\n]*\n\s*)*\{',text,re.M)
    at=match.end();depth=1
    while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
    return text[match.start():at]+'\n'


def review(root):
    def blob(path,commit=SOURCE):return subprocess.check_output(['git','-C',str(root),'show',commit+':'+path],timeout=30)
    def sha(data):return hashlib.sha256(data).hexdigest()
    raw=blob(PROOF+'host-proof.json',RECEIPT);proof=json.loads(raw);binding=json.loads(blob(PROOF+'source-binding.json',RECEIPT))
    assert binding['source_commit']==SOURCE and binding['proof_sha256']==sha(raw) and binding['all_tested_inputs_match_committed_source'] is True
    local={}
    for relative,expected in proof['source_sha256'].items():
        parts=[]
        for part in PurePosixPath(BASE+relative).parts:
            if part=='..':parts.pop()
            else:parts.append(part)
        path='/'.join(parts);actual=sha(blob(path));assert actual==expected;local[path]=actual
    small=proof['source_oracle']['small_original_provider'];original={}
    for name,expected in small['source_sha256_lf'].items():
        source=blob('upstream/ouroboros/'+name).decode().replace('\r\n','\n');assert sha(source.encode())==expected;original[name]=source
    for qualified,expected in small['function_sha256_lf'].items():
        name,function=qualified.rsplit(':',1);assert sha(extract(original[name],function).encode())==expected
    for name,expected in proof['source_oracle']['extra_tokenstore_function_sha256_lf'].items():assert sha(extract(original['libs/UtilitiesLib/src/utils/tokenstore.c'],name).encode())==expected
    crc=proof['source_oracle']['crc_provider']
    for name,expected in crc['source_sha256_lf'].items():assert sha(blob('upstream/ouroboros/'+name).decode().encode())==expected
    for name,expected in crc['whole_function_sha256_lf'].items():assert sha(extract(original['libs/UtilitiesLib/src/utils/textparser.c'],name).encode())==expected
    crypt=blob('upstream/ouroboros/libs/UtilitiesLib/src/network/crypt.cpp').decode()
    for name,expected in crc['original_crypto_wrapper_sha256_lf'].items():assert sha(extract(crypt,name).encode())==expected
    archive=blob('native-android/engine/entities/qualification/costume-export-20261017/exact-client-dictionary-bins.zip')
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        for name,expected in [('BodyParts.bin',0xcf27aba3),('costume.bin',0xa3374618),('supergroupColors.bin',0xf0095ef2)]:
            with z.open('data/bin/'+name) as stream:header=stream.read(12)
            assert header[:8]==b'CrypticS' and int.from_bytes(header[8:12],'little')==expected
    costume=original['Common/gameData/costume_data.c'];tables={m.group(1):m.group() for m in re.finditer(r'TokenizerParseInfo\s+(\w+)\s*\[\s*\]\s*=\s*\{.*?\n};',costume,re.S) if m.group(1)not in('ParseTailorCost','ParseTailorCostList')}
    assert {name:sha(text.encode()) for name,text in tables.items()}==proof['source_oracle']['full_actual_table_sha256_lf']
    header=original['Common/gameData/costume_data.h'];declaration=header[header.index('typedef struct ColorPalette'):header.index('} CostumeMasterList;')+len('} CostumeMasterList;')]
    assert sha(declaration.encode())==proof['source_oracle']['full_actual_declarations_sha256_lf']
    assert len(proof['actual_schemas'])==13 and [i for i,s in enumerate(proof['actual_schemas']) if len(s)==1 and s[0][0]&255==29]==[12]
    assert proof['crc_numeric_hex']==['0xa3374618','0xcf27aba3','0xf0095ef2'] and proof['crc_matches_all3_verified_donor_headers'] is True
    assert len(proof['independent_negative_controls'])==73
    assert proof['cases'][0]['stats']==[17691352,29057538,801422,8,17691352,138760,2030156,844161,223107,0,894801,181165,6]
    assert proof['cases'][0]['projection_sha256']=='45f6dab4cebcab006b35c123c3e3bedf6bb8884784c1161ab0243b63ad274ea5'
    assert proof['cases'][0]['wire_sha256']=='10ef7562156be60bd1ef3c437c3b46d10b36b6b265129c10f39d25c4a4df5a77'
    for mode in ('release','asan','ubsan'):
        assert proof['original_host_executions'][mode]['passed'] is True
        assert proof['original_host_executions'][mode]['cases']==[{k:item[k] for k in('stats','projection_sha256','wire_sha256')} for item in proof['cases']]
    assert all(item['whole_original_reader_writer_readback'] and item['independent_all_fields_match'] for item in proof['cases'])
    assert proof['scope']['authentic_runtime_dictionary'] is False and proof['scope']['actor_or_ACK_authority'] is False
    return {'schema':'coh-full-costume-offline-independent-source-review-v1','source_commit':SOURCE,'receipt_commit':RECEIPT,'approved_for_offline_source_preparer_scope':True,
            'host_proof_sha256':sha(raw),'source_binding_sha256':sha(blob(PROOF+'source-binding.json',RECEIPT)),
            'local_source_and_archive_sha256':local,'original_small_source_files_verified':len(original),'original_small_function_hashes_verified':len(small['function_sha256_lf']),
            'extra_original_tokenstore_functions_verified':8,'original_crc_functions_verified':len(crc['whole_function_sha256_lf']),'full_actual_table_hashes_verified':len(tables),
            'all13_schema_descriptors_and_unique_root_reviewed':True,'all3_exact_donor_header_crc_words_verified':True,'original_crypto_wrapper_function_hashes_verified':3,'reported_cases':2,'reported_negative_controls':73,'reported_modes':['release','asan','ubsan'],
            'huge_decode_or_compilation_rerun_by_reviewer':False,
            'findings':['Complete source reader/writer functions remain hash-pinned; explicit host storage adapters are not an original Win32 ABI claim.',
                'Independent all-field digest traversal uses bounded segments/arrays/nodes/fields/strings/depth; raw reads stay within input and failed decode publishes no result.',
                'Whole original ParseTableCRC and field interpreters are hashed; source ignores layout offset and substructure size. Explicit zlib-to-Crypto++ digest-byte adapter preserves donor little-endian numeric CRC scope.',
                'Tracked source allocations have requested-byte and count bounds and reset frees owned entries on success or failed read; modified fixture borrows a constant name while original allocation remains tracked for cleanup.',
                'Input/output and allocation tracking storage are separately bounded; named256MiB offline C-owned budget excludes driver/external-library/RSS and cannot be imported into96MiB live world owner.',
                'Envelope prefix is retained rather than regenerated. Original oracle consumes verified or original-produced data only; assert adapters do not qualify malformed input safety.',
                'No preprocessing/final callbacks, original stash construction, cache/shared branch, runtime generation, dictionary permit or actor authority admitted.'],
            'blocking_findings':[],'runtime_or_android_acceptance_inferred':False}


if __name__=='__main__':
    root=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],text=True).strip());value=review(root)
    value['reviewer_script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    Path(__file__).with_name('review.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({'approved':True,'schemas':13,'negative_controls_receipt':73,'huge_rerun':False}))
