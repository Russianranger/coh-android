#include "tests/tex_defaults_fixture.h"
#include <stdlib.h>
#include <string.h>
#define REQUIRE(x) do{if(!(x))abort();}while(0)
#define assert(x) ((void)0) /* original release debug/sentinel checks disabled */
#define devassert(x) (required_present=!!(x)) /* observe original assertion */
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
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
typedef struct {const char*name;TexFlags flags;uint32_t row;} BasicTexture;
static BasicTexture entries[DEFAULTS_ORACLE_ROWS];
static uint32_t count,required_present,lookups;static void*g_basicTextures_ht;
static BasicTexture *white_tex,*grey_tex,*invisible_tex,*black_tex;
static BasicTexture *dummy_bump_tex,*dummy_dynamic_cubemap_tex,*building_lights_tex;
static unsigned fold(unsigned x){return x>='A'&&x<='Z'?x+32:x;}
static int same(const char*a,const char*b){while(*a&&*b){if(fold((unsigned char)*a++)!=fold((unsigned char)*b++))return 0;}return!*a&&!*b;}
static void strncpyt(char*d,const char*s,int n){REQUIRE(n>0&&strlen(s)<(unsigned)n);memcpy(d,s,strlen(s)+1);}
static int stashFindPointer(void*t,const char*key,BasicTexture**out){
 (void)t;lookups++;for(uint32_t i=0;i<count;i++)if(same(key,entries[i].name)){*out=entries+i;return 1;}return 0;
}
static int texFixName(const char *s,char *res, int size)
{
char *const res_start = res;
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
    else if(res - res_start >= 8 && res[-8] == '.')
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
BasicTexture *texFind(const char *name)
{
    char search[128];
    BasicTexture *match = 0;

    assert(name!=(char*)0xfafafafa);

    if (!name)
        return NULL;

    assert(*(int*)name!=0xfafafafa);

    if (name[0]=='!')
        name++;

    texFixName(name, search, ARRAY_SIZE(search));
    if (!stashFindPointer(g_basicTextures_ht, search, &match)) {
        //printf("Warning: Missing texture: '%s'\n", name);
        return NULL;
    }
    return match;
}
static void texFindNeededBinds()
{
    // Find basic textures
    white_tex            = texFind("white");
    grey_tex            = texFind("grey");
    invisible_tex        = texFind("invisible");
    if(invisible_tex)
        invisible_tex->flags &= ~TEX_ALPHA;
    black_tex            = texFind("black");
    dummy_bump_tex        = texFind("dummy_bump");
    dummy_dynamic_cubemap_tex = texFind("dummy_dynamic_cubemap_face0");
    building_lights_tex = texFind("buildingLightPattern");

    // Game crashes if these basic textures are missing (there may be more)
    devassert(white_tex && grey_tex && dummy_dynamic_cubemap_tex);
}

void original_defaults(const char*const*names,const uint32_t*flags,uint32_t n,DefaultsOracle*out){
 REQUIRE(n<=DEFAULTS_ORACLE_ROWS);count=n;lookups=required_present=0;
 memset(entries,0,sizeof(entries));memset(out,0,sizeof(*out));
 for(uint32_t i=0;i<n;i++){REQUIRE(names[i]&&strlen(names[i])<128);entries[i]=(BasicTexture){names[i],(TexFlags)flags[i],i};}
 white_tex=grey_tex=invisible_tex=black_tex=dummy_bump_tex=dummy_dynamic_cubemap_tex=building_lights_tex=NULL;
 texFindNeededBinds();
 BasicTexture*selected[]={white_tex,grey_tex,invisible_tex,black_tex,dummy_bump_tex,dummy_dynamic_cubemap_tex,building_lights_tex};
 out->required_present=required_present;out->lookup_count=lookups;
 for(uint32_t i=0;i<7;i++){out->rows[i]=selected[i]?selected[i]->row:UINT32_MAX;if(selected[i])out->selected_mask|=1u<<i;}
 for(uint32_t i=0;i<n;i++)out->flags[i]=(uint32_t)entries[i].flags;
}
