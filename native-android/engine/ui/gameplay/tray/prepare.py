#!/usr/bin/env python3
"""Prepare exact original tray ring/number RGBA resources; no assets enter Git."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import zlib
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

def require(value,message):
    if not value:raise ValueError(message)

def checked(raw,pin):
    require(len(raw)==pin['size'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'Original tray member size/SHA256 differs: '+pin['file_name'])
    require(f'{zlib.crc32(raw):08x}'==pin['crc32'],'Original tray member CRC differs')
    return raw

def decode(raw):
    require(len(raw)>=32,'Texture wrapper truncated')
    head,size,width,height,flags,fade0,fade1,alpha,version=struct.unpack_from('<iiiiIffB3s',raw)
    require(32<head<=1056 and head+size==len(raw) and version in (b'TEX',b'TX2'),'Texture wrapper differs')
    dds=raw[head:]
    require(len(dds)>=128 and dds[:4]==b'DDS ','DDS header missing')
    dw=lambda offset:struct.unpack_from('<I',dds,offset)[0]
    require(dw(4)==124 and dw(76)==32 and dw(80)==65 and dw(84)==0,'Only original ARGB8888 DDS is admitted')
    require(struct.unpack_from('<5I',dds,88)==(32,0xff0000,0xff00,0xff,0xff000000),'ARGB masks differ')
    storage_width,storage_height=dw(16),dw(12)
    require(0<width<=storage_width<=64 and 0<height<=storage_height<=64,'Tray footprint differs')
    require(dw(24) in (0,1) and dw(112)==0 and dw(28) in (0,1),'Tray DDS volume/cubemap/mips unsupported')
    require(len(dds)==128+storage_width*storage_height*4,'Tray DDS payload bounds differ')
    # Original rt_tex.c's no-BGRA path swaps first and third bytes, retaining
    # original straight alpha. This preparation performs it off the frame path.
    pixels=bytearray(b''.join(dds[128+y*storage_width*4:128+y*storage_width*4+width*4] for y in range(height)))
    for offset in range(0,len(pixels),4):pixels[offset],pixels[offset+2]=pixels[offset+2],pixels[offset]
    return bytes(pixels),width,height,dds

def load_ranges():
    spec=importlib.util.spec_from_file_location('tray_ranges',ROOT/'tools/material_fixture/acquire.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def acquire(pins,corpus):
    """Only selected pinned local ZIP records; exact HTTP206 and stable ETag."""
    ranges=load_ranges();reader=None;inner=None;result=[]
    for pin in pins['records']:
        local=corpus/pin['file_name'] if corpus else None
        if local and local.is_file():raw=checked(local.read_bytes(),pin)
        else:
            if reader is None:
                reader=ranges.HTTPRange(pins['outer_asset_url'],pins['outer_expected_bytes'],4<<20)
                with zipfile.ZipFile(reader) as outer:inner=ranges.subzip(reader,outer.getinfo(pins['inner_member']))
                require(inner.size==pins['inner_expected_bytes'],'Inner ZIP size differs')
            inner.seek(pin['offset']);header=inner.read(30)
            require(header[:4]==b'PK\x03\x04','Local ZIP header differs')
            flags,method=struct.unpack_from('<HH',header,6);nl,el=struct.unpack_from('<HH',header,26)
            require(not flags&1 and method==pin['method'] and method in (0,8),'ZIP method/encryption differs')
            require(inner.read(nl).decode('utf8')==pin['name'],'ZIP member identity differs')
            inner.seek(pin['offset']+30+nl+el);packed=inner.read(pin['compressed'])
            require(len(packed)==pin['compressed'],'ZIP member truncated')
            if method==8:
                stream=zlib.decompressobj(-15);raw=stream.decompress(packed,pin['size']+1)
                require(stream.eof and not stream.unused_data and not stream.unconsumed_tail,'ZIP deflate bounds differ')
            else:raw=packed
            checked(raw,pin)
            if local:local.parent.mkdir(parents=True,exist_ok=True);local.write_bytes(raw)
        result.append((pin,raw))
    return result,{'range_bytes':reader.total if reader else 0,'etag':reader.etag if reader else None,
                   'strict_http206':True,'member_sha_crc_verified':True,'full_archive_hash_verified':False}

def build(output,corpus=None):
    pins=json.loads((HERE/'pins.json').read_text());records,network=acquire(pins,corpus)
    prepared=[];header=['#ifndef COH_HUD_TRAY_GENERATED_H','#define COH_HUD_TRAY_GENERATED_H','#include <stdint.h>',
        'typedef struct { uint32_t resource,width,height; const unsigned char *rgba; } CohHudTrayImage;']
    # Admit every input before writing deliverables.
    for pin,raw in records:
        rgba,width,height,_=decode(raw);prepared.append((pin,rgba,width,height))
    output.mkdir(parents=True,exist_ok=True)
    report=[]
    for index,(pin,rgba,width,height) in enumerate(prepared):
        symbol=f'coh_hud_tray_rgba_{index}'
        header.append(f'static const unsigned char {symbol}[{len(rgba)}]={{')
        header.extend(','.join(str(x) for x in rgba[i:i+32])+',' for i in range(0,len(rgba),32));header.append('};')
        (output/(pin['file_name']+'.rgba')).write_bytes(rgba)
        report.append(dict(pin,width=width,height=height,rgba_bytes=len(rgba),rgba_sha256=hashlib.sha256(rgba).hexdigest()))
    header.append('static const CohHudTrayImage coh_hud_tray_images[11]={')
    header.extend(f'{{{pin["resource"]},{width},{height},coh_hud_tray_rgba_{i}}},' for i,(pin,rgba,width,height) in enumerate(prepared))
    header+=['};','static const uint32_t coh_hud_tray_numbers[10]={101,102,103,104,105,106,107,108,109,110};','#endif']
    (output/'support_tray.h').write_text('\n'.join(header)+'\n')
    manifest={'schema':'coh-hud-original-tray-v1','records':report,'network':network,
              'scope':'Original ring and slot-number artwork, no power-specific icon or full UI parity claim',
              'source_commit':pins['source_commit'],'data_commit':pins['data_commit'],
              'generator_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (output/'tray-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--corpus',type=Path)
    a=p.parse_args();m=build(a.output,a.corpus);print(json.dumps({'images':len(m['records']),'rgba_bytes':sum(r['rgba_bytes'] for r in m['records']),'output':str(a.output),'network':m['network']}))
