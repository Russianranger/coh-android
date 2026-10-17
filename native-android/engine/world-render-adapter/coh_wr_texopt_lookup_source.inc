/* Unchanged original function bodies; lookup signature receives private context. */
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

TexOpt *source_lookup(Lookup *ctx, const char *name, TexOptFlags *texopt_flags)
{
    char    buf[1200],*s,*s2,*slash;
    TexOpt    *tex;

    strcpy(buf,name);
    forwardSlashes(buf);
    slash = strrchr(buf,'/');
    if (!slash++)
        slash = buf;

    // Remove extension
    s = strrchr(buf,'.');
    if (s && s > slash)
        *s = 0;
    // Remove texture locale
    s = strrchr(buf, '#');
    if (s)
        *s = 0;

    // look for direct match
    stashFindPointer( trick_list.texopt_name_hashes,slash, &tex );
    if (tex) {
        if (texopt_flags)
            *texopt_flags = texOptFlagsFromName(name, tex->flags);
        return tex;
    }

    // look for directory match
    strcpy(buf,name);
    forwardSlashes(buf);
    s = strstri(buf,"texture_library");
    if (!s) {
        s = buf;
    } else {
        s += strlen("texture_library");
    }
    if (s[0]=='/') s++;

    for(;;)
    {
        s[strlen(s)-1] = 0;
        s2 = strrchr(s,'/');
        if (!s2)
            break;
        s2[1] = 0;

        stashFindPointer( trick_list.texopt_name_hashes,s, &tex );
        if (tex) {
            if (texopt_flags)
                *texopt_flags = texOptFlagsFromName(name, tex->flags);
            return tex;
        }
    }
    if (texopt_flags)
        *texopt_flags = texOptFlagsFromName(name, 0);
    return 0;
}

