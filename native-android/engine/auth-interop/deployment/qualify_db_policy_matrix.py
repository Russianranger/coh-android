#!/usr/bin/env python3
"""Extend the existing exact original DB login block to dev/normal policy matrix."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import checksum_candidate


def qualify(root,output):
    executions={}
    with tempfile.TemporaryDirectory(prefix='coh-db-policy-matrix-') as temp:
        directory=Path(temp);base=checksum_candidate.prepare(root,directory)
        for name in ('original','candidate'):
            code=(directory/(name+'-policy.c')).read_text()
            provider='static const char *getCompatibleGameVersion(void){return "auth-qualification-1";}'
            if code.count(provider)!=1:raise ValueError('policy_matrix_provider_boundary')
            code=code.replace(provider,'static const char *server_version="auth-qualification-1";\nstatic const char *getCompatibleGameVersion(void){return server_version;}')
            old_sender='static void sendMsg(void *a,const char *b,GameClientLink *c){(void)a;(void)b;(void)c;}'
            if code.count(old_sender)!=1:raise ValueError('policy_matrix_sender_boundary')
            code=code.replace(old_sender,'static char last_message[1000];\nstatic void sendMsg(void *a,const char *b,GameClientLink *c){(void)a;(void)c;snprintf(last_message,sizeof(last_message),"%s",b);}')
            code=code.replace('static void seed(Packet *p){memset(p,0,sizeof(*p));','static void seed(Packet *p){last_message[0]=0;memset(p,0,sizeof(*p));')
            start=code.index('int main(void){Packet p;GameClientLink client={0};')
            code=code[:start]+r'''
int main(void){Packet p;GameClientLink client={0};unsigned prod_rejections=0,provisional_acceptances=0;
 for(int dev=0;dev<2;++dev)for(int fake=0;fake<2;++fake)for(int bypass=0;bypass<2;++bypass){
  server_version=dev?"dev: qualification":"auth-qualification-1";
  seed(&p);server_cfg.fake_auth=fake;p.no_version=bypass;CHECK(login_policy(&p,&client)==1);
  seed(&p);server_cfg.fake_auth=fake;p.no_version=bypass;strcpy(p.version,"wrong-version");
  int may_skip=bypass&&(fake||dev);CHECK(login_policy(&p,&client)==may_skip && (may_skip || strncmp(last_message,"WrongVersion",12)==0));
  seed(&p);server_cfg.fake_auth=fake;p.no_version=bypass;p.protocol--;CHECK(!login_policy(&p,&client) && strcmp(last_message,"WrongProtocol")==0);
  for(unsigned bit=0;bit<128;++bit){seed(&p);server_cfg.fake_auth=fake;p.no_version=bypass;((U8*)p.sum)[bit/8]^=(U8)(1u<<(bit%8));
   int accepts=EXPECT_ORIGINAL||may_skip;CHECK(login_policy(&p,&client)==accepts && (accepts || strncmp(last_message,"WrongVersion",12)==0));if(!dev&&!fake&&!accepts)++prod_rejections;if((dev||fake)&&accepts)++provisional_acceptances;}
  seed(&p);server_cfg.fake_auth=fake;p.no_version=bypass;ignore_checksum=1;int accepts_missing=EXPECT_ORIGINAL||may_skip;CHECK(login_policy(&p,&client)==accepts_missing && (accepts_missing || strncmp(last_message,"WrongVersion",12)==0));
 }
 printf("{\"passed\":true,\"checks\":%u,\"original_defect_expected\":%s,\"production_checksum_bit_refusals\":%u,\"provisional_checksum_bit_acceptances\":%u,\"live_db_login_verified\":false}\n",checks,EXPECT_ORIGINAL?"true":"false",prod_rejections,provisional_acceptances);return 0;}
'''
            generated=directory/(name+'-matrix.c');generated.write_text(code)
            for mode in ('release','asan_ubsan'):
                flags=['-O2'] if mode=='release' else ['-O1','-g','-fsanitize=address,undefined','-fno-pie','-no-pie']
                binary=directory/(name+'-'+mode)
                result=subprocess.run(['cc','-std=c11','-Wno-sizeof-array-argument',*flags,generated,'-o',binary],capture_output=True,timeout=60)
                if result.returncode:raise ValueError('policy_matrix_compile_failed:'+result.stderr.decode()[:1000])
                result=subprocess.run([binary],capture_output=True,timeout=30,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'))
                if result.returncode:raise ValueError('policy_matrix_failed:'+result.stderr.decode()[:1000])
                value=json.loads(result.stdout)
                expected={'passed':True,'checks':1056,'original_defect_expected':name=='original','production_checksum_bit_refusals':0 if name=='original' else 256,'provisional_checksum_bit_acceptances':768 if name=='original' else 384,'live_db_login_verified':False}
                if value!=expected:raise ValueError('policy_matrix_corpus:'+json.dumps(value))
                executions[name+'-'+mode]={'result':value,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'generated_sha256':hashlib.sha256(code.encode()).hexdigest()}
    proof={'schema':'coh-original-db-login-dev-normal-policy-matrix-v1','passed':True,'base_checksum_source_qualification':base,
        'qualifier_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'executions':executions,
        'scope':'Exact existing original first handleLogin block and original/checksum-candidate verifier; synthetic getters and version provider vary only fixture metadata. No complete packet decoder, installed version provider or actual DB login.',
        'nondevelopment_profile_deployed':False,'live_authenticated_db_login_verified':False,'leak_sanitizer_enabled':False}
    output.write_text(json.dumps(proof,indent=2)+'\n');return proof


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    proof=qualify(a.source_root.resolve(),a.output);print(json.dumps({'passed':True,'checks_per_mode_per_verifier':1056,'live_db_login_verified':False}))
