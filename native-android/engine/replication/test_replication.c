#include "coh_replication.h"
#include "fixtures.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static unsigned checks, truncations, fuzz_cases;
#define CHECK(x) do { assert(x);checks++; } while(0)
#define BYTES(a) (CohBytes){a,sizeof(a)}
static CohRepReader body(CohBytes bytes,size_t bits,int mode) {
    CohRepReader r;uint32_t command;
    CHECK(coh_rep_reader(&r,bytes,bits,mode)==COH_OK);
    CHECK(coh_rep_pack(&r,1,&command)==COH_OK);return r;
}
static void connect_truncation(CohBytes bytes,size_t bits,int mode) {
    CohRepReader full=body(bytes,bits,mode);
    for(size_t n=full.cursor;n<bits;n++) {
        CohRepReader r=full;r.bits=n;CohRepReader saved=r;
        CohRepConnect output,old;memset(&output,0xa5,sizeof(output));old=output;
        CHECK(coh_rep_connect(&r,&output)!=COH_OK);
        CHECK(!memcmp(&r,&saved,sizeof(r)));CHECK(!memcmp(&output,&old,sizeof(output)));truncations++;
    }
}
static void parser_truncations(CohBytes bytes,size_t bits,int mode,unsigned kind,const CohRepSchema *schema) {
    CohRepReader full=body(bytes,bits,mode);
    for(size_t n=full.cursor;n<bits;n++) {
        CohRepReader r=full;r.bits=n;CohRepReader old=r;CohStatus st;
        if(kind==0) {
            CohRepSchema v,before;memset(&v,0xa5,sizeof(v));before=v;
            st=coh_rep_shortcuts(&r,&v);CHECK(!memcmp(&v,&before,sizeof(v)));
        } else if(kind==1) {
            CohRepScenePrefix v,before;memset(&v,0xa5,sizeof(v));before=v;
            st=coh_rep_scene_prefix(&r,&v);CHECK(!memcmp(&v,&before,sizeof(v)));
        } else {
            CohRepUpdatePrefix v,before;memset(&v,0xa5,sizeof(v));before=v;
            st=coh_rep_update_prefix(&r,schema,COH_REP_ALLENTS,&v);CHECK(!memcmp(&v,&before,sizeof(v)));
        }
        CHECK(st!=COH_OK);CHECK(!memcmp(&r,&old,sizeof(r)));truncations++;
    }
}
static void run_mode(int mode,CohBytes connect,size_t connect_bits,CohBytes reject,size_t reject_bits,
    CohBytes legacy,size_t legacy_bits,CohBytes shortcuts,size_t shortcut_bits,CohBytes scene,size_t scene_bits,
    CohBytes update,size_t update_bits,CohBytes unknown,size_t unknown_bits,CohBytes physics,size_t physics_bits,
    CohBytes recording,size_t recording_bits,CohBytes full,size_t full_bits,CohBytes partial,size_t partial_bits,
    CohBytes older,size_t older_bits,const unsigned *full_expected,const unsigned *partial_expected,const unsigned *older_expected) {
    CohRepReader r=body(connect,connect_bits,mode);CohRepConnect reply;
    CHECK(coh_rep_connect(&r,&reply)==COH_OK);CHECK(reply.accepted==1&&reply.timezone_delta==-6);
    CHECK(r.cursor==connect_bits);connect_truncation(connect,connect_bits,mode);
    r=body(reject,reject_bits,mode);CHECK(coh_rep_connect(&r,&reply)==COH_OK&&reply.accepted==0);
    CohRepSchema schema={0};r=body(shortcuts,shortcut_bits,mode);
    CHECK(coh_rep_shortcuts(&r,&schema)==COH_OK);CHECK(r.cursor==shortcut_bits);CHECK(schema.count==5);
    CHECK(schema.entries[0].kind==1&&schema.entries[3].kind==10&&schema.entries[4].kind==0);
    parser_truncations(shortcuts,shortcut_bits,mode,0,&schema);
    CohRepScenePrefix sp;r=body(scene,scene_bits,mode);CHECK(coh_rep_scene_prefix(&r,&sp)==COH_OK);
    CHECK(sp.base_map_id==1&&sp.instance_id==7&&sp.intro_zone==4&&sp.page_count==1&&sp.beacons_loaded==1);
    CHECK(!strcmp(sp.map_path,"maps/City_Zones/City_01_01/City_01_01.txt"));
    CHECK(r.cursor==sp.group_tail_bit&&r.cursor<scene_bits);
    parser_truncations(scene,r.cursor,mode,1,&schema);
    CohRepUpdatePrefix up;r=body(update,update_bits,mode);
    CHECK(coh_rep_update_prefix(&r,&schema,COH_REP_ALLENTS,&up)==COH_OK);
    CHECK(up.full_update_id==17&&up.abs_time==123456&&up.db_seconds==87654321&&up.command_count==4);
    CHECK(up.interp_level==2&&up.interp_precision==1&&up.has_debug_info==0);
    CHECK(r.cursor==up.entity_tail_bit&&r.cursor<update_bits);
    parser_truncations(update,r.cursor,mode,2,&schema);
    r=body(unknown,unknown_bits,mode);CohRepReader saved=r;CohRepUpdatePrefix old_up=up;
    CHECK(coh_rep_update_prefix(&r,&schema,COH_REP_ALLENTS,&up)==COH_UNSUPPORTED);
    CHECK(!memcmp(&r,&saved,sizeof(r))&&!memcmp(&up,&old_up,sizeof(up)));
    CohRepPhysics phys;CHECK(coh_rep_reader(&r,physics,physics_bits,mode)==COH_OK);
    CHECK(coh_rep_physics(&r,&phys)==COH_OK&&r.cursor==physics_bits);
    CHECK(phys.net_id==4321&&phys.has_id&&phys.position_changed);
    CHECK(phys.position.x==12.5f&&phys.position.y==-6.25f&&phys.position.z==128);
    CHECK(phys.velocity.x==0&&phys.velocity.y==2.5f&&phys.velocity.z==0);
    CHECK(coh_rep_reader(&r,recording,recording_bits,mode)==COH_OK);saved=r;CohRepPhysics old_phys=phys;
    CHECK(coh_rep_physics(&r,&phys)==COH_UNSUPPORTED);
    CHECK(!memcmp(&r,&saved,sizeof(r))&&!memcmp(&phys,&old_phys,sizeof(phys)));
    CohRepPosition pos;coh_rep_position_init(&pos);
    CHECK(coh_rep_reader(&r,partial,partial_bits,mode)==COH_OK);CHECK(coh_rep_position(&r,1,&pos)==COH_STATE);
    CHECK(coh_rep_reader(&r,full,full_bits,mode)==COH_OK);CHECK(coh_rep_position(&r,10,&pos)==COH_OK);
    CHECK(!memcmp(pos.packed,full_expected,12)&&pos.valid);CHECK(pos.position.x==12.5f&&pos.position.y==-6.25f&&pos.position.z==128);
    CHECK(coh_rep_reader(&r,partial,partial_bits,mode)==COH_OK);CHECK(coh_rep_position(&r,12,&pos)==COH_OK);
    CHECK(!memcmp(pos.packed,partial_expected,12));
    CHECK(coh_rep_reader(&r,older,older_bits,mode)==COH_OK);CHECK(coh_rep_position(&r,11,&pos)==COH_OK);
    CHECK(!memcmp(pos.packed,older_expected,12));
    for(size_t n=0;n<full_bits;n++) {
        CHECK(coh_rep_reader(&r,full,n,mode)==COH_OK);saved=r;CohRepPosition old=pos;
        CHECK(coh_rep_position(&r,13,&pos)==COH_INVALID);
        CHECK(!memcmp(&pos,&old,sizeof(pos))&&!memcmp(&r,&saved,sizeof(r)));truncations++;
    }
    for(size_t n=0;n<physics_bits;n++) {
        CHECK(coh_rep_reader(&r,physics,n,mode)==COH_OK);saved=r;CohRepPhysics old=phys;
        CHECK(coh_rep_physics(&r,&phys)==COH_INVALID);
        CHECK(!memcmp(&phys,&old,sizeof(phys))&&!memcmp(&r,&saved,sizeof(r)));truncations++;
    }
    CohRepSession session;coh_rep_session_init(&session);CHECK(coh_rep_session_begin(&session,101)==COH_OK);
    CHECK(coh_rep_session_message(&session,&schema,connect,connect_bits,mode,0,0)==COH_STATE);
    CHECK(coh_rep_session_message(&session,&schema,scene,scene_bits,mode,0,1)==COH_STATE);
    CHECK(coh_rep_session_message(&session,&schema,connect,connect_bits,mode,0,1)==COH_OK&&session.phase==COH_REP_MAP_CONNECTED);
    CHECK(coh_rep_session_message(&session,&schema,shortcuts,shortcut_bits,mode,0,1)==COH_OK);
    CHECK(coh_rep_session_message(&session,&schema,scene,scene_bits,mode,0,1)==COH_OK&&session.phase==COH_REP_SCENE_PREFIX_SEEN);
    CHECK(coh_rep_session_message(&session,&schema,update,update_bits,mode,0,1)==COH_OK&&session.phase==COH_REP_ENTITY_PREFIX_SEEN);
    CHECK(session.selected_dbid==101);coh_rep_session_disconnect(&session);
    CHECK(session.phase==COH_REP_DISCONNECTED&&!session.selected_dbid&&!session.scene.map_path[0]);
    CHECK(coh_rep_session_begin(&session,102)==COH_OK&&session.generation==2);
    CHECK(coh_rep_session_message(&session,&schema,legacy,legacy_bits,mode,1,1)==COH_OK);
    CHECK(coh_rep_session_message(&session,&schema,scene,scene_bits,mode,0,1)==COH_OK);
    CHECK(coh_rep_session_message(&session,&schema,update,update_bits,mode,0,1)==COH_STATE);
    CHECK(coh_rep_session_message(&session,&schema,reject,reject_bits,mode,0,1)==COH_OK&&session.phase==COH_REP_DISCONNECTED);
}
static void extra_mode(int mode,CohBytes nan,size_t nan_bits,CohBytes duplicate,size_t duplicate_bits,
    CohBytes long_name,size_t long_bits,CohBytes debug,size_t debug_bits,CohBytes same,size_t same_bits,
    CohBytes id_only,size_t id_bits,CohBytes empty,size_t empty_bits) {
    CohRepReader r=body(nan,nan_bits,mode),old=r;CohRepConnect connect={0},before=connect;
    CHECK(coh_rep_connect(&r,&connect)==COH_INVALID);
    CHECK(!memcmp(&r,&old,sizeof(r))&&!memcmp(&connect,&before,sizeof(connect)));
    CohRepSchema schema={0},saved_schema=schema;r=body(duplicate,duplicate_bits,mode);old=r;
    CHECK(coh_rep_shortcuts(&r,&schema)==COH_INVALID);
    CHECK(!memcmp(&r,&old,sizeof(r))&&!memcmp(&schema,&saved_schema,sizeof(schema)));
    r=body(long_name,long_bits,mode);old=r;CHECK(coh_rep_shortcuts(&r,&schema)==COH_LIMIT);
    CHECK(!memcmp(&r,&old,sizeof(r))&&!memcmp(&schema,&saved_schema,sizeof(schema)));
    CohRepUpdatePrefix update;r=body(debug,debug_bits,mode);
    CHECK(coh_rep_update_prefix(&r,&schema,COH_REP_UPDATE,&update)==COH_OK);
    CHECK(update.has_debug_info==1&&update.interp_level==3&&update.interp_precision==2&&r.cursor==debug_bits);
    CohRepScenePrefix scene;r=body(same,same_bits,mode);CHECK(coh_rep_scene_prefix(&r,&scene)==COH_OK);
    CHECK(!scene.new_world&&scene.undo_count==1&&scene.redo_count==2&&!scene.map_path[0]);
    CohRepPhysics phys;CHECK(coh_rep_reader(&r,id_only,id_bits,mode)==COH_OK);CHECK(coh_rep_physics(&r,&phys)==COH_OK);
    CHECK(!phys.position_changed&&phys.has_id&&phys.net_id==65535);
    CHECK(coh_rep_reader(&r,empty,empty_bits,mode)==COH_OK);CHECK(coh_rep_physics(&r,&phys)==COH_OK);
    CHECK(!phys.position_changed&&!phys.has_id);
}
static void source_command_catalog(int mode,CohBytes source,size_t source_bits,
    CohBytes maximum,size_t maximum_bits,CohBytes overflow,size_t overflow_bits) {
    CohRepReader r=body(source,source_bits,mode);CohRepSchema schema={0};
    CHECK(coh_rep_shortcuts(&r,&schema)==COH_OK&&r.cursor==source_bits);
    CHECK(schema.count==1&&schema.entries[0].kind==1);
    CHECK(schema.accessible_commands==SOURCE_ACCESSIBLE_COMMAND_COUNT);
    /* Sample truncated catalog tails and each truncation of the final64 bits.
     * Schema and reader are transactional, including after hundreds of names. */
    CohRepReader start=body(source,source_bits,mode);
    for(size_t bits=start.cursor;bits<source_bits;bits+=257) {
        r=start;r.bits=bits;CohRepReader old=r;CohRepSchema saved=schema;
        CHECK(coh_rep_shortcuts(&r,&schema)!=COH_OK);
        CHECK(!memcmp(&r,&old,sizeof(r))&&!memcmp(&schema,&saved,sizeof(schema)));truncations++;
    }
    for(size_t bits=source_bits-64;bits<source_bits;bits++) {
        r=start;r.bits=bits;CohRepReader old=r;CohRepSchema saved=schema;
        CHECK(coh_rep_shortcuts(&r,&schema)!=COH_OK);
        CHECK(!memcmp(&r,&old,sizeof(r))&&!memcmp(&schema,&saved,sizeof(schema)));truncations++;
    }
    r=body(maximum,maximum_bits,mode);
    CHECK(coh_rep_shortcuts(&r,&schema)==COH_OK&&r.cursor==maximum_bits);
    CHECK(schema.accessible_commands==COH_REP_ACCESSIBLE_COMMAND_MAX&&schema.count==1);
    r=body(overflow,overflow_bits,mode);CohRepReader old=r;CohRepSchema saved=schema;
    CHECK(coh_rep_shortcuts(&r,&schema)==COH_LIMIT);
    CHECK(!memcmp(&r,&old,sizeof(r))&&!memcmp(&schema,&saved,sizeof(schema)));
}
static void fuzz(void) {
    uint32_t seed=0x12345678;unsigned char buffer[257];CohRepSchema schema={0};
    for(unsigned n=0;n<30000;n++) {
        for(unsigned i=0;i<sizeof(buffer);i++){seed=seed*1664525u+1013904223u;buffer[i]=(unsigned char)(seed>>24);}
        size_t bytes=seed%257,bits=bytes?seed%(bytes*8+1):0;CohRepReader r;
        CHECK(coh_rep_reader(&r,(CohBytes){buffer+1,bytes?bytes-1:0},bits>0?bits-1:0,n&1)!=COH_OK || r.cursor==0);
        CHECK(coh_rep_reader(&r,(CohBytes){buffer,bytes},bits,n&1)==COH_OK);
        CohRepReader q=r;CohRepConnect connect;CohRepScenePrefix scene;CohRepUpdatePrefix update;CohRepPhysics physics;CohRepPosition pos;
        coh_rep_position_init(&pos);
        (void)coh_rep_connect(&q,&connect);q=r;(void)coh_rep_shortcuts(&q,&schema);q=r;
        (void)coh_rep_scene_prefix(&q,&scene);q=r;(void)coh_rep_update_prefix(&q,&schema,3,&update);q=r;
        (void)coh_rep_physics(&q,&physics);q=r;(void)coh_rep_position(&q,1,&pos);fuzz_cases++;
    }
}
int main(void) {
#define MODE(n) run_mode(n,BYTES(connect##n),connect##n##_bits,BYTES(reject##n),reject##n##_bits,BYTES(legacy_connect##n),legacy_connect##n##_bits,BYTES(shortcuts##n),shortcuts##n##_bits,BYTES(scene##n),scene##n##_bits,BYTES(update##n),update##n##_bits,BYTES(unknown##n),unknown##n##_bits,BYTES(physics##n),physics##n##_bits,BYTES(physics_recording##n),physics_recording##n##_bits,BYTES(pos_full##n),pos_full##n##_bits,BYTES(pos_partial##n),pos_partial##n##_bits,BYTES(pos_older##n),pos_older##n##_bits,pos_full##n##_expected,pos_partial##n##_expected,pos_older##n##_expected)
    MODE(0);MODE(1);fuzz();
#define EXTRA(n) extra_mode(n,BYTES(connect_nan##n),connect_nan##n##_bits,BYTES(duplicate_shortcuts##n),duplicate_shortcuts##n##_bits,BYTES(long_shortcut##n),long_shortcut##n##_bits,BYTES(update_debug##n),update_debug##n##_bits,BYTES(scene_same##n),scene_same##n##_bits,BYTES(physics_id_only##n),physics_id_only##n##_bits,BYTES(physics_empty##n),physics_empty##n##_bits)
    EXTRA(0);EXTRA(1);
#define CATALOG(n) source_command_catalog(n,BYTES(source_commands##n),source_commands##n##_bits,BYTES(maximum_commands##n),maximum_commands##n##_bits,BYTES(overflow_commands##n),overflow_commands##n##_bits)
    CATALOG(0);CATALOG(1);
    CohRepReader invalid;CHECK(coh_rep_reader(&invalid,(CohBytes){NULL,1},8,0)==COH_INVALID);
    CHECK(coh_rep_reader(&invalid,(CohBytes){NULL,0},1,0)==COH_INVALID);
    CHECK(coh_rep_reader(&invalid,(CohBytes){connect0,COH_REP_MESSAGE_MAX+1},1,0)==COH_INVALID);
    printf("{\"passed\":true,\"checks\":%u,\"truncations\":%u,\"fuzz_cases\":%u,\"live_server\":false}\n",checks,truncations,fuzz_cases);
    return 0;
}
