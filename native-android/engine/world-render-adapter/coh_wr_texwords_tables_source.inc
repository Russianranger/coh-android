/* Whole unchanged original ParseTexWord tables; token/storage adapters live in the includer. */
TokenizerParseInfo ParseDropShadow[] =
{
    {    "",                TOK_STRUCTPARAM| TOK_U8(TexWordLayerFont, dropShadowXOffset,0) },
    {    "",                TOK_STRUCTPARAM| TOK_U8(TexWordLayerFont, dropShadowYOffset,0) },
    {    "\n",            TOK_END,                                0},
    {    "", 0, 0 }
};

TokenizerParseInfo ParseTexWordLayerFont[] = {
    { "Name",                    TOK_STRING(TexWordLayerFont,fontName,0)            },
    { "Size",                    TOK_INT(TexWordLayerFont,drawSize, 16)        },
    { "Italic",                    TOK_BOOLFLAG(TexWordLayerFont,italicize,0)        },
    { "Bold",                    TOK_BOOLFLAG(TexWordLayerFont,bold,0)                },
    { "Outline",                TOK_U8(TexWordLayerFont,outlineWidth,0)        },
    { "DropShadow",                TOK_NULLSTRUCT(ParseDropShadow)    },
//    { "SoftShadow",                TOK_U8(TexWordLayerFont,softShadowSpread)    },

    { "EndFont",                TOK_END,        0                                            },
    { "", 0, 0 }
};

TokenizerParseInfo ParseTexWordLayerFilterOffset[] =
{
    {    "",                TOK_STRUCTPARAM | TOK_INT(TexWordLayerFilter, offset[0],0) },
    {    "",                TOK_STRUCTPARAM | TOK_INT(TexWordLayerFilter, offset[1],0) },
    {    "\n",            TOK_END,                                0},
    {    "", 0, 0 }
};

TokenizerParseInfo ParseTexWordLayerFilter[] = {
    { "Type",                    TOK_INT(TexWordLayerFilter,type, 0), ParseTexWordFilterType    },
    { "Magnitude",                TOK_INT(TexWordLayerFilter,magnitude, 1)    },
    { "Percent",                TOK_F32(TexWordLayerFilter,percent, 1)    },
    { "Spread",                    TOK_F32(TexWordLayerFilter,spread, 0)    },
    { "Color",                    TOK_INTARRAY(TexWordLayerFilter,rgba)            },
    { "Offset",                    TOK_NULLSTRUCT(ParseTexWordLayerFilterOffset)},

    { "Blend",                    TOK_INT(TexWordLayerFilter,blend, 0), ParseTexWordBlendType    },

    { "EndFilter",                TOK_END,        0                                            },
    { "", 0, 0 }
};



TokenizerParseInfo ParseTexWordLayer[] = {
    { "Name",                    TOK_STRING(TexWordLayer,layerName,0)    },
    { "Type",                    TOK_INT(TexWordLayer,type, 0), ParseTexWordLayerType    },
    { "Stretch",                TOK_INT(TexWordLayer,stretch, 0), ParseTexWordLayerStretch},
    { "Text",                    TOK_STRING(TexWordLayer,text,0)            },
    { "Image",                    TOK_STRING(TexWordLayer,imageName,0)    },
    { "Color",                    TOK_INTARRAY(TexWordLayer,rgba)            },
    { "Color0",                    TOK_INTARRAY(TexWordLayer,rgbas[0])        },
    { "Color1",                    TOK_INTARRAY(TexWordLayer,rgbas[1])        },
    { "Color2",                    TOK_INTARRAY(TexWordLayer,rgbas[2])        },
    { "Color3",                    TOK_INTARRAY(TexWordLayer,rgbas[3])        },
    { "Pos",                    TOK_VEC2(TexWordLayer,pos)            },
    { "Size",                    TOK_VEC2(TexWordLayer,size)            },
    { "Rot",                    TOK_F32(TexWordLayer,rot,0)            },
    { "Hidden",                    TOK_BOOLFLAG(TexWordLayer,hidden,0),        },
    { "Font",                    TOK_EMBEDDEDSTRUCT(TexWordLayer,font,ParseTexWordLayerFont)},

    { "Filter",                    TOK_STRUCT(TexWordLayer,filter, ParseTexWordLayerFilter) },

    { "SubLayer",                TOK_STRUCT(TexWordLayer,sublayer, ParseTexWordLayer) },
    { "SubBlend",                TOK_INT(TexWordLayer,subBlend, 0), ParseTexWordBlendType    },
    { "SubBlendWeight",            TOK_F32(TexWordLayer,subBlendWeight, 1), 0},

    { "EndLayer",                TOK_END,        0                                    },
    { "EndSubLayer",            TOK_END,        0                                    },
    { "", 0, 0 }
};

TokenizerParseInfo ParseTexWordLayerSize[] =
{
    {    "",                TOK_STRUCTPARAM | TOK_INT(TexWord, width,0) },
    {    "",                TOK_STRUCTPARAM | TOK_INT(TexWord, height,0) },
    {    "\n",            TOK_END,                                0},
    {    "", 0, 0 }
};

TokenizerParseInfo ParseTexWord[] = {
    { "TexWord",                    TOK_IGNORE,    0}, // hack, so we can read in individual entries
    { "Name",                        TOK_CURRENTFILE(TexWord,name)                },
    { "Size",                        TOK_NULLSTRUCT(ParseTexWordLayerSize) },
    { "Layer",                        TOK_STRUCT(TexWord,layers, ParseTexWordLayer) },

    { "EndTexWord",                    TOK_END,        0                                        },
    { "", 0, 0 }
};

TokenizerParseInfo ParseTexWordFiles[] = {
    { "TexWord",                    TOK_STRUCT(TexWordList,texWords, ParseTexWord) },
    { "", 0, 0 }
};
