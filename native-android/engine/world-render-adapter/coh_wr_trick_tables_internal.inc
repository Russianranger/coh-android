/* Exact original Parse6 declarations, interpreted through bounded wire metadata. */
TokenizerParseInfo parse_st_anim[] = {
    { "",                TOK_STRUCTPARAM | TOK_F32(StAnim,speed_scale,0)},
    { "",                TOK_STRUCTPARAM | TOK_F32(StAnim,st_scale,0)},
    { "",                TOK_STRUCTPARAM | TOK_STRING(StAnim,name,0)},
    { "",                TOK_STRUCTPARAM | TOK_FLAGS(StAnim,flags,0),stanim_flags},
    { "\n",                TOK_END,            0 },
    { "", 0, 0 }
};
TokenizerParseInfo parse_auto_lod[] = {
    { "AllowedError",    TOK_F32(AutoLOD,max_error, 0)            },
    { "LodNearFade",    TOK_F32(AutoLOD,lod_nearfade, 0)        },
    { "LodNear",        TOK_F32(AutoLOD,lod_near, 0)            },
    { "LodFar",            TOK_F32(AutoLOD,lod_far, 0)            },
    { "LodFarFade",        TOK_F32(AutoLOD,lod_farfade, 0)        },
    { "LodFlags",        TOK_FLAGS(AutoLOD,flags,0),autolod_flags   },
    { "ModelName",        TOK_STRING(AutoLOD,lod_modelname, 0)        },
    { "End",            TOK_END,            0},
    { "", 0, 0 }
};
TokenizerParseInfo parse_trick[] = {
    { "",                TOK_STRUCTPARAM | TOK_STRING(TrickInfo,name,0)},
    { "",                TOK_CURRENTFILE(TrickInfo,file_name)},
    { "",                TOK_TIMESTAMP(TrickInfo,fileAge)},
    { "LodFar",            TOK_F32(TrickInfo,lod_far,0)   },
    { "LodFarFade",        TOK_F32(TrickInfo,lod_farfade,0)   },
    { "LodNear",        TOK_F32(TrickInfo,lod_near,0)   },
    { "LodNearFade",    TOK_F32(TrickInfo,lod_nearfade,0)   },

    { "TrickFlags",        TOK_FLAGS(TrickInfo,tnode.flags1,0),trick_flags   },
    { "ObjFlags",        TOK_FLAGS(TrickInfo,model_flags,0),model_flags   },
    { "GroupFlags",        TOK_FLAGS(TrickInfo,group_flags,0),group_flags   },

    { "Sway",            TOK_VEC2(TrickInfo,sway)   },
    { "SwayRandomize",    TOK_VEC2(TrickInfo,sway_random)   },
    { "Rotate",            TOK_REDUNDANTNAME | TOK_F32(TrickInfo,sway[0],0)   },
    { "RotateRandomize",TOK_REDUNDANTNAME | TOK_F32(TrickInfo,sway_random[0],0)   },
    { "SwayPitch",        TOK_VEC2(TrickInfo,sway_pitch)   },
    { "SwayRoll",        TOK_VEC2(TrickInfo,sway_roll)   },
    { "AlphaRef",        TOK_F32(TrickInfo,alpha_ref_parser,0)   },
    { "SortBias",        TOK_F32(TrickInfo,alpha_sort_mod,0)   },
    { "WaterReflectionSkew",        TOK_F32(TrickInfo,water_reflection_skew,30)   },
    { "WaterReflectionStrength",    TOK_F32(TrickInfo,water_reflection_strength,60)   },
    { "ScrollST0",        TOK_FIXED_ARRAY | TOK_F32_X, offsetof(TrickInfo,texScrollAmt[0]),    2   },
    { "ScrollST1",        TOK_FIXED_ARRAY | TOK_F32_X, offsetof(TrickInfo,texScrollAmt[1]),    2   },
    { "ShadowDist",        TOK_F32(TrickInfo,shadow_dist,0)   },
    { "NightGlow",        TOK_VEC2(TrickInfo,nightglow_times)   },
    { "TintColor0",        TOK_FIXED_ARRAY | TOK_U8_X, offsetof(TrickInfo,tnode.trick_rgba),    3   },
    { "TintColor1",        TOK_FIXED_ARRAY | TOK_U8_X, offsetof(TrickInfo,tnode.trick_rgba2),  3  },
    { "ObjTexBias",        TOK_F32(TrickInfo,tex_bias,0)    },
    { "CameraFaceTightenUp",TOK_F32(TrickInfo,tighten_up,0)   },

    { "StAnim",            TOK_STRUCT(TrickInfo,stAnim,parse_st_anim) },

    { "AutoLOD",        TOK_STRUCT(TrickInfo,auto_lod,parse_auto_lod) },

    { "End",            TOK_END,            0},
    { "", 0, 0 }
};
