"""ctypes boundary for the small native source world/camera adapter."""
import ctypes as C
class Node(C.Structure):
 _fields_=[('parent',C.c_uint32),('position',C.c_float*3),('pyr_degrees',C.c_float*3)]
class Camera(C.Structure):
 _fields_=[('position',C.c_float*3),('pyr_degrees',C.c_float*3),('fovy',C.c_float),('aspect',C.c_float),('znear',C.c_float),('zfar',C.c_float),('flip_x',C.c_uint32),('flip_y',C.c_uint32)]
class Inputs(C.Structure):
 _fields_=[('nodes',Node*6),('cameras',Camera*6)]
def configure(lib):
 fp=C.POINTER(C.c_float);ip=C.POINTER(Inputs)
 lib.coh_world_parse_inputs.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,ip]
 lib.coh_world_group_matrices.argtypes=[ip,fp,fp]
 lib.coh_world_group_eye_matrices.argtypes=[ip,fp,fp]
 lib.coh_world_camera.argtypes=[ip,C.c_uint32,C.c_float,fp,fp]
 lib.coh_world_vertex.argtypes=[fp,fp,fp,fp,fp,fp]
 lib.coh_world_gl_matrix.argtypes=[fp,fp];lib.coh_world_gl_matrix.restype=None
 for f in ('parse_inputs','group_matrices','group_eye_matrices','camera','vertex'):getattr(lib,'coh_world_'+f).restype=C.c_int
 return lib
