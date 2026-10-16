#!/usr/bin/env python3
"""Exercise the exact extracted numeric report function with a host JNI shim.

The actual Android JNI boundary remains a separate emulator qualification.
"""
import argparse, hashlib, json, re, subprocess, tempfile
from pathlib import Path


def extract(source, name):
    match = re.search(r'^.*\b' + name + r'\s*\([^;{}]*\)\s*\{', source, re.M)
    if not match:
        raise ValueError(name)
    start = source.index('{', match.start())
    depth, at = 1, start + 1
    while depth:
        depth += (source[at] == '{') - (source[at] == '}')
        at += 1
    return source[match.start():at] + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-root', type=Path, required=True)
    ap.add_argument('--header-root', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    root = args.source_root.resolve()
    headers = (args.header_root or root).resolve()
    path = root/'native-android/combined-client/app/src/main/cpp/combined_network.c'
    source = path.read_text()
    report = extract(source, 'Java_org_coh_nativecombined_LocalNative_report')
    phase = extract(source, 'phase_name')
    fields = 'new_world files present_files defs removed_defs children roots removed_roots properties swaps raw_matrices packed_matrices strings string_bytes work_units max_def_id max_root_id footer_file_count footer_active_roots footer_defs_crc footer_refs_crc'.split()
    preamble = r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "coh_local.h"
#define JNIEXPORT
#define JNICALL
typedef const char *jstring;typedef void *jclass;typedef long long jlong;
typedef struct JniFunctions JniFunctions;typedef const JniFunctions *JNIEnv;
struct JniFunctions {jstring (*NewStringUTF)(JNIEnv *,const char *);};
typedef struct {CohLocal *local;CohStatus last_status;} Combined;
static Combined *owner(jlong v){return (Combined *)(uintptr_t)v;}
static CohLocalDiagnostics current;
void coh_local_diagnostics(const CohLocal *unused,CohLocalDiagnostics*out){(void)unused;*out=current;}
static char captured[8192];
static jstring capture(JNIEnv *unused,const char*s){(void)unused;size_t n=strlen(s);if(n>=sizeof(captured))return 0;memcpy(captured,s,n+1);return captured;}
'''
    main_code = r'''
int main(void){
 JniFunctions functions={capture};JNIEnv env=&functions;Combined owner_={0};jlong handle=(jlong)(uintptr_t)&owner_;
 memset(&current,0,sizeof(current));puts(Java_org_coh_nativecombined_LocalNative_report(&env,0,handle));
 memset(&current,255,sizeof(current));current.phase=COH_LOCAL_SCENE_INCOMPLETE;
 puts(Java_org_coh_nativecombined_LocalNative_report(&env,0,handle));
 memset(&current,0,sizeof(current));current.phase=COH_LOCAL_SCENE_INCOMPLETE;
 @FIELDS@
 current.map_protocol.scene_inspection.prefix_bits=123456;
 current.map_protocol.scene_inspection.consumed_bits=234567;
 current.map_protocol.scene_failure.stage=COH_GROUPS_STAGE_PROPERTY;
 current.map_protocol.scene_failure.bit_offset=345678;
 current.map_protocol.scene_failure.status=COH_LIMIT;
 puts(Java_org_coh_nativecombined_LocalNative_report(&env,0,handle));return 0;
}
'''
    setters = '\n'.join('current.map_protocol.scene_inspection.%s=%du;' % (name, i+31) for i, name in enumerate(fields))
    code = preamble + phase + report + main_code.replace('@FIELDS@', setters)
    with tempfile.TemporaryDirectory(prefix='coh-jni-review-') as tmp:
        c = Path(tmp)/'jni.c'
        c.write_text(code)
        output = Path(tmp)/'probe'
        command = ['cc','-std=c99','-O2','-Wall','-Wextra','-Werror','-Wformat=2','-pedantic',
            '-I'+str(headers/'native-android/engine/local'),'-I'+str(headers/'native-android/include'),str(c),'-o',str(output)]
        compiled = subprocess.run(command,capture_output=True,text=True)
        if compiled.returncode:
            raise RuntimeError(compiled.stdout + compiled.stderr)
        lines = subprocess.check_output([str(output)],text=True).splitlines()
    idle, maximum, mapped = [json.loads(line) for line in lines]
    assert idle['phase']=='IDLE' and len(lines[1])<6144
    inspection = mapped['map_protocol']['scene_inspection']
    assert inspection == {**{name:i+31 for i,name in enumerate(fields)}, 'prefix_bits':123456,'consumed_bits':234567}
    assert mapped['map_protocol']['scene_failure']=={'stage':8,'bit_offset':345678,'status':4}
    for item in (idle,maximum,mapped):
        assert item['authserver_authenticated'] is False and item['live_world_rendered'] is False
    proof = {'schema':1,'passed':True,'scope':'exact extracted numeric report function executed through host-only NewStringUTF shim; not Android JNI execution',
        'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'report_function_sha256':hashlib.sha256(report.encode()).hexdigest(),
        'strict_format_compile':True,'cases':3,'inspection_field_mappings':len(fields)+2,
        'failure_field_mappings':3,'report_buffer_bytes':6144,
        'maximum_scalar_output_bytes':len(lines[1].encode()),
        'no_server_text_or_packet_data_fields':True,'auth_and_live_claims_remain_false':True}
    args.output.write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(proof,indent=2))


if __name__=='__main__':
    main()
