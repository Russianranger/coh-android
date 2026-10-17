#!/usr/bin/env python3
"""Read-only exact candidate/donor loader prerequisites; no runtime execution."""
import argparse,hashlib,io,json,re,struct,subprocess,tarfile,zipfile
from pathlib import Path,PurePosixPath
COMPILE_SHA='641c7f1eb7637c2c81ac0dc8861a5597654ea8bcc17c70f917ac1a79c25b38e9'
DONOR_SHA='6d6312b3ef4f7b9d25252ced724cbbdb36a4712a011647a8339b5a3207857911'
BINARY_SHA={'DbServer.exe':'9144727b021526b3777cba53e4935c0ab9c35a76a51d6f00aa50678b7590ea63','CrashRpt.dll':'055c5e42e43fc19f29eea88dbd6854448989ccb2fc2f7e8a928f8cecc04ed5b3'}
VC_SHA={'msvcp140.dll':'f0cda2a0cf1fe6fbbf579b9098462329d3aaa7513a207af2e0f33b01456e388a','vcruntime140.dll':'2fa6efc053203460a23d3a25158f227d895d2dadc63acc1a372da97c3a4281c3'}
def sha(b):return hashlib.sha256(b).hexdigest()
def need(ok,reason):
 if not ok:raise ValueError(reason)
class PE:
 def __init__(self,raw):
  self.raw=raw;need(64<=len(raw)<=8*1024*1024 and raw[:2]==b'MZ','pe_file_budget')
  at=self.u32(60);need(at<=1024*1024 and self.take(at,4)==b'PE\0\0','pe_signature')
  machine,count=struct.unpack('<HH',self.take(at+4,4));optional=self.u16(at+20);start=at+24
  need(machine==0x14c and 1<=count<=96 and optional>=224 and self.u16(start)==0x10b,'pe_win32_profile')
  need(self.u32(start+92)>=16,'pe_directory_count');self.sections=[];self.virtual_sections=[];self.image_size=self.u32(start+56)
  for i in range(count):
   row=start+optional+i*40;virtual,rva,size,offset=struct.unpack('<IIII',self.take(row+8,16))
   need(offset+size<=len(raw) and rva+max(virtual,size)<=0xffffffff,'pe_section_range')
   self.sections.append((rva,size,offset));self.virtual_sections.append((rva,max(virtual,size)))
   need(rva+max(virtual,size)<=self.image_size,'pe_virtual_image_range')
  self.dirs=[struct.unpack('<II',self.take(start+96+i*8,8)) for i in range(16)]
  need(self.dirs[13]==(0,0),'delay_imports_need_separate_admission')
 def take(self,at,size):
  need(type(at)is int and type(size)is int and at>=0 and size>=0 and at+size<=len(self.raw),'pe_file_range');return self.raw[at:at+size]
 def u16(self,at):return struct.unpack('<H',self.take(at,2))[0]
 def u32(self,at):return struct.unpack('<I',self.take(at,4))[0]
 def rva(self,address,size):
  owners=[offset+address-rva for rva,length,offset in self.sections if rva<=address and address+size<=rva+length]
  need(len(owners)==1,'pe_rva_owner');return self.take(owners[0],size)
 def word(self,address):return struct.unpack('<I',self.rva(address,4))[0]
 def text(self,address,limit=512):
  value=bytearray()
  for i in range(limit):
   c=self.rva(address+i,1)[0]
   if not c:return value.decode('ascii')
   need(32<=c<127,'pe_symbol_ascii');value.append(c)
  raise ValueError('pe_string_budget')
 def imports(self):
  address,size=self.dirs[1];result={}
  if not address:need(not size,'pe_import_directory');return result
  need(20<=size<=65536,'pe_import_directory_budget')
  for i in range(min(size//20,513)):
   row=struct.unpack('<IIIII',self.rva(address+i*20,20))
   if not any(row):return result
   need(i<512,'pe_import_descriptor_budget');lookup,stamp,chain,name,iat=row
   dll=self.text(name,128).lower();need(re.fullmatch(r'[a-z0-9_.-]+\.dll',dll) and dll not in result,'pe_import_dll')
   need(lookup or iat,'pe_import_lookup');symbols=[]
   for j in range(4097):
    v=self.word((lookup or iat)+j*4)
    if not v:break
    need(j<4096,'pe_import_symbol_budget')
    if v&0x80000000:
     need(not(v&0x7fff0000) and v&65535,'pe_import_ordinal');symbol={'ordinal':v&65535}
    else:self.rva(v,2);symbol={'name':self.text(v+2)}
    need(symbol not in symbols,'pe_duplicate_import');symbols.append(symbol)
   result[dll]=symbols
  raise ValueError('pe_import_termination')
 def exports(self):
  address,size=self.dirs[0];result={}
  if not address:need(not size,'pe_export_directory');return result
  need(40<=size<=4*1024*1024,'pe_export_directory_budget')
  row=self.rva(address,40);base,count,names,eat,npt,ordinals=struct.unpack('<IIIIII',row[16:])
  need(count<=65536 and names<=count and base+count<=0xffffffff,'pe_export_count')
  for i in range(count):
   target=self.word(eat+4*i)
   if target:
    if not address<=target<address+size:need(sum(rva<=target<rva+length for rva,length in self.virtual_sections)==1,'pe_export_virtual_owner')
    result['#'+str(base+i)]={'ordinal':base+i,'forwarder':self.text(target) if address<=target<address+size else None}
  for i in range(names):
   name=self.text(self.word(npt+4*i));index=struct.unpack('<H',self.rva(ordinals+2*i,2))[0]
   need(index<count and name not in result and '#'+str(base+index) in result,'pe_export_name_ordinal');result[name]=result['#'+str(base+index)]
  return result

def zip_checked(raw,limit):
 need(len(raw)<=limit,'zip_size');z=zipfile.ZipFile(io.BytesIO(raw));need(len(z.infolist())<=65536,'zip_member_budget');seen=set()
 for m in z.infolist():
  p=PurePosixPath(m.filename);need(not p.is_absolute() and '..' not in p.parts and '\\' not in m.filename and m.filename not in seen,'zip_owner')
  need((m.external_attr>>16)&0o170000!=0o120000 and m.file_size<=64*1024*1024,'zip_member_profile');seen.add(m.filename)
 return z

def preflight(compile_archive,donor_archive,wine_exports_raw):
 need(sha(wine_exports_raw)=='8752eb591dbd7395e350a6b8a1ad78468a9f099ec84e707724e431a9e18f5f53','wine_source_export_map_identity')
 wine_exports=json.loads(wine_exports_raw);need(wine_exports['wine_commit']=='b073859675060c9211fcbccfd90e4e87520dc2c2','wine_source_generation')
 c=compile_archive.read_bytes();d=donor_archive.read_bytes();need(sha(c)==COMPILE_SHA and sha(d)==DONOR_SHA,'exact_archive_identity')
 z=zip_checked(c,4*1024*1024);binaries={n:z.read(n) for n in BINARY_SHA}
 for n,raw in binaries.items():need(sha(raw)==BINARY_SHA[n],'candidate_identity')
 donor=zip_checked(d,55*1024*1024);apkraw=donor.read('COH-Atlas-Gameplay-0.13.33.apk');apk=zip_checked(apkraw,55*1024*1024)
 manifest=apk.read('assets/runtime/startup-dbserver-manifest.json');need(sha(manifest)=='949a15e5a796c5c63cf94d3b16072762f9f310545ca28184f5a714d897c9f087','accepted_manual_manifest')
 vc={}
 with tarfile.open(fileobj=io.BytesIO(apk.read('assets/runtime/dbserver-package.tar.gz')),mode='r:gz') as tar:
  members=tar.getmembers();need(len(members)<=128,'runtime_member_budget');seen=set()
  for m in members:
   p=PurePosixPath(m.name);need(not p.is_absolute() and '..' not in p.parts and m.name not in seen and not m.issym() and not m.islnk(),'runtime_owner');seen.add(m.name)
   if m.name in {'normal/'+n for n in VC_SHA}:
    need(m.isfile() and m.size<=1024*1024,'runtime_dll_budget');vc[p.name]=tar.extractfile(m).read()
 need(set(vc)==set(VC_SHA),'runtime_dll_set')
 for n,raw in vc.items():need(sha(raw)==VC_SHA[n],'runtime_dll_identity')
 all_bytes={**binaries,**vc};imports={n:PE(raw).imports() for n,raw in all_bytes.items()};exports={n:PE(raw).exports() for n,raw in vc.items()}
 resolved=[];platform={};forwarded=[];odbc_source=[]
 for symbol in imports['DbServer.exe'].get('odbc32.dll',[]):
  need(set(symbol)=={'ordinal'} and str(symbol['ordinal']) in wine_exports['exports'],'wine_source_odbc_ordinal')
  odbc_source.append({'ordinal':symbol['ordinal'],**wine_exports['exports'][str(symbol['ordinal'])]})
 for consumer,dlls in imports.items():
  for dll,symbols in dlls.items():
   if dll in exports:
    for symbol in symbols:
     key=symbol.get('name') or '#'+str(symbol['ordinal']);need(key in exports[dll],'missing_exact_vc_export')
     row={'consumer':consumer,'dll':dll,'symbol':symbol,'target':exports[dll][key]};resolved.append(row)
     if row['target']['forwarder']:forwarded.append(row)
   else:platform.setdefault(dll,[]).append({'consumer':consumer,'symbols':symbols})
 return {'schema':'coh-exact-manual-runtime-loader-prerequisite-v1','passed':True,'candidate_binaries_sha256':BINARY_SHA,'donor_vc_sha256':VC_SHA,'accepted_apk_sha256':sha(apkraw),'imports':imports,'matched_vc_imports':resolved,'forwarded_vc_exports_needing_platform_admission':forwarded,'unqualified_platform_imports':platform,'source_wine_odbc_ordinal_expectations':odbc_source,'wine_export_map_sha256':sha(wine_exports_raw),'direct_vc_import_exports_present':True,'wine_odbc_pg_loader_qualified':False,'runtime_profile_admitted':False,'service_executed':False,'actual_persistence_verified':False,'nondevelopment_version_observed':False,'authenticated_db_login_verified':False,'shipping_runtime_replacement_permit':False}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--compile-archive',type=Path,required=True);p.add_argument('--donor-archive',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--expected-commit',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 root=a.source_root.resolve();script=Path(__file__).resolve();git=lambda *v:subprocess.check_output(['git','--no-replace-objects','-C',str(root),*v],timeout=30)
 need(git('rev-parse','HEAD').decode().strip()==a.expected_commit,'current_source_commit');raw=script.read_bytes();need(raw==git('show',a.expected_commit+':'+script.relative_to(root).as_posix()),'current_script_git_bytes');need(not a.output.exists(),'new_receipt_required')
 wine_raw=git('show',a.expected_commit+':database/wine-dbserver/odbc32-exports.json');result=preflight(a.compile_archive,a.donor_archive,wine_raw);need(script.read_bytes()==raw and git('rev-parse','HEAD').decode().strip()==a.expected_commit,'source_changed');result.update(source_commit=a.expected_commit,helper_sha256=sha(raw));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'matched_vc_imports':len(result['matched_vc_imports']),'unqualified_platform_dlls':len(result['unqualified_platform_imports']),'runtime_profile_admitted':False}))
