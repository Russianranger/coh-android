"""Whole unchanged sendEntity control flow with explicit injected child spans.

This is an outer-order fixture provider, NOT complete child/engine execution.
Caller independently qualifies every injected child's grammar and start offset.
"""
import ctypes as C
import hashlib
import importlib.util
import re
import subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
SOURCE='MapServer/src/entity/entsend.c'
SOURCE_SHA='045a5ecb5b64b956229583143fc61316dd8113d8eacf92183ad4756abad0a054'
CHILDREN=['CREATE','MODES','POSITION','QROT','SEQUENCE','TRIGGERS','AI','NETFX',
          'COSTUME','POWER','RAGDOLL','STATS','TARGET','STATUS','INVENTORY',
          'ARCHITECT','PARAMS','PET','AFK','SUPERGROUP','PACT','LOGOUT','TEAMMATE']
def sha(b):return hashlib.sha256(b).hexdigest()
def extract(text,name):
    m=re.search(r'^static void '+re.escape(name)+r'\([^;{}]*\)\s*\{',text,re.M)
    if not m:raise ValueError('whole original '+name+' missing')
    at=m.end();depth=1
    while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
    return text[m.start():at]+'\n'
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def generate(texts):
    """Return fixture C suffix and immutable original function identity.

    Requires an existing original Packet/bit-writer TU from dbclient/check.py.
    Its global storage/packet remain the bounded fixture allocation.
    """
    text=texts[SOURCE].replace('\r\n','\n')
    if sha(text.encode())!=SOURCE_SHA:raise ValueError('original sendEntity source pin differs')
    function=extract(text,'sendEntity')
    return ((HERE/'outer_adapters.h').read_text()+'\n'+function+'\n'+(HERE/'outer_wrapper.h').read_text(),
            {'source_sha256_lf':SOURCE_SHA,'whole_sendEntity_sha256_lf':sha(function.encode()),
             'whole_original_control_function_executed':True,'original_child_serializers_executed':False,
             'child_spans_injected':True,'whole_engine_or_win32_abi':False})
def build(root,work):
    db=module('selected_order_db_bits',root/'native-android/engine/dbclient/check.py')
    base=work/'base';base.mkdir();_,pins=db.oracle(root,base)
    code=(base/'oracle.c').read_text();helper=module('selected_order_source_extract',root/'native-android/tools/protocol_fixture/prepare.py')
    util=(root/'upstream/ouroboros/libs/UtilitiesLib/src/network/net_packetutil.c').read_text()
    code+='\n'+helper.extract(util,'pktSendIfSetBits')+'\n'+helper.extract(util,'pktSendIfSetString')
    addition,proof=generate({SOURCE:(root/'upstream/ouroboros'/SOURCE).read_text()})
    code+='\n'+addition;(work/'original_order.c').write_text(code)
    subprocess.run(['cc','-std=gnu99','-O0','-fwrapv','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),work/'original_order.c','-lz','-o',work/'original_order.so'],check=True)
    lib=C.CDLL(str(work/'original_order.so'))
    lib.record_set_child.argtypes=[C.c_uint,C.c_void_p,C.c_uint,C.c_uint]
    lib.record_outer.argtypes=[C.c_uint,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p]
    proof.update(base_original_bit_writer_pins=pins,generated_c_sha256=sha(code.encode()),child_ids={name:n+1 for n,name in enumerate(CHILDREN)})
    return lib,proof
