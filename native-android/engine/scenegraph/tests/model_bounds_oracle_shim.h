#include "coh_model_bounds.h"
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t U8;typedef uint32_t U32;typedef int16_t S16;typedef float F32;typedef float Vec3[3];
#define CLIENT 0
typedef struct {U32 cell;Vec3 pos;F32 size,inv_size;int tag,num_bits;} PolyGrid;
typedef struct {int packsize;U32 unpacksize,data;} PackData;
typedef struct {U32 id,count;} TexID;
typedef struct {PackData tris,verts,norms,sts,weights,matidxs,grid;} PackBlockOnDisk;
typedef struct {U32 flags;F32 radius;U32 vbo;int tex_count;S16 id;U8 blend_mode,loadstate;U32 boneinfo,trick;int vert_count,tri_count;U32 tex_idx;PolyGrid grid;U32 ctris,tags,name,api,extra;Vec3 scale,min,max;U32 gld;PackBlockOnDisk pack;} ModelFormatOnDisk_v2;
typedef char OldRecordSize[(sizeof(ModelFormatOnDisk_v2)==216&&offsetof(ModelFormatOnDisk_v2,min)==104&&offsetof(ModelFormatOnDisk_v2,max)==116)?1:-1];
typedef struct {PackData tris,verts,norms,sts,sts3,weights,matidxs,grid,reductions,reflection_quads;} Pack;
typedef struct TrickInfo TrickInfo;
typedef struct TrickNode {TrickInfo *info;U8 trick_rgba[4],trick_rgba2[4];} TrickNode;
struct TrickInfo {TrickNode tnode;};
typedef struct {char name[256];} GeoLoadData;
typedef struct {U32 flags;F32 radius;int tex_count;S16 id;U8 loadstate;U32 boneinfo;TrickNode *trick;U32 ctris,tags,api,extra;GeoLoadData *gld;int vert_count,tri_count,reflection_quad_count;TexID *tex_idx;PolyGrid grid;char *name;Vec3 scale,min,max;Pack pack;} Model;
#define copyVec3(a,b) memcpy(b,a,sizeof(Vec3))
#define setVec3(v,a,b,c) ((v)[0]=(a),(v)[1]=(b),(v)[2]=(c))
static TrickInfo original_trick;static int original_has_trick;
static TrickInfo *trickFromObjectName(char *name,char *file){(void)name;(void)file;return original_has_trick?&original_trick:NULL;}
