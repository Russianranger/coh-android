#!/usr/bin/env python3
"""Prepare real DDS quality-skip cases, execute pinned reference, and compare exact RGBA bytes."""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,struct,subprocess,sys
class Mip(C.Structure):
    _fields_=[('width',C.c_uint32),('height',C.c_uint32),('mips',C.c_uint32),('format',C.c_uint32),('blocks',C.c_void_p),('block_bytes',C.c_size_t),('rgba_bytes',C.c_size_t)]
def sha(b):return hashlib.sha256(b).hexdigest()
def write(path,obj):path.write_text(json.dumps(obj,indent=2)+'\n')
def prepare(a):
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    lib=C.CDLL(str(a.library.resolve()));lib.coh_dds_mip.argtypes=[C.c_void_p,C.c_size_t,C.c_uint32,C.POINTER(Mip)];lib.coh_dds_rgba.argtypes=[C.c_void_p,C.c_size_t,C.c_uint32,C.c_void_p,C.c_size_t]
    cases=[]
    for file in sorted(a.corpus.rglob('*.dds')):
        data=file.read_bytes();buf=C.create_string_buffer(data);v=Mip()
        if lib.coh_dds_mip(buf,len(data),0,C.byref(v)):
            raise ValueError('unsupported/invalid corpus input '+str(file))
        for level in range(v.mips):
            assert lib.coh_dds_mip(buf,len(data),level,C.byref(v))==0
            if v.rgba_bytes>64*1024*1024:raise ValueError('case allocation cap')
            dest=C.create_string_buffer(v.rgba_bytes)
            assert lib.coh_dds_rgba(buf,len(data),level,dest,v.rgba_bytes)==0
            header=bytearray(data[:128]);struct.pack_into('<I',header,12,v.height);struct.pack_into('<I',header,16,v.width);struct.pack_into('<I',header,28,max(struct.unpack_from('<I',data,28)[0]-level,0))
            # Match raw path after quality skip, retaining original pixel format/caps.
            offset=v.blocks-C.addressof(buf)
            single=bytes(header)+data[offset:]
            ident=sha(data)[:20]+'-mip'+str(level);folder=out/ident;folder.mkdir(exist_ok=True)
            (folder/'input.dds').write_bytes(single);(folder/'native.rgba').write_bytes(dest.raw)
            cases.append({'id':ident,'source_file':file.relative_to(a.corpus).as_posix(),'source_sha256':sha(data),'mip':level,'width':v.width,'height':v.height,'format':v.format,'bytes':v.rgba_bytes,'reconstructed_dds_sha256':sha(single),'native_sha256':sha(dest.raw)})
    if not cases:raise ValueError('empty corpus')
    write(out/'cases.json',{'native_library_sha256':sha(a.library.read_bytes()),'cases':cases})
    print(json.dumps({'cases':len(cases),'formats':sorted(set(c['format'] for c in cases))}))
def reference(a):
    cases=json.loads((a.cases/'cases.json').read_text())['cases'];runs=[]
    for case in cases:
        folder=(a.cases/case['id']).resolve()
        command=[str(a.exe.resolve()),str(folder/'input.dds'),str(folder/'reference.raw'),str(folder/'reference.rgba'),str(folder/'reference.json')]
        for name in ('reference.raw','reference.rgba','reference.json'):(folder/name).unlink(missing_ok=True)
        try:
            r=subprocess.run(command,capture_output=True,text=True,timeout=30)
            runs.append({'id':case['id'],'exit_code':r.returncode,'stdout':r.stdout[-2000:],'stderr':r.stderr[-2000:]})
        except subprocess.TimeoutExpired:
            runs.append({'id':case['id'],'exit_code':-99,'stderr':'reference timeout'})
    write(a.cases/'reference-runs.json',{'executable_sha256':sha(a.exe.read_bytes()),'runs':runs})
def compare(a):
    cases=json.loads((a.cases/'cases.json').read_text())['cases'];results=[]
    runs={r['id']:r for r in json.loads((a.cases/'reference-runs.json').read_text())['runs']}
    for case in cases:
        folder=a.cases/case['id'];r={'id':case['id'],'format':case['format'],'mip':case['mip'],'width':case['width'],'height':case['height']}
        try:
            if runs.get(case['id'],{}).get('exit_code')!=0:raise ValueError('original decoder failed: '+str(runs.get(case['id'])))
            meta=json.loads((folder/'reference.json').read_text());native=(folder/'native.rgba').read_bytes();ref=(folder/'reference.rgba').read_bytes()
            r.update(reference=meta,native_sha256=sha(native),reference_sha256=sha(ref),reference_bytes=len(ref))
            dims=meta.get('width')==case['width'] and meta.get('height')==case['height']
            r['passed']=dims and len(native)==len(ref) and native==ref
            if len(native)==len(ref):
                count=0;delta=0;channels=[0]*4;first=[]
                for i,(x,y) in enumerate(zip(native,ref)):
                    if x!=y:
                        count+=1;delta=max(delta,abs(x-y));channels[i%4]+=1
                        if len(first)<8:first.append((i,x,y))
                r.update(different_bytes=count,max_channel_delta=delta,different_by_channel=channels,first_differences=first)
        except (OSError,ValueError) as e:r.update(passed=False,error=str(e))
        results.append(r)
    report={'passed':bool(results) and all(x['passed'] for x in results),'scope':'Pinned original nvDXT Win32 library vs native host decode of selected real DDS mip cases; no Android GPU/device qualification','total_cases':len(results),'passed_cases':sum(x['passed'] for x in results),'cases':results}
    write(a.output,report);print(json.dumps({k:v for k,v in report.items() if k!='cases'}));return 0 if report['passed'] else 1
def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='mode',required=True)
    x=s.add_parser('prepare');x.add_argument('--corpus',type=Path,required=True);x.add_argument('--library',type=Path,required=True);x.add_argument('--output',type=Path,required=True)
    x=s.add_parser('reference');x.add_argument('--cases',type=Path,required=True);x.add_argument('--exe',type=Path,required=True)
    x=s.add_parser('compare');x.add_argument('--cases',type=Path,required=True);x.add_argument('--output',type=Path,required=True)
    a=p.parse_args();return {'prepare':prepare,'reference':reference,'compare':compare}[a.mode](a)
if __name__=='__main__':sys.exit(main())
