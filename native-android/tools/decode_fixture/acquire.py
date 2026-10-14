#!/usr/bin/env python3
"""Acquire only hash-pinned codec sources. No network or fetch occurs in the app."""
import argparse,hashlib,io,json,tarfile,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def sha(data): return hashlib.sha256(data).hexdigest()
def acquire(output):
    pins=json.loads((ROOT/'decode/dependency-pins.json').read_text())
    output.mkdir(parents=True,exist_ok=True)
    for name,pin in pins.items():
        target=output/name
        if all((target/f).is_file() and sha((target/f).read_bytes())==h for f,h in pin['files'].items()):
            continue
        request=urllib.request.Request(pin['archive_url'],headers={'User-Agent':'coh-native-pinned-codec/1'})
        with urllib.request.urlopen(request,timeout=90) as response: archive=response.read(4*1024*1024)
        if len(archive)!=pin['archive_bytes'] or sha(archive)!=pin['archive_sha256']:
            raise ValueError('Pinned '+name+' archive identity differs')
        with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as tar:
            prefix=tar.getnames()[0]+'/'
            for f,h in pin['files'].items():
                data=tar.extractfile(prefix+f).read()
                if sha(data)!=h: raise ValueError('Pinned codec source differs: '+name+'/'+f)
                path=target/f;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    source=output/'vorbis/lib/sharedbook.c'
    original=source.read_text()
    old='ogg_uint32_t word=i<<(32-c->dec_firsttablen);'
    new='ogg_uint32_t word=(ogg_uint32_t)i<<(32-c->dec_firsttablen);'
    if original.count(old)!=1: raise ValueError('Unsigned-shift adaptation anchor differs')
    safe=output/'safe/sharedbook.c';safe.parent.mkdir(parents=True,exist_ok=True)
    safe.write_text(original.replace(old,new))
    overlay={'source':'vorbis/lib/sharedbook.c','line':425,
             'source_sha256':sha(source.read_bytes()),'overlay_sha256':sha(safe.read_bytes()),
             'before':old,'after':new,'reason':'UBSan on valid fixture: left shift into signed int sign bit; cast to declared unsigned destination type defines identical intended bits'}
    config=output/'ogg/include/ogg/config_types.h'
    config.write_text('''/* Generated fixed-width types for Android/host, not an upstream source edit. */
#ifndef __CONFIG_TYPES_H__
#define __CONFIG_TYPES_H__
#include <stdint.h>
typedef int16_t ogg_int16_t; typedef uint16_t ogg_uint16_t;
typedef int32_t ogg_int32_t; typedef uint32_t ogg_uint32_t;
typedef int64_t ogg_int64_t; typedef uint64_t ogg_uint64_t;
#endif
''')
    return {'passed':True,'source_files_verified':sum(len(p['files']) for p in pins.values()),
            'revisions':{n:p['revision'] for n,p in pins.items()},'unsigned_shift_overlay':overlay,'runtime_network':False}
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'decode/.deps')
    args=parser.parse_args();print(json.dumps(acquire(args.output)))
