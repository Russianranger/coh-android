/* Exact original source functions; bounded owner adapters supply storage/dictionary/error hooks. */
int strStartsWith(const char* str, const char* start)
{
    if(!str || !start)
        return 0;

    return strnicmp(str, start, strlen(start))==0;
}

int strEndsWith(const char* str, const char* ending)
{
    int strLength;
    int endingLength;
    if(!str || !ending)
        return 0;

    strLength = (int)strlen(str);
    endingLength = (int)strlen(ending);

    if(endingLength > strLength)
        return 0;

    if(stricmp(str + strLength - endingLength, ending) == 0)
        return 1;
    else
        return 0;
}

TexOptFlags texOptFlagsFromName(const char *cName, TexOptFlags origFlags)
{
    TexOptFlags flags=origFlags;
    char namebuf[MAX_PATH];
    char* name;
    strcpy(namebuf, cName);
    name = strrchr(namebuf, '.');
    if (name)
        *name = 0;
    name = namebuf;
    if (strstriConst(name,"PLAYERS/") || strstriConst(name,"ENEMIES/") || strstriConst(name,"NPCS/"))
        flags |= TEXOPT_CLAMPS|TEXOPT_CLAMPT;
    if (strEndsWith(name,"_bump"))
        flags |= TEXOPT_BUMPMAP;

// TODO - Add "_nm" to this list??
    if( strEndsWith(name, "_ns") || strEndsWith(name, "_n") || strEndsWith(name,"_normal") ) {
        flags |= TEXOPT_NODITHER;    // fpe 9/30/09 -- don't dither normal maps.  
        flags |= TEXOPT_NORMALMAP;
        // TODO: Do we want to do this?
        //        Virtually all normal maps are currently authored with
        //        specular in the alpgha channel, even if they aren't
        //        named "_ns.tga", so...
        flags |= TEXOPT_SPECINALPHA;
    }

    // fpe 12/2/09 -- implicity assignment of cubemap flag, since we will have alot of these auto-generated, don't require
    //    that artists create a trick for each one, instead imply by naming convention.  Only the first face (which must end
    //    with 0.tga) gets assigned the cubemap flag.
    // 06/29/10 -- allow all cubemap faces to have the TEXOPT_CUBEMAP flag set.
    //  Need this to update unloadCriteria() to keep it from unloading non-0 faces.
    if( strstriConst(name, "cubemap") ) {
        char lastChar = name[strlen(name)-1];
        if(lastChar >= '0' && lastChar <= '5')
            flags |= TEXOPT_CUBEMAP;
    }

    if (origFlags & TEXOPT_REPEATS) // Explicit repeat to override default clamp
        flags &= ~TEXOPT_CLAMPS;
    if (origFlags & TEXOPT_REPEATT)
        flags &= ~TEXOPT_CLAMPT;
    return flags;
}

static bool texOptNeedsMultiTex(TexOpt *tex)
{
    int i;
    if (// tex->blend_names[BLEND_BASE1] ||
        tex->blend_names[BLEND_MULTIPLY1] ||
        //tex->blend_names[BLEND_DUALCOLOR1] || // DualColor with bumpmap can still use old texture blending mode
        //tex->blend_names[BLEND_BUMPMAP1] || // Single bumpmap still gets old texture blending mode
        tex->blend_names[BLEND_ADDGLOW1] ||
        tex->blend_names[BLEND_MASK] ||
        tex->blend_names[BLEND_BASE2] ||
        tex->blend_names[BLEND_MULTIPLY2] ||
        tex->blend_names[BLEND_DUALCOLOR2] ||
        tex->blend_names[BLEND_BUMPMAP2])
        return true;
    for (i=0; i<BLEND_NUM_BLEND_NAMES; i++) 
        if ((i>1 && (tex->scrollsScales.texopt_scale[i][0]!=1 || // Scale on old-style (0 and 1) are fine
            tex->scrollsScales.texopt_scale[i][1]!=1)) ||
            tex->scrollsScales.texopt_scroll[i][0]!=0 ||
            tex->scrollsScales.texopt_scroll[i][1]!=0)
            return true;
    return false;
}

#define SAFE_STRUCT_FREE_STRING_CONST(_x) do { if ((_x) && !shared_memory) StructFreeStringConst((_x)); if (_x) onlyfulldebugdevassert(shared_memory == isSharedMemory((_x))); (_x) = NULL; } while(0,0)
static void setupTexOpt(TexOpt *tex, bool shared_memory)
{
    int        i;
    TexOpt    *dup_tex;

    assert( tex );
    tex->flags &= ~(TEXOPT_MULTITEX|TEXOPT_FADE|TEXOPT_TREAT_AS_MULTITEX); // Reset flags set only in this function

    tex->scrollsScales.debug_backpointer = tex;

    if(!tex->name)
        return;

    if (tex->texopt_fade[0] || tex->texopt_fade[1])
        tex->flags |= TEXOPT_FADE;

    if (tex->flags & TEXOPT_NORANDOMADDGLOW) {
        tex->scrollsScales.minAddGlow = 255;
        tex->scrollsScales.maxAddGlow = 255;
    }
    if (tex->flags & TEXOPT_ALWAYSADDGLOW) {
        tex->scrollsScales.baseAddGlow = 255;
        tex->scrollsScales.minAddGlow = 255;
        tex->scrollsScales.maxAddGlow = 255;
    }

    if (tex->scrollsScales.hasRgb34) {
        if (!tex->scrollsScales.rgba3[0] && !tex->scrollsScales.rgba3[1] && !tex->scrollsScales.rgba3[2]) {
            tex->scrollsScales.hasRgb34 = false;
        }
    }

    if (tex->scrollsScales.diffuseScaleTrick[1] == 1 && tex->scrollsScales.diffuseScaleTrick[2] == 1)
        tex->scrollsScales.diffuseScaleTrick[1] = tex->scrollsScales.diffuseScaleTrick[2] = tex->scrollsScales.diffuseScaleTrick[0];
    if (tex->scrollsScales.ambientScaleTrick[1] == 1 && tex->scrollsScales.ambientScaleTrick[2] == 1)
        tex->scrollsScales.ambientScaleTrick[1] = tex->scrollsScales.ambientScaleTrick[2] = tex->scrollsScales.ambientScaleTrick[0];
    if (tex->scrollsScales.ambientMin[1] == 0 && tex->scrollsScales.ambientMin[2] == 0)
        tex->scrollsScales.ambientMin[1] = tex->scrollsScales.ambientMin[2] = tex->scrollsScales.ambientMin[0];
    if (tex->fallback.diffuseScaleTrick[1] == 1 && tex->fallback.diffuseScaleTrick[2] == 1)
        tex->fallback.diffuseScaleTrick[1] = tex->fallback.diffuseScaleTrick[2] = tex->fallback.diffuseScaleTrick[0];
    if (tex->fallback.ambientScaleTrick[1] == 1 && tex->fallback.ambientScaleTrick[2] == 1)
        tex->fallback.ambientScaleTrick[1] = tex->fallback.ambientScaleTrick[2] = tex->fallback.ambientScaleTrick[0];
    if (tex->fallback.ambientMin[1] == 0 && tex->fallback.ambientMin[2] == 0)
        tex->fallback.ambientMin[1] = tex->fallback.ambientMin[2] = tex->fallback.ambientMin[0];
    if (tex->flags & TEXOPT_FULLBRIGHT) {
        if (0) {
            // per-material fullbright - doesn't work on indoor lighting
            setVec3(tex->scrollsScales.diffuseScaleTrick, 0, 0, 0);
            setVec3(tex->scrollsScales.ambientMin, 1, 1, 1);
        } else {
            // Make the whole object fullbright - doesn't work on multi-sub
            tex->model_flags |= OBJ_FULLBRIGHT;
        }
    }

    for (i=0; i<BLEND_NUM_BLEND_NAMES; i++) {
        if (tex->blend_names[i]) {
            // note: textures are not yet loaded at this point
            if (strStartsWith(tex->blend_names[i], "texture_name") || !stricmp(tex->blend_names[i], "none"))
                SAFE_STRUCT_FREE_STRING_CONST(tex->blend_names[i]);
            else if (stricmp(tex->blend_names[i], "SWAPPABLE")==0)
                tex->swappable[i] = 1;
        }
    }

    // Verify OldTint -> no DualColor texture
    if (tex->flags & TEXOPT_OLDTINT && tex->blend_names[BLEND_DUALCOLOR1]) {
        ErrorFilenamef(tex->file_name, "Trick %s is flagged as \"OldTint\", but has a DualColor texture (%s).", tex->name, tex->blend_names[BLEND_DUALCOLOR1]);
    }

    // Clean up silliness
    if ((!tex->blend_names[BLEND_MASK] || stricmp(tex->blend_names[BLEND_MASK], "white")==0 || strStartsWith(tex->blend_names[BLEND_MASK], "white."))
        && !(tex->model_flags & OBJ_FANCYWATER))
    {
        // No mask
        SAFE_STRUCT_FREE_STRING_CONST(tex->blend_names[BLEND_MASK]);
        SAFE_STRUCT_FREE_STRING_CONST(tex->blend_names[BLEND_BASE2]);
        SAFE_STRUCT_FREE_STRING_CONST(tex->blend_names[BLEND_MULTIPLY2]);
        SAFE_STRUCT_FREE_STRING_CONST(tex->blend_names[BLEND_BUMPMAP2]);
        SAFE_STRUCT_FREE_STRING_CONST(tex->blend_names[BLEND_DUALCOLOR2]);
    }
    // Clean up scales/scrolls on irrelevant textures
    for (i=0; i<BLEND_NUM_BLEND_NAMES; i++) {
        if (!tex->blend_names[i]) {
            tex->scrollsScales.texopt_scale[i][0] = tex->scrollsScales.texopt_scale[i][1] = 1;
            tex->scrollsScales.texopt_scroll[i][0] = tex->scrollsScales.texopt_scroll[i][1] = 0;
        }
    }


    // Determine texture type
    if (tex->blend_names[BLEND_OLD_TEX_GENERIC_BLEND]) {
        // Old style dual texture
        if (!tex->blend_names[BLEND_BASE1]) {
            SAFE_STRUCT_FREE_STRING_CONST(tex->blend_names[BLEND_BASE1]);
#if SERVER
            tex->blend_names[BLEND_BASE1] = NULL; // Can't set it to anything, otherwise either it won't free or it won't work with shared memory
#else
            // Warning: this isn't friendly with shared memory, but the server doesn't look at texture tricks?
            tex->blend_names[BLEND_BASE1] = shared_memory ? allocAddSharedString(tex->name) : ParserAllocString(tex->name);
#endif
        }
    } else if (texOptNeedsMultiTex(tex)) {
        tex->flags |= TEXOPT_MULTITEX|TEXOPT_TREAT_AS_MULTITEX;
    } else {
        if (tex->blend_names[BLEND_DUALCOLOR1]) {
            // Convert a skeleton of a multi-tex into an old-style texture
            SAFE_STRUCT_FREE_STRING_CONST(tex->blend_names[BLEND_OLD_TEX_GENERIC_BLEND]);
            tex->blend_names[BLEND_OLD_TEX_GENERIC_BLEND] = tex->blend_names[BLEND_DUALCOLOR1];
            tex->blend_names[BLEND_DUALCOLOR1] = NULL;

            tex->blend_mode = BLENDMODE_COLORBLEND_DUAL;
            if (tex->blend_names[BLEND_BUMPMAP1]) {
                tex->blend_mode = BLENDMODE_BUMPMAP_COLORBLEND_DUAL;
            } else {
                // JE: These values should probably be 0.5, 1.0 instead, but things are already tweaked for these values :(
                scaleVec3(tex->scrollsScales.ambientScaleTrick, 0.25, tex->scrollsScales.ambientScaleTrick);
                scaleVec3(tex->scrollsScales.diffuseScaleTrick, 0.5, tex->scrollsScales.diffuseScaleTrick);
            }
            tex->flags |= TEXOPT_TREAT_AS_MULTITEX;
        } else if (tex->blend_names[BLEND_BASE1]) {
            // Explicit base specification, assume this is a new shader and use at least ColorBlendDual stuff
            SAFE_STRUCT_FREE_STRING_CONST(tex->blend_names[BLEND_OLD_TEX_GENERIC_BLEND]);
            tex->blend_names[BLEND_OLD_TEX_GENERIC_BLEND] = shared_memory ? allocAddSharedString("white") : ParserAllocString("white");
            tex->blend_mode = BLENDMODE_COLORBLEND_DUAL;
            if (tex->blend_names[BLEND_BUMPMAP1]) {
                tex->blend_mode = BLENDMODE_BUMPMAP_COLORBLEND_DUAL;
            } else {
                scaleVec3(tex->scrollsScales.ambientScaleTrick, 0.25, tex->scrollsScales.ambientScaleTrick);
                scaleVec3(tex->scrollsScales.diffuseScaleTrick, 0.5, tex->scrollsScales.diffuseScaleTrick);
            }
            tex->flags |= TEXOPT_TREAT_AS_MULTITEX;
        }

        // Doing this causes textures to be reloaded as dualcolorblend textures... I think the original need for these lines was fixed somewhere else
        //if (!tex->blend_names[BLEND_BASE1]) {
        //    // Warning: this isn't friendly with shared memory, but the server doesn't look at texture tricks?
        //    tex->blend_names[BLEND_BASE1] = shared_memory ? allocAddSharedString(tex->name) : ParserAllocString(tex->name);
        //}
    }

#if SERVER || CLIENT
    if (tex->surface_name)
    {
        int surface;
        surface = seqGetStateNumberFromName(tex->surface_name);
        if( surface < 0 )  //default surface should be zero, not -1
            surface = 0;
        if( surface > 255 )
        {
            //coll->surf is a U8, but STATE_BITS can go over 256, so we need to be careful not to have any surface bits over 255 in seq_states. (Just move them around)
            Errorf( "Surface bit %s added that's greater than 256.  Have a programmer fix this oddity in seq_states", tex->surface_name );
            surface = 0;
        }
        tex->surface = surface;
    }
#endif // SERVER || CLIENT

    if (tex->scrollsScales.specularRgba2[0] == 0 &&
        tex->scrollsScales.specularRgba2[1] == 0 &&
        tex->scrollsScales.specularRgba2[2] == 0)
    {
        copyVec3(tex->scrollsScales.specularRgba1, tex->scrollsScales.specularRgba2);
    }

    tex->scrollsScales.specularExponent1 = tex->specularExponent1_parser*2;
    tex->scrollsScales.specularExponent2 = tex->specularExponent2_parser*2;

    if (tex->scrollsScales.specularExponent2 == 0)
        tex->scrollsScales.specularExponent2 = tex->scrollsScales.specularExponent1;

    tex->flags = texOptFlagsFromName(tex->name, tex->flags); // add TEXOPT_BUMPMAP
    
    if (!stashAddPointer(trick_list.texopt_name_hashes,tex->name,tex, false))
    {
        stashFindPointer( trick_list.texopt_name_hashes,tex->name, &dup_tex );
        ErrorFilenameDup(tex->file_name, dup_tex->file_name, tex->name, "Texture Trick");
    }
}

