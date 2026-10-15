"""ctypes ABI for test callers, independent of the renderer implementation."""
import ctypes as C
F=C.c_float;U=C.c_uint32;Z=C.c_size_t;Q=C.c_uint64
V3=F*3;V4=F*4;M4=F*16
class Vertex(C.Structure):_fields_=[('position',V3),('normal',V3),('uv0',F*2),('uv1',F*2),('color',V4)]
class Geometry(C.Structure):_fields_=[('vertices',C.POINTER(Vertex)),('vertex_count',Z),('indices',C.POINTER(U)),('index_count',Z),('identity',Q),('generation',U)]
class Texture(C.Structure):_fields_=[('handle',U),('wrap_s',C.c_int),('wrap_t',C.c_int),('min_filter',C.c_int),('mag_filter',C.c_int)]
class Material(C.Structure):_fields_=[('family',C.c_int),('lighting',C.c_int),('textures',Texture*3),('const0',V4),('const1',V4),('fog_params',V4),('fog_color',V4),('glow_params',V4),('light',V3),('diffuse',V4),('ambient',V4),('specular',V3),('shininess',F),('alpha_ref',F),('blend',C.c_int),('depth_test',C.c_uint8),('depth_write',C.c_uint8),('cull_back',C.c_uint8),('front_cw',C.c_uint8)]
class Draw(C.Structure):_fields_=[('geometry',Geometry),('material',Material),('model_view',M4),('projection',M4),('sequence',Q)]
class Config(C.Structure):_fields_=[('max_draws',Z),('max_vertices_per_draw',Z),('max_indices_per_draw',Z),('shader_capacity',Z)]
class Backend(C.Structure):_fields_=[('compile',C.c_void_p),('destroy_program',C.c_void_p),('bind',C.c_void_p),('draw',C.c_void_p),('context',C.c_void_p)]
class Cancel(C.Structure):_fields_=[('poll',C.c_void_p),('context',C.c_void_p)]
class Stats(C.Structure):_fields_=[('owned_bytes',Z),('borrowed_vertex_bytes',Z),('borrowed_index_bytes',Z),('queued',Z),('high_water_draws',Z),('submitted',Q),('drawn',Q),('rejected',Q),('compiles',Q),('cache_hits',Q),('evictions',Q),('state_binds',Q),('cancelled',Q),('surface_generation',U)]
def load(path,gles=False):
    l=C.CDLL(str(path));l.coh_renderer_default_material.argtypes=[C.c_int];l.coh_renderer_default_material.restype=Material
    l.coh_renderer_fragment.argtypes=[C.POINTER(Material),C.POINTER(F),C.POINTER(F),F,C.POINTER(F),F,C.POINTER(F),C.POINTER(C.c_int)]
    l.coh_renderer_vertex.argtypes=[C.POINTER(Draw),C.POINTER(Vertex),C.POINTER(F),C.POINTER(F),C.POINTER(F),C.POINTER(F)]
    l.coh_renderer_blend.argtypes=[C.c_int,C.POINTER(F),C.POINTER(F),C.POINTER(F)]
    l.coh_renderer_create.argtypes=[C.POINTER(Config),C.POINTER(Backend),C.POINTER(C.c_void_p)];l.coh_renderer_destroy.argtypes=[C.c_void_p]
    l.coh_renderer_begin.argtypes=[C.c_void_p,U];l.coh_renderer_submit.argtypes=[C.c_void_p,C.POINTER(Draw)];l.coh_renderer_flush.argtypes=[C.c_void_p,Cancel];l.coh_renderer_surface_lost.argtypes=[C.c_void_p,U,C.c_int]
    l.coh_renderer_stats.argtypes=[C.c_void_p];l.coh_renderer_stats.restype=Stats
    if gles:
        l.coh_renderer_gles_create.argtypes=[Z,Z,C.POINTER(C.c_void_p),C.POINTER(Backend)];l.coh_renderer_gles_destroy.argtypes=[C.c_void_p,C.c_int];l.coh_renderer_gles_recreate.argtypes=[C.c_void_p,C.c_int];l.coh_renderer_gles_shader_log.argtypes=[C.c_void_p];l.coh_renderer_gles_shader_log.restype=C.c_char_p
    return l
def identity():return M4(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1)
