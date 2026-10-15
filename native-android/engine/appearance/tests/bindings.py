import ctypes as C
u32=C.c_uint32
class Body(C.Structure):_fields_=[('body_type',u32),('ent_type',C.c_char*256),('geometry_prefix',C.c_char*256),('texture_prefix',C.c_char*256)]
class Def(C.Structure):_fields_=[('name',C.c_char_p),('geometry_name',C.c_char_p),('texture_name',C.c_char_p),('base_name',C.c_char_p),('socket',u32*2),('socket_count',u32),('dont_clear',u32)]
class Part(C.Structure):_fields_=[('definition',u32),('geometry',C.c_char_p),('texture',C.c_char_p*2),('color',(C.c_uint8*4)*4)]
Probe=C.CFUNCTYPE(C.c_int,C.c_void_p,u32,C.c_char_p)
CancelFn=C.CFUNCTYPE(C.c_int,C.c_void_p)
class Cancel(C.Structure):_fields_=[('poll',CancelFn),('context',C.c_void_p)]
class Request(C.Structure):_fields_=[('body',Body),('definitions',C.POINTER(Def)),('definition_count',u32),('parts',C.POINTER(Part)),('part_count',u32),('generation',u32),('skin',C.c_uint8*4),('chest_links',C.POINTER(C.c_char_p)),('chest_link_count',u32),('probe',Probe),('probe_context',C.c_void_p),('cancel',Cancel)]
class Draw(C.Structure):_fields_=[('definition',u32),('socket',u32),('generation',u32),('flags',u32),('geometry_key',C.c_char*256),('geometry_path',C.c_char*256),('model_name',C.c_char*256),('texture',(C.c_char*256)*2),('color',(C.c_uint8*4)*4)]
class Diagnostics(C.Structure):_fields_=[('draws',u32),('cleared',u32),('skin_routed',u32),('geometry_probes',u32),('texture_probes',u32),('scratch_bytes',C.c_size_t)]
class Workspace(C.Structure):_fields_=[('draws',Draw*120)]
def configure(lib):
 lib.coh_appearance_body.argtypes=[u32,C.c_char_p,C.c_char_p,C.POINTER(Body)]
 lib.coh_appearance_assemble.argtypes=[C.POINTER(Request),C.POINTER(Workspace),C.POINTER(Draw),C.c_size_t,C.POINTER(C.c_size_t),C.POINTER(Diagnostics)]
def b(s):return s.encode() if s is not None else None
