"""Shared bounded-fixture identities; no Android execution or world authority."""
import hashlib
import json

KINDS=('valid','bone','scale','lightmap','weights','matidx','reflection','missing_uv',
       'reflection_count','pivot','bad_index','duplicate_model')
ABIS={'arm64-v8a':('aarch64-linux-android26',183),
      'x86_64':('x86_64-linux-android26',62)}
AUTHORED={'passed':True,'checks':259,'version':8,'parts':2,'vertices':4,'triangles':2,
          'material_pins_balanced':True,'fixture_only':True,'world_authority':False}
ACTUAL={'passed':True,'checks':22,'geo_version':8,'vertices':56,'triangles':28,
        'authentic_geo_bytes':True,'material_fixture_only':True,
        'generation_fixture_only':True,'world_authority':False}
ACTUAL_SHA='218d1b2ff890678cca25b005d295aff8f76c6f551acad6b2144d1786723239b5'

def equal(a,b):return json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False)

def result(value,actual=False):
    if not equal(value,ACTUAL if actual else AUTHORED):
        raise ValueError('Rigid native corpus/count/scope mismatch')
    return value

def digest_header(fixtures):
    """Only exact admitted fixture bytes can replay their SHA256 identity.

    This is NOT a SHA implementation. Production still requires a genuine SHA256
    callback; Android tests qualify CPU resource behavior, not cryptography.
    """
    parts=['#include <stddef.h>\n#include <stdint.h>\n#include <string.h>\n']
    for i,(name,raw) in enumerate(sorted(fixtures.items())):
        parts.append('static const unsigned char rigid_bytes_%d[]={%s};\n'%(i,','.join(str(b) for b in raw)))
        parts.append('static const unsigned char rigid_sha_%d[]={%s};\n'%(i,','.join(str(b) for b in hashlib.sha256(raw).digest())))
    parts.append('static unsigned char*coh_rigid_fixture_digest(const unsigned char*p,size_t n,unsigned char*out){\n')
    for i,(name,raw) in enumerate(sorted(fixtures.items())):
        parts.append('if(n==sizeof(rigid_bytes_%d)&&!memcmp(p,rigid_bytes_%d,n)){memcpy(out,rigid_sha_%d,32);return out;}\n'%(i,i,i))
    parts.append('memset(out,0,32);return NULL;}\n')
    return ''.join(parts).encode()
