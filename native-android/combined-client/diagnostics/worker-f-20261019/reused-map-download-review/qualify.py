#!/usr/bin/env python3
"""Exercise historical downloader with explicit API/download providers, no network."""
import contextlib,copy,hashlib,importlib.util,io,json,os,pathlib,tempfile,unittest.mock as mock,zipfile
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[4]
SUPPLIER=ROOT/'native-android/combined-client/diagnostics/initial-fragment-workflow-20261019/admit_reused_map.py'
VALIDATOR=ROOT/'native-android/combined-client/diagnostics/server-initial-workflow-20261018/admit_workflow_artifact.py'
def sha(v):return hashlib.sha256(v).hexdigest()
def load(name,p):s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def archive(name='compile-only-receipt.json',body=b'{"scope":"synthetic compiler receipt"}\n',symbolic=False):
 output=io.BytesIO()
 with zipfile.ZipFile(output,'w')as z:
  item=zipfile.ZipInfo(name);item.external_attr=((0o120777 if symbolic else 0o100600)<<16);z.writestr(item,body)
 return output.getvalue()
def main():
 supplier=load('f_download_supplier',SUPPLIER);validator=load('f_download_validator',VALIDATOR)
 old='1'*40;current='2'*40;receipt=b'{"scope":"synthetic compiler receipt"}\n';goodzip=archive(body=receipt)
 env={'GITHUB_REPOSITORY':validator.REPO,'GITHUB_REF':'refs/heads/native-android','RUNNER_ENVIRONMENT':'github-hosted','RUNNER_OS':'Linux','RUNNER_ARCH':'X64','GITHUB_SHA':current}
 origin={'artifact_id':11,'run_id':22,'revision':old,'attempt':1,'zip_sha256':sha(goodzip),'receipt_sha256':sha(receipt)}
 artifact={'id':11,'expired':False,'name':'server-initial-compile-'+old+'-attempt-1','size_in_bytes':len(goodzip),'digest':'sha256:'+sha(goodzip),'workflow_run':{'id':22,'head_sha':old,'repository_id':1368730125,'head_repository_id':1368730125}}
 run={'id':22,'run_attempt':1,'head_sha':old,'head_branch':'native-android','path':validator.WORKFLOW,'repository':{'id':1368730125},'head_repository':{'id':1368730125}}
 jobs={'jobs':[{'name':'compile','run_id':22,'head_sha':old,'run_attempt':1,'status':'completed','conclusion':'success'}]}
 results={}
 cases=[('positive',None),('wrong-origin-revision','revision'),('wrong-origin-attempt','attempt'),('wrong-origin-receipt','receipt'),('failed-compile','compile'),('wrong-artifact-digest','digest'),('wrong-download-bytes','bytes'),('traversal-member','traversal'),('symlink-member','symlink'),('extra-origin-field','extra'),('wrong-branch','branch')]
 for label,kind in cases:
  with tempfile.TemporaryDirectory(prefix='coh-f-artifact-test-')as t:
   folder=pathlib.Path(t);o=copy.deepcopy(origin);a=copy.deepcopy(artifact);r=copy.deepcopy(run);j=copy.deepcopy(jobs);wire=goodzip
   if kind=='revision':o['revision']='3'*40
   if kind=='attempt':o['attempt']=2
   if kind=='receipt':o['receipt_sha256']='0'*64
   if kind=='compile':j['jobs'][0]['conclusion']='failure'
   if kind=='digest':a['digest']='sha256:'+'0'*64
   if kind=='bytes':wire=goodzip[:-1]+b'X'
   if kind in ('traversal','symlink'):
    wire=archive('../escape' if kind=='traversal' else 'compile-only-receipt.json',receipt,kind=='symlink');o['zip_sha256']=sha(wire);a['digest']='sha256:'+sha(wire);a['size_in_bytes']=len(wire)
   if kind=='extra':o['private_body']='forbidden'
   if kind=='branch':r['head_branch']='main'
   original=folder/'origin.json';original.write_text(json.dumps(o));target=folder/'extracted';called=[]
   def api(path):
    called.append(path)
    return a if path=='actions/artifacts/11' else r if path=='actions/runs/22' else j if path=='actions/runs/22/attempts/1/jobs?per_page=100' else j
   def download(cmd,stdout,**kw):
    assert cmd==['gh','api','repos/'+validator.REPO+'/actions/artifacts/11/zip'];stdout.write(wire);return type('Result',(),{'returncode':0})()
   error=None
   with mock.patch.object(supplier,'load',return_value=validator),mock.patch.object(validator,'api',side_effect=api),mock.patch.object(supplier.subprocess,'run',side_effect=download),mock.patch.dict(os.environ,env,clear=False),mock.patch('sys.argv',['admit','--origin',str(original),'--output',str(target)]),contextlib.redirect_stdout(io.StringIO()):
    try:supplier.main()
    except Exception as e:error=type(e).__name__+': '+str(e)
   if kind is None:
    assert error is None,error;assert(target/'compile-only-receipt.json').read_bytes()==receipt
    output=json.loads((folder/'extracted-recovery.json').read_bytes());assert output['origin']==origin and output['current_execution_revision']==current and output['current_execution_revision']!=output['origin']['revision']
    assert output['same_execution_run_claimed']is False and output['compiler_reexecuted']is False and output['runtime_executed']is False and output['world_authority']is False
    assert not(folder/'extracted.zip').exists();results[label]={'passed':True,'separate_origin_and_execution_revisions':True}
   else:assert error is not None,label;results[label]={'expected_refusal':error}
 result={'schema':'coh-independent-historical-map-downloader-review-v1','passed':True,'supplier_sha256':sha(SUPPLIER.read_bytes()),'unchanged_validator_sha256':sha(VALIDATOR.read_bytes()),'controls':results,'actual_GitHub_API_or_download':False,'actual_compiler_or_original_server':False,'privacy':'Fixed source/artifact/run IDs, hashes and byte/member counts only; no account, character, payload or private server data.','workflow_dependency':'Current raw/Git source gate must pin downloader, unchanged validator and immutable origin file before import. Successful download is still separate from full historical/current Map recipe admission.','world_authority':False}
 (HERE/'review.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps({'passed':True,'positive':1,'negative':len(cases)-1,'actual_network':False}))
if __name__=='__main__':main()
