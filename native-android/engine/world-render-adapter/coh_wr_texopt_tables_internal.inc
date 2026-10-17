/* Exact original parse declaration text, interpreted through bounded wire descriptors. */
TokenizerParseInfo Vec2Default1[] =
{
    { "", TOK_STRUCTPARAM    |    TOK_F32_X,    0,                1 },
    { "", TOK_STRUCTPARAM    |    TOK_F32_X,    sizeof(F32),    1 },
    { "\n",                        TOK_END },
    { "", 0, 0 }
};
TokenizerParseInfo Vec3Default1[] =
{
    { "", TOK_STRUCTPARAM    |    TOK_F32_X,    0,                1 },
    { "", TOK_STRUCTPARAM    |    TOK_F32_X,    sizeof(F32),    1 },
    { "", TOK_STRUCTPARAM    |    TOK_F32_X,    2*sizeof(F32),    1 },
    { "\n",                        TOK_END },
    { "", 0, 0 }
};
TokenizerParseInfo RGBDefault255[] =
{
    { "", TOK_STRUCTPARAM    |    TOK_U8_X,    0,                255 },
    { "", TOK_STRUCTPARAM    |    TOK_U8_X,    sizeof(U8),        255 },
    { "", TOK_STRUCTPARAM    |    TOK_U8_X,    2*sizeof(U8),    255 },
    { "\n",                        TOK_END },
    { "", 0, 0 }
};
TokenizerParseInfo parse_rgb3[] = {
    { "",                TOK_STRUCTPARAM | TOK_U8(TexOpt,scrollsScales.rgba3[0],0)},
    { "",                TOK_STRUCTPARAM | TOK_U8(TexOpt,scrollsScales.rgba3[1],0)},
    { "",                TOK_STRUCTPARAM | TOK_U8(TexOpt,scrollsScales.rgba3[2],0)},
    { "",                TOK_U8(TexOpt,scrollsScales.hasRgb34,1)},
    { "\n",                TOK_END,            0 },
    { "", 0, 0 }
};
TokenizerParseInfo parse_tex_opt_fallback[] = {
    //{ "ScaleST0",        TOK_VEC2(TexOptFallback,scaleST[1], 1)},
    //{ "ScaleST1",        TOK_VEC2(TexOptFallback,scaleST[0], 1)},
    { "ScaleST0",        TOK_EMBEDDEDSTRUCT(TexOptFallback,scaleST[1],Vec2Default1) },
    { "ScaleST1",        TOK_EMBEDDEDSTRUCT(TexOptFallback,scaleST[0],Vec2Default1) },

    { "Base",            TOK_STRING(TexOptFallback,base_name,0)},
    { "Blend",            TOK_STRING(TexOptFallback,blend_name,0)},
    { "BumpMap",        TOK_STRING(TexOptFallback,bumpmap,0)},
    { "BlendType",        TOK_INT(TexOptFallback,blend_mode,0),texblend_flags},
    { "UseFallback",    TOK_U8(TexOptFallback,useFallback,0)},

    { "AmbientScale",        TOK_REDUNDANTNAME|TOK_F32(TexOptFallback,ambientScaleTrick[0], 0)},
    { "DiffuseScale",        TOK_REDUNDANTNAME|TOK_F32(TexOptFallback,diffuseScaleTrick[0], 0)},
    { "AmbientMin",            TOK_REDUNDANTNAME|TOK_F32(TexOptFallback,ambientMin[0], 0)},
    //{ "DiffuseScaleVec",    TOK_VEC3(TexOptFallback,diffuseScaleTrick, 1)},
    //{ "AmbientScaleVec",    TOK_VEC3(TexOptFallback,ambientScaleTrick, 1)},
    { "DiffuseScaleVec",    TOK_EMBEDDEDSTRUCT(TexOptFallback,diffuseScaleTrick,Vec3Default1)},
    { "AmbientScaleVec",    TOK_EMBEDDEDSTRUCT(TexOptFallback,ambientScaleTrick,Vec3Default1)},
    { "AmbientMinVec",        TOK_VEC3(TexOptFallback,ambientMin)},

    { "End",            TOK_END,            0},
    { "", 0, 0 }
};
TokenizerParseInfo parse_tex_opt[] = {
    { "",                TOK_STRUCTPARAM | TOK_STRING(TexOpt,name,0)},
    { "F",                TOK_CURRENTFILE(TexOpt,file_name)},
    { "TS",                TOK_TIMESTAMP(TexOpt,fileAge)},
    { "InternalName",    TOK_STRING(TexOpt,name,0)},
    { "Gloss",            TOK_F32(TexOpt,gloss,1.f)   },
    { "Surface",        TOK_STRING(TexOpt,surface_name,0) },
    { "Fade",            TOK_VEC2(TexOpt,texopt_fade) },
    { "ScaleST0",        TOK_EMBEDDEDSTRUCT(TexOpt,scrollsScales.texopt_scale[BLEND_OLD_TEX_GENERIC_BLEND],Vec2Default1)}, // JE: These two, apparently, have always been backwards.
    { "ScaleST1",        TOK_EMBEDDEDSTRUCT(TexOpt,scrollsScales.texopt_scale[BLEND_OLD_TEX_BASE],Vec2Default1)},
    { "Blend",            TOK_STRING(TexOpt,blend_names[BLEND_OLD_TEX_GENERIC_BLEND],0)},
    { "BumpMap",        TOK_STRING(TexOpt,blend_names[BLEND_BUMPMAP1],0)},
    { "BlendType",        TOK_INT(TexOpt,blend_mode,0),texblend_flags},
    { "Flags",            TOK_FLAGS(TexOpt,flags,0),tex_flags},
    { "ObjFlags",        TOK_FLAGS(TexOpt,model_flags,0),model_flags},
    { "DF_ObjName",     TOK_STRING(TexOpt,df_name,0) },

    // New Texture blending definitions
    { "Base1",                TOK_STRING(TexOpt,blend_names[BLEND_BASE1],0)},
    { "Base1Scale",            TOK_EMBEDDEDSTRUCT(TexOpt,scrollsScales.texopt_scale[BLEND_BASE1],Vec2Default1)},
    { "Base1Scroll",        TOK_VEC2(TexOpt,scrollsScales.texopt_scroll[BLEND_BASE1])},
    { "Base1ScrollType",    TOK_INT(TexOpt,scrollsScales.texopt_scrollType[BLEND_BASE1],TEXOPTSCROLL_NORMAL), parse_texopt_scroll_type},
    { "Base1Swappable",        TOK_U8(TexOpt,swappable[BLEND_BASE1],0) },

    { "Multiply1",            TOK_STRING(TexOpt,blend_names[BLEND_MULTIPLY1],0)},
    { "Multiply1Scale",        TOK_EMBEDDEDSTRUCT(TexOpt,scrollsScales.texopt_scale[BLEND_MULTIPLY1],Vec2Default1)},
    { "Multiply1Scroll",    TOK_VEC2(TexOpt,scrollsScales.texopt_scroll[BLEND_MULTIPLY1])},
    { "Multiply1ScrollType",TOK_INT(TexOpt,scrollsScales.texopt_scrollType[BLEND_MULTIPLY1], TEXOPTSCROLL_NORMAL), parse_texopt_scroll_type},
    { "Multiply1Swappable",    TOK_U8(TexOpt,swappable[BLEND_MULTIPLY1],0) },

    { "DualColor1",            TOK_STRING(TexOpt,blend_names[BLEND_DUALCOLOR1],0)},
    { "DualColor1Scale",    TOK_EMBEDDEDSTRUCT(TexOpt,scrollsScales.texopt_scale[BLEND_DUALCOLOR1],Vec2Default1)},
    { "DualColor1Scroll",    TOK_VEC2(TexOpt,scrollsScales.texopt_scroll[BLEND_DUALCOLOR1])},
    { "DualColor1ScrollType",TOK_INT(TexOpt,scrollsScales.texopt_scrollType[BLEND_DUALCOLOR1], TEXOPTSCROLL_NORMAL), parse_texopt_scroll_type},
    { "DualColor1Swappable",TOK_U8(TexOpt,swappable[BLEND_DUALCOLOR1],0) },

    { "AddGlow1",            TOK_STRING(TexOpt,blend_names[BLEND_ADDGLOW1],0)},
    { "AddGlow1Scale",        TOK_EMBEDDEDSTRUCT(TexOpt,scrollsScales.texopt_scale[BLEND_ADDGLOW1],Vec2Default1)},
    { "AddGlow1Scroll",        TOK_VEC2(TexOpt,scrollsScales.texopt_scroll[BLEND_ADDGLOW1])},
    { "AddGlow1ScrollType",    TOK_INT(TexOpt,scrollsScales.texopt_scrollType[BLEND_ADDGLOW1], TEXOPTSCROLL_NORMAL), parse_texopt_scroll_type},
    { "AddGlow1Swappable",    TOK_U8(TexOpt,swappable[BLEND_ADDGLOW1],0) },

    { "BumpMap1",            TOK_STRING(TexOpt,blend_names[BLEND_BUMPMAP1],0)},
    { "BumpMap1Scale",        TOK_EMBEDDEDSTRUCT(TexOpt,scrollsScales.texopt_scale[BLEND_BUMPMAP1],Vec2Default1)},
    { "BumpMap1Scroll",        TOK_VEC2(TexOpt,scrollsScales.texopt_scroll[BLEND_BUMPMAP1])},
    { "BumpMap1ScrollType",    TOK_INT(TexOpt,scrollsScales.texopt_scrollType[BLEND_BUMPMAP1], TEXOPTSCROLL_NORMAL), parse_texopt_scroll_type},
    { "BumpMap1Swappable",    TOK_U8(TexOpt,swappable[BLEND_BUMPMAP1],0) },

    { "Mask",                TOK_STRING(TexOpt,blend_names[BLEND_MASK],0)},
    { "MaskScale",            TOK_EMBEDDEDSTRUCT(TexOpt,scrollsScales.texopt_scale[BLEND_MASK],Vec2Default1)},
    { "MaskScroll",            TOK_VEC2(TexOpt,scrollsScales.texopt_scroll[BLEND_MASK])},
    { "MaskScrollType",        TOK_INT(TexOpt,scrollsScales.texopt_scrollType[BLEND_MASK], TEXOPTSCROLL_NORMAL), parse_texopt_scroll_type},
    { "MaskSwappable",        TOK_U8(TexOpt,swappable[BLEND_MASK],0) },

    { "Base2",                TOK_STRING(TexOpt,blend_names[BLEND_BASE2],0)},
    { "Base2Scale",            TOK_EMBEDDEDSTRUCT(TexOpt,scrollsScales.texopt_scale[BLEND_BASE2],Vec2Default1)},
    { "Base2Scroll",        TOK_VEC2(TexOpt,scrollsScales.texopt_scroll[BLEND_BASE2])},
    { "Base2ScrollType",    TOK_INT(TexOpt,scrollsScales.texopt_scrollType[BLEND_BASE2], TEXOPTSCROLL_NORMAL), parse_texopt_scroll_type},
    { "Base2Swappable",        TOK_U8(TexOpt,swappable[BLEND_BASE2],0) },

    { "Multiply2",            TOK_STRING(TexOpt,blend_names[BLEND_MULTIPLY2],0)},
    { "Multiply2Scale",        TOK_EMBEDDEDSTRUCT(TexOpt,scrollsScales.texopt_scale[BLEND_MULTIPLY2],Vec2Default1)},
    { "Multiply2Scroll",    TOK_VEC2(TexOpt,scrollsScales.texopt_scroll[BLEND_MULTIPLY2])},
    { "Multiply2ScrollType",TOK_INT(TexOpt,scrollsScales.texopt_scrollType[BLEND_MULTIPLY2], TEXOPTSCROLL_NORMAL), parse_texopt_scroll_type},
    { "Multiply2Swappable",    TOK_U8(TexOpt,swappable[BLEND_MULTIPLY2],0) },

    { "DualColor2",            TOK_STRING(TexOpt,blend_names[BLEND_DUALCOLOR2],0)},
    { "DualColor2Scale",    TOK_EMBEDDEDSTRUCT(TexOpt,scrollsScales.texopt_scale[BLEND_DUALCOLOR2],Vec2Default1)},
    { "DualColor2Scroll",    TOK_VEC2(TexOpt,scrollsScales.texopt_scroll[BLEND_DUALCOLOR2])},
    { "DualColor2ScrollType",TOK_INT(TexOpt,scrollsScales.texopt_scrollType[BLEND_DUALCOLOR2], TEXOPTSCROLL_NORMAL), parse_texopt_scroll_type},
    { "DualColor2Swappable",TOK_U8(TexOpt,swappable[BLEND_DUALCOLOR2],0) },

    { "BumpMap2",            TOK_STRING(TexOpt,blend_names[BLEND_BUMPMAP2],0)},
    { "BumpMap2Scale",        TOK_EMBEDDEDSTRUCT(TexOpt,scrollsScales.texopt_scale[BLEND_BUMPMAP2],Vec2Default1)},
    { "BumpMap2Scroll",        TOK_VEC2(TexOpt,scrollsScales.texopt_scroll[BLEND_BUMPMAP2])},
    { "BumpMap2ScrollType",    TOK_INT(TexOpt,scrollsScales.texopt_scrollType[BLEND_BUMPMAP2], TEXOPTSCROLL_NORMAL), parse_texopt_scroll_type},
    { "BumpMap2Swappable",    TOK_U8(TexOpt,swappable[BLEND_BUMPMAP2],0) },

    { "CubeMap",            TOK_STRING(TexOpt,blend_names[BLEND_CUBEMAP],0)},
    { "CubeMapScale",        TOK_EMBEDDEDSTRUCT(TexOpt,scrollsScales.texopt_scale[BLEND_CUBEMAP],Vec2Default1)},
    { "CubeMapScroll",        TOK_VEC2(TexOpt,scrollsScales.texopt_scroll[BLEND_CUBEMAP])},
    { "CubeMapScrollType",    TOK_INT(TexOpt,scrollsScales.texopt_scrollType[BLEND_CUBEMAP], TEXOPTSCROLL_NORMAL), parse_texopt_scroll_type},
    { "CubeMapSwappable",    TOK_U8(TexOpt,swappable[BLEND_CUBEMAP],0) },

    { "Color3",                TOK_NULLSTRUCT(parse_rgb3) }, // Using embedded struct to flag
    { "Color4",                TOK_FIXED_ARRAY | TOK_U8_X, offsetof(TexOpt,scrollsScales.rgba4),    3},
    { "SpecularColor",        TOK_EMBEDDEDSTRUCT(TexOpt,scrollsScales.specularRgba1,RGBDefault255) },
    { "SpecularColor1",        TOK_REDUNDANTNAME|TOK_EMBEDDEDSTRUCT(TexOpt,scrollsScales.specularRgba1,RGBDefault255)},
    { "SpecularColor2",        TOK_FIXED_ARRAY | TOK_U8_X, offsetof(TexOpt,scrollsScales.specularRgba2), 3 },
    { "SpecularExponent",    TOK_F32(TexOpt,specularExponent1_parser,8)},
    { "SpecularExponent1",    TOK_REDUNDANTNAME|TOK_F32(TexOpt,specularExponent1_parser,8)},
    { "SpecularExponent2",    TOK_F32(TexOpt,specularExponent2_parser,0)},
    { "Reflectivity",        TOK_F32(TexOpt,scrollsScales.reflectivity,0)}, // deprecated, to be removed
    { "ReflectivityBase",    TOK_F32(TexOpt,scrollsScales.reflectivityBase,-1.0f)},
    { "ReflectivityScale",    TOK_F32(TexOpt,scrollsScales.reflectivityScale,-1.0f)},
    { "ReflectivityPower",    TOK_F32(TexOpt,scrollsScales.reflectivityPower,-1.0f)},

    { "AlphaMask",            TOK_U8(TexOpt,scrollsScales.alphaMask,0)},
    { "MaskWeight",            TOK_F32(TexOpt,scrollsScales.maskWeight, 1)},
    { "Multiply1Reflect",    TOK_U8(TexOpt,scrollsScales.multiply1Reflect,0)},
    { "Multiply2Reflect",    TOK_U8(TexOpt,scrollsScales.multiply2Reflect,0)},
    { "BaseAddGlow",        TOK_U8(TexOpt,scrollsScales.baseAddGlow, 0)},
    { "MinAddGlow",            TOK_U8(TexOpt,scrollsScales.minAddGlow, 0)},
    { "MaxAddGlow",            TOK_U8(TexOpt,scrollsScales.maxAddGlow, 128)},

    { "AddGlowMat2",        TOK_U8(TexOpt,scrollsScales.addGlowMat2, 0)},
    { "AddGlowTint",        TOK_U8(TexOpt,scrollsScales.tintGlow, 0)},
    { "ReflectionTint",        TOK_U8(TexOpt,scrollsScales.tintReflection, 0)},
    { "ReflectionDesaturate",TOK_U8(TexOpt,scrollsScales.desaturateReflection, 0)},
    { "AlphaWater",            TOK_U8(TexOpt,scrollsScales.alphaWater, 0)},

    { "AmbientScale",        TOK_REDUNDANTNAME|TOK_F32(TexOpt,scrollsScales.ambientScaleTrick[0], 0)},
    { "DiffuseScale",        TOK_REDUNDANTNAME|TOK_F32(TexOpt,scrollsScales.diffuseScaleTrick[0], 0)},
    { "AmbientMin",            TOK_REDUNDANTNAME|TOK_F32(TexOpt,scrollsScales.ambientMin[0], 0)},
    { "DiffuseScaleVec",    TOK_EMBEDDEDSTRUCT(TexOpt,scrollsScales.diffuseScaleTrick,Vec3Default1)},
    { "AmbientScaleVec",    TOK_EMBEDDEDSTRUCT(TexOpt,scrollsScales.ambientScaleTrick,Vec3Default1)},
    { "AmbientMinVec",        TOK_VEC3(TexOpt,scrollsScales.ambientMin)},

    { "Fallback",            TOK_EMBEDDEDSTRUCT(TexOpt,fallback,parse_tex_opt_fallback) },

    { "End",                TOK_END,            0},
    { "", 0, 0 }
};
