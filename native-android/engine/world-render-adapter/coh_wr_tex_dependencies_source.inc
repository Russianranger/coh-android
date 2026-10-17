/* Exact original private declarations and source projection bodies. */
typedef enum TexFlags
{
    TEX_ALPHA        = 1 << 0,
    TEX_RGB8        = 1 << 1,
    TEX_COMP4        = 1 << 2,
    TEX_COMP8        = 1 << 3,
    
    TEX_TGA            = 1 << 5,
    TEX_DDS            = 1 << 6,


    TEX_CUBEMAPFACE    = 1 << 9,
    TEX_REPLACEABLE    = 1 << 10,
    TEX_BUMPMAP        = 1 << 11,

    TEX_JPEG        = 1 << 13,
} TexFlags;
static int texFixName(const char *s,char *res, int size)
{
int        type = 0;

    if (s != res)
        strncpyt(res,s,size);

    if( strlen(res) < 4 )
        return TEX_TGA; //I guess, maybe error out?

    for(;*s;s++,res++)
    {
        //*res = tolower(*s);
    }
    if (res[-4] == '.')
    {
        if (strcmp(res-3,"tga")==0) {
            // Even though we don't load .tga files anymore, this is still used (through texFind)
            type = TEX_TGA;
        } else if (strcmp(res-3,"jpg")==0)
            type = TEX_JPEG;
        else if (strcmp(res-3,"dds")==0)
            type = TEX_DDS;
        res[-4] = 0;
    }
    //fix for files that were incorrectly named .texture instead of dds.
    else if(res[-8] == '.')
    {
        if (strcmp(res-7,"texture")==0) {
            // Even though we don't load .tga files anymore, this is still used (through texFind)
            type = TEX_DDS;
        }
        res[-8] = 0;
    }
    *res = 0;
    return type;
}

static bool IsValidTexName(const char* texname)
{
    if( !texname || !texname[0] || texname[0]=='%' || !stricmp(texname, "swappable") || !stricmp(texname, "none"))
        return false;
    return true;
}

int texResetTrickBasedParametersBasic(BasicTexture *bind, BasicTexture **binds, int i)
{
    TexOpt    *texopt;
    TexOptFlags texopt_flags = 0;
    TexFlags old_flags = bind->flags;
    TexOptFlags old_texopt_flags = bind->texopt_flags;

    // Clear flags that should only be set in this function
    bind->flags &= ~(TEX_REPLACEABLE);

    texopt = trickFromTextureDirName(bind->dirname,bind->name, &texopt_flags);

    if (texopt)
        bind->gloss = texopt->gloss;
    else
        bind->gloss = 1;

    bind->texopt_flags = texopt_flags;
    bind->texopt_surface = texopt?texopt->surface:0;

    if (texopt_flags & TEXOPT_REPLACEABLE)
        bind->flags |= TEX_REPLACEABLE;

    if( bind->name && strstriConst(bind->name, "cubemap") )
        return 0; // temp hack until get flags for sub faces properly

    // Check to see if any flags changed that need a reload
    #define RELOAD_TEXOPT_FLAGS (TEXOPT_CLAMPS|TEXOPT_CLAMPT|TEXOPT_REPEATS|TEXOPT_REPEATT|TEXOPT_NOMIP|TEXOPT_MIRRORS|TEXOPT_MIRRORT|TEXOPT_BORDER)
    if ((old_texopt_flags&RELOAD_TEXOPT_FLAGS) != (bind->texopt_flags&RELOAD_TEXOPT_FLAGS))
        return 1;
    return 0;

}

static void header_flags(BasicTexture *bind, Header tfh) {
    if(tfh.alpha && !(tfh.flags & TEXOPT_FADE))
        bind->flags |= TEX_ALPHA;
    if(tfh.flags & TEXOPT_BUMPMAP)
        bind->flags |= TEX_BUMPMAP;

    /*hack for bunch of textures with invalid flags*/ // fpe added
    if(tfh.flags & TEXOPT_CUBEMAP && strstriConst(bind->name, "cubemap"))
        bind->flags |= TEX_CUBEMAPFACE;

    assert((tfh.flags & TEXOPT_JPEG) || !(bind->flags & TEX_JPEG)); // If the texture was built with TEXOPT_JPEG, then the flags should include TEX_JPEG
}
static void target_projection(BasicTexture *bind) {
    if (bind->flags & TEX_CUBEMAPFACE || bind->texopt_flags & TEXOPT_CUBEMAP) { // only the first face is marked with this flag upon load
        bind->texopt_flags |= TEXOPT_CLAMPS|TEXOPT_CLAMPT;
        bind->target = GL_TEXTURE_CUBE_MAP_ARB;
    } else
        bind->target = GL_TEXTURE_2D;

    bind->load_state[0] = TEX_NOT_LOADED;
    bind->load_state[1] = TEX_NOT_LOADED;

    bind->hasBeenComposited = 0;
}
