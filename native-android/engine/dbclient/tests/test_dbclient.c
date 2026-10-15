#include "../coh_dbclient.h"
#include "fixtures.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do { checks++; if(!(x)){fprintf(stderr,"DB check failed line %d: %s\n",__LINE__,#x);exit(1);} } while(0)
static void config(CohDbLogin *v) {
    memset(v,0,sizeof(*v));strcpy(v->account,"fixture");strcpy(v->patch_version,"disposable-native-test");
    strcpy(v->patch_message,"updater fixture");strcpy(v->system_spec,"Disabled");
    v->user_id=0x12345678;v->protocol_version=COH_DB_PROTOCOL_VERSION;v->cookie=0x89abcdef;
    v->no_timeout=1;v->keyed_access_level=7;strcpy(v->keyed_access_issued_to,"authorized test fixture");
    for(unsigned i=0;i<COH_DB_AUTH_BYTES;i++)v->auth_user_data[i]=(uint8_t)(i^0xa5);
    for(unsigned i=0;i<16;i++)v->executable_checksum[i]=(uint8_t)(i*13);
}
static void players_test(const unsigned char *data,size_t size,size_t bits,int mode,int legacy) {
    CohDbPlayers p;memset(&p,0xa5,sizeof(p));
    CHECK(coh_db_players_parse((CohBytes){data,size},bits,mode,legacy,&p)==COH_OK);
    CHECK(p.user_id==12345&&p.max_slots==5&&p.base_slots==8&&p.bonus_slots==2&&p.selectable_count==1);
    CHECK(p.ignored_remote_command==1&&p.vip==1&&p.beta_shard==0&&p.vip_shard==1);
    CHECK(!strcmp(p.players[0].name,"Native Fixture")&&p.players[0].wire_slot==0);
    CHECK(p.players[1].empty&&p.players[2].visitor&&p.players[3].invalid&&p.players[4].slot_lock==2);
    CHECK(p.players[0].scale==0.25f&&p.players[0].bone_scale==-0.5f&&p.players[0].skin_color==0x11223344);
    CHECK(!strcmp(p.players[0].map_name,"maps/City_Zones/City_01_01/City_01_01.txt"));
    for(unsigned i=0;i<128;i++){CHECK(p.auth_user_data[i]==(uint8_t)(i^0x31));CHECK(p.overridden_auth[i]==(uint8_t)(i^0x78));}
    CohDbChoose choice;CHECK(coh_db_player_choose(&p,0,0x0100007f,0,&choice)==COH_OK);
    CHECK(choice.slot==0&&!strcmp(choice.name,"Native Fixture"));
    for(unsigned i=1;i<5;i++)CHECK(coh_db_player_choose(&p,i,0,0,&choice)==COH_STATE);
    CHECK(coh_db_player_choose(&p,5,0,0,&choice)==COH_INVALID);
    for(size_t n=0;n<bits;n++) {
        CohDbPlayers before;p.players[0].level=0x12345678;before=p;
        CHECK(coh_db_players_parse((CohBytes){data,size},n,mode,legacy,&p)!=COH_OK);
        CHECK(!memcmp(&p,&before,sizeof(p)));
    }
    CHECK(coh_db_players_parse((CohBytes){data,size},bits,mode,!legacy,&p)==COH_UNSUPPORTED);
}
static void encode_test(const unsigned char *login,size_t login_size,size_t login_bits,const unsigned char *choose,size_t choose_size,size_t choose_bits,int mode,int legacy) {
    CohDbLogin v;config(&v);uint8_t out[4096];size_t bits=0;
    CHECK(coh_db_login_encode(&v,mode,legacy,out,sizeof(out),&bits)==COH_OK);
    CHECK(bits==login_bits&&(bits+7)/8==login_size&&!memcmp(out,login,login_size));
    CohDbChoose c={3,0x0100007f,0,{0}};strcpy(c.name,"Native Fixture");
    CHECK(coh_db_choose_encode(&c,mode,legacy,out,sizeof(out),&bits)==COH_OK);
    CHECK(bits==choose_bits&&(bits+7)/8==choose_size&&!memcmp(out,choose,choose_size));
    memset(out,0xa5,sizeof(out));uint8_t before[4096];memcpy(before,out,sizeof(out));bits=123;
    CHECK(coh_db_login_encode(&v,mode,legacy,out,1,&bits)==COH_LIMIT);
    CHECK(bits==123&&!memcmp(before,out,sizeof(out)));
    memset(v.account,'x',sizeof(v.account));CHECK(coh_db_login_encode(&v,mode,legacy,out,sizeof(out),&bits)==COH_LIMIT);
    CHECK(bits==123&&!memcmp(before,out,sizeof(out)));
    config(&v);v.protocol_version=0;CHECK(coh_db_login_encode(&v,mode,legacy,out,sizeof(out),&bits)==COH_INVALID);
    config(&v);v.no_version_check=2;CHECK(coh_db_login_encode(&v,mode,legacy,out,sizeof(out),&bits)==COH_INVALID);
    CHECK(coh_db_choose_encode(&c,mode,legacy,out,1,&bits)==COH_LIMIT);
    CHECK(bits==123&&!memcmp(before,out,sizeof(out)));
    c.slot=64;CHECK(coh_db_choose_encode(&c,mode,legacy,out,sizeof(out),&bits)==COH_INVALID);
    coh_db_wipe(&v,sizeof(v));for(size_t i=0;i<sizeof(v);i++)CHECK(!((uint8_t *)&v)[i]);
}
static uint32_t rng=0x414254;
static uint32_t next(void){rng=rng*1664525u+1013904223u;return rng;}
static void map_test(const unsigned char *data,size_t size,size_t bits,int mode,int legacy) {
    CohAuthMapHandoff map;memset(&map,0x5a,sizeof(map));
    CHECK(coh_db_map_handoff_parse((CohBytes){data,size},bits,mode,legacy,&map)==COH_OK);
    CHECK(map.link_id==17&&map.map_id==1&&map.address[0]==0x0100007f&&map.udp_port==7002&&map.tcp_port==7003&&map.cookie==123456);
    for(size_t n=0;n<bits;n++) {
        CohAuthMapHandoff before=map;
        CHECK(coh_db_map_handoff_parse((CohBytes){data,size},n,mode,legacy,&map)!=COH_OK);
        CHECK(!memcmp(&map,&before,sizeof(map)));
    }
}
int main(void) {
    encode_test(login0,sizeof(login0),login0_bits,choose0,sizeof(choose0),choose0_bits,0,0);
    encode_test(login1,sizeof(login1),login1_bits,choose1,sizeof(choose1),choose1_bits,1,0);
    encode_test(login_old0,sizeof(login_old0),login_old0_bits,choose_old0,sizeof(choose_old0),choose_old0_bits,0,1);
    encode_test(login_old1,sizeof(login_old1),login_old1_bits,choose_old1,sizeof(choose_old1),choose_old1_bits,1,1);
    players_test(players0,sizeof(players0),players0_bits,0,0);
    players_test(players1,sizeof(players1),players1_bits,1,0);
    players_test(players_old0,sizeof(players_old0),players_old0_bits,0,1);
    players_test(players_old1,sizeof(players_old1),players_old1_bits,1,1);
    map_test(map0,sizeof(map0),map0_bits,0,0);map_test(map1,sizeof(map1),map1_bits,1,0);
    map_test(map_old0,sizeof(map_old0),map_old0_bits,0,1);map_test(map_old1,sizeof(map_old1),map_old1_bits,1,1);
    CohAuthMapHandoff map;memset(&map,0x5a,sizeof(map));CohAuthMapHandoff original=map;
    CHECK(coh_db_map_handoff_parse((CohBytes){badmap0,sizeof(badmap0)},badmap0_bits,0,0,&map)==COH_INVALID);
    CHECK(!memcmp(&map,&original,sizeof(map)));
    CHECK(coh_db_server_error_parse((CohBytes){error0,sizeof(error0)},error0_bits,0,0)==COH_OK);
    CHECK(coh_db_server_error_parse((CohBytes){error1,sizeof(error1)},error1_bits,1,0)==COH_OK);
    CHECK(coh_db_server_error_parse((CohBytes){error_old0,sizeof(error_old0)},error_old0_bits,0,1)==COH_OK);
    CHECK(coh_db_server_error_parse((CohBytes){error_old1,sizeof(error_old1)},error_old1_bits,1,1)==COH_OK);
    for(size_t n=0;n<error0_bits;n++)CHECK(coh_db_server_error_parse((CohBytes){error0,sizeof(error0)},n,0,0)!=COH_OK);
    const unsigned char *queues[]={queue0,queue1};size_t sizes[]={sizeof(queue0),sizeof(queue1)},bits[]={queue0_bits,queue1_bits};
    for(int mode=0;mode<2;mode++) {
        CohDbQueue q={0,0};CHECK(coh_db_queue_parse((CohBytes){queues[mode],sizes[mode]},bits[mode],mode,0,&q)==COH_OK);CHECK(q.position==3&&q.count==10);
        for(size_t n=0;n<bits[mode];n++){CohDbQueue before=q;CHECK(coh_db_queue_parse((CohBytes){queues[mode],sizes[mode]},n,mode,0,&q)!=COH_OK);CHECK(!memcmp(&q,&before,sizeof(q)));}
    }
    CohDbPlayers out,before;memset(&out,0xb3,sizeof(out));before=out;
    CHECK(coh_db_players_parse((CohBytes){overslots0,sizeof(overslots0)},overslots0_bits,0,0,&out)==COH_LIMIT);
    CHECK(coh_db_players_parse((CohBytes){badscale0,sizeof(badscale0)},badscale0_bits,0,0,&out)==COH_INVALID);
    CHECK(coh_db_players_parse((CohBytes){badlock0,sizeof(badlock0)},badlock0_bits,0,0,&out)==COH_UNSUPPORTED);
    CHECK(!memcmp(&out,&before,sizeof(out)));
    CHECK(sizeof(large0)>1472&&sizeof(large1)>1472);
    CHECK(coh_db_players_parse((CohBytes){large0,sizeof(large0)},large0_bits,0,0,&out)==COH_OK);
    CHECK(out.max_slots==64&&out.selectable_count==60&&!strcmp(out.players[63].name,"Additional Fixture 63"));
    CHECK(coh_db_players_parse((CohBytes){large1,sizeof(large1)},large1_bits,1,0,&out)==COH_OK);
    CHECK(out.max_slots==64&&out.selectable_count==60&&!strcmp(out.players[63].name,"Additional Fixture 63"));
    memset(&out,0xb3,sizeof(out));before=out;
    uint8_t random[1024];unsigned malformed=0;
    for(unsigned k=0;k<10000;k++) {
        size_t n=next()%sizeof(random)+1;for(size_t i=0;i<n;i++)random[i]=(uint8_t)next();
        CohStatus s=coh_db_players_parse((CohBytes){random,n},n*8-(next()%8),k%2,(k/2)%2,&out);
        CHECK(s!=COH_OK);CHECK(!memcmp(&out,&before,sizeof(out)));malformed++;
    }
    CHECK(coh_db_players_parse((CohBytes){random,sizeof(random)},sizeof(random)*8,2,0,&out)==COH_INVALID);
    printf("{\"passed\":true,\"checks\":%u,\"malformed_inputs\":%u,\"real_server_login\":false}\n",checks,malformed);
    return 0;
}
