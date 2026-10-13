"""Native character ABI layouts, without reference implementation math."""
from pathlib import Path
import ctypes as C,importlib.util
_spec=importlib.util.spec_from_file_location('coh_animation_ctypes',Path(__file__).parent.parent/'animation_fixture/_types.py')
_animation=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_animation)
Rig,Pose,animation_configure=_animation.Rig,_animation.Pose,_animation.configure
BONES=99
class Morph(C.Structure):
 _fields_=[('bytes',C.POINTER(C.c_uint8)),('byte_count',C.c_size_t),('body_type',C.c_uint32),
 ('geom_scale',C.c_float*3),('bone_scale',C.c_float),('shoulder_scale',C.c_float),('chest_scale',C.c_float),('waist_scale',C.c_float),('hip_scale',C.c_float),('leg_scale',C.c_float),('arm_scale',C.c_float),('head_scales',C.c_float*3),('leg_scale_ratio',C.c_float),
 ('shoulder_skinny',C.c_float*3),('shoulder_fat',C.c_float*3),('hip',C.c_float*3),('neck',C.c_float*3),('head_min',C.c_float*3),('head_max',C.c_float*3),('face_scales',(C.c_float*3)*7),
 ('fat_model_scale',(C.c_float*3)*BONES),('skinny_model_scale',(C.c_float*3)*BONES),('bone_scales',(C.c_float*3)*BONES),('effective_head_scales',C.c_float*3),('neck_scale',C.c_float),('actor_root_rows',C.c_float*12)]
def configure(lib):
 animation_configure(lib)
 lib.coh_character_parse_morph.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(Morph)]
 lib.coh_character_sample.argtypes=[C.POINTER(Rig),C.POINTER(Morph),C.c_float,C.POINTER(Pose)]
 lib.coh_character_palette.argtypes=[C.POINTER(Rig),C.POINTER(Morph),C.POINTER(Pose),C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(C.c_float)]
 for name in ('parse_morph','sample','palette'):getattr(lib,'coh_character_'+name).restype=C.c_int
 return lib
