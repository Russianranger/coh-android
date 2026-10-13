"""Ctypes layout of the separately scoped raw animation runtime; no fixture math."""
import ctypes as C
BONES=99
class Track(C.Structure):
 _fields_=[('rotation',C.POINTER(C.c_uint8)),('position',C.POINTER(C.c_uint8)),('rotation_keys',C.c_uint16),('position_keys',C.c_uint16),('rotation_frames',C.c_uint16),('position_frames',C.c_uint16),('id',C.c_uint8),('flags',C.c_uint8),('present',C.c_uint8)]
class File(C.Structure):
 _fields_=[('bytes',C.POINTER(C.c_uint8)),('byte_count',C.c_size_t),('track_count',C.c_uint32),('tracks',Track*BONES)]
class Rig(C.Structure):
 _fields_=[('bytes',C.POINTER(C.c_uint8)),('byte_count',C.c_size_t),('base',File),('motion',File),('parent',C.c_int16*BONES),('order',C.c_uint8*BONES),('node_count',C.c_uint32),('base_position',(C.c_float*3)*BONES),('base_rotation',(C.c_float*4)*BONES),('bind_translation',(C.c_float*3)*BONES),('animation_delta',(C.c_float*3)*BONES),('palette_ids',C.c_uint32*15),('palette_count',C.c_uint32),('socket_id',C.c_uint32),('first_frame',C.c_float),('last_frame',C.c_float),('ticks_per_second',C.c_float)]
class Pose(C.Structure):
 _fields_=[('frame',C.c_float),('position',(C.c_float*3)*BONES),('rotation',(C.c_float*4)*BONES),('world_rows',(C.c_float*12)*BONES)]
def configure(lib):
 lib.coh_animation_parse.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(Rig)]
 lib.coh_animation_sample.argtypes=[C.POINTER(Rig),C.c_float,C.POINTER(Pose)]
 lib.coh_animation_palette.argtypes=[C.POINTER(Rig),C.POINTER(Pose),C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(C.c_float)]
 lib.coh_animation_default_palette.argtypes=[C.POINTER(Rig),C.POINTER(Pose),C.POINTER(C.c_float)]
 lib.coh_animation_step.argtypes=[C.POINTER(Rig),C.c_float,C.c_float,C.c_float,C.c_int,C.POINTER(C.c_float)]
 for name in ('parse','sample','palette','default_palette','step'):getattr(lib,'coh_animation_'+name).restype=C.c_int
 return lib
