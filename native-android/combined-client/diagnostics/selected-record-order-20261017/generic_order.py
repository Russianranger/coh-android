"""Additive generic INITIAL-create outer fixture. Frozen selected provider is unchanged.

Only fixture wrappers change. Whole sendEntity still uses explicit injected child
spans and source inline grammar, never a claimed original engine object graph.
"""
import ctypes as C,hashlib,importlib.util,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
def build(root,work):
 s=importlib.util.spec_from_file_location('f_generic_original_order',HERE/'order_oracle.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 base=work/'selected';base.mkdir();_,proof=m.build(root,base);source=(base/'original_order.c').read_text();wrapper=(HERE/'outer_wrapper.h').read_text();at=wrapper.index('void record_outer(');template=wrapper[at:]
 template=template.replace('void record_outer(unsigned scenario,','void record_generic_outer(unsigned profile,unsigned scenario,',1)
 template=template.replace('unsigned*boundaries,unsigned*event_out','unsigned*event_out',1)
 template=template.replace('assert(scenario<16','assert(profile<5&&scenario<16',1)
 template=template.replace('Entity e={0};Player pl={0};','Entity e={0},receiver={0};Player pl={0};',1)
 template=template.replace('send_ent.player_ent=&e;', 'e.pl=profile<2?&pl:NULL;e.pchar=profile<3?&character:NULL;e.netfx_count=profile==4;send_ent.player_ent=profile?&receiver:&e;',1)
 # Boundary derivation belongs to the eventual generic composer. Expose only
 # actual source child call cursors; inline grammar remains in the emitted wire.
 template=template[:template.index(' unsigned before[CH_COUNT]')]+'}\n'
 if 'boundaries' in template:raise ValueError('selected boundary assumptions leaked')
 template=template.replace('send_ent.last_idx_sent=16;','send_ent.last_idx_sent=generic_previous;').replace('pktSendBitsPack(&packet,1,0);','pktSendBitsPack(&packet,1,generic_index-generic_previous-1);').replace('sendEntity(17,&e,','sendEntity(generic_index,&e,')
 code=source+'\nstatic unsigned generic_index=17,generic_previous=16;\nvoid record_generic_indices(unsigned index,unsigned previous){assert(index>0&&index<10240&&previous<10240);generic_index=index;generic_previous=previous;}\n'+template;(work/'generic-order.c').write_text(code)
 subprocess.run(['cc','-std=gnu99','-O0','-fwrapv','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),work/'generic-order.c','-lz','-Wl,-z,defs','-o',work/'generic-order.so'],check=True)
 lib=C.CDLL(str(work/'generic-order.so'));lib.record_set_child.argtypes=[C.c_uint,C.c_void_p,C.c_uint,C.c_uint];lib.record_generic_outer.argtypes=[C.c_uint]*4+[C.c_void_p]*5
 proof.update(generic_generated_sha256=hashlib.sha256(code.encode()).hexdigest(),profiles=['self-player-character','other-player-character','other-npc-character','other-npc-no-character','other-npc-netfx-no-character'],scope='Whole unchanged INITIAL sendEntity control; independently injected child spans, fixture-only identity/types, no original object-graph/live/actor/ACK claim',selected_provider_unchanged=True)
 return lib,proof
