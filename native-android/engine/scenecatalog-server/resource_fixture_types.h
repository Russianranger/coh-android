/* TRUSTED fixture field shim, NOT original ABI/layout or captured data. The
 * consumer observes named original fields; full declarations are independently
 * hashed in resource_oracle.py. SERVER has no tex_binds or client lod_info. */
typedef struct ResourceFixtureTrickInfo {
 char *name,*file_name;unsigned model_flags,group_flags;
 F32 lod_near,lod_far,lod_nearfade,lod_farfade,lod_scale,shadow_dist;
} TrickInfo;
typedef struct {int flags1,flags2;TrickInfo*info;} TrickNode;
typedef struct ResourceFixtureModel Model;
typedef struct {unsigned short id,count;} TexID;
typedef struct {char **strings;int count;} PackNames;
typedef struct {Model **models;int model_count;} ModelHeader;
typedef struct {
 ModelHeader modelheader;char name[192];PackNames texnames;
 int file_format_version,loadstate,geo_use_type;
} GeoLoadData;
struct ResourceFixtureModel {
 char *name;GeoLoadData*gld;unsigned flags;unsigned char loadstate;
 TrickNode*trick;int vert_count,tri_count,tex_count;TexID*tex_idx;
 F32 min[3],max[3],scale[3],radius;int namelen_notrick;
};
