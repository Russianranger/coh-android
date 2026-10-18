/* New inventory composition peer only. Bodies are source-written synthetic
 * fixtures; actual run39094808506 supplied headers, never these body values.
 * No historical peer test entrypoint is invoked. */
#define COH_INITIAL_INVENTORY_PEER 1
#include "test_initial_peer.c"
#include "account-fixtures.h"
#include "inventory-fixtures.h"
static void initial_inventory_handle(UiPeer *u) {
    if(u->db_phase==2&&!initial_inventory_controls_sent&&!initial_inventory_sent) {
        uint8_t frame[COH_PROTOCOL_FRAME_MAX];struct sockaddr_in from;
        socklen_t length=sizeof(from);
        ssize_t bytes=recvfrom(u->db.fd,frame,sizeof(frame),MSG_PEEK,(struct sockaddr*)&from,&length);
        CHECK(bytes>0&&length==sizeof(from));CohNetPacket input;
        CHECK(coh_net_frame_decode(5,NULL,0,0,(CohBytes){frame,(size_t)bytes},&input)==COH_OK);
        CohProtocolBits bits;unsigned cmd=read_command(&input,&bits);
        if(cmd==COH_DB_LOGIN) {
            CHECK(ntohl(from.sin_addr.s_addr)==UINT32_C(0x7f000001)&&
                from.sin_port==htons(u->db_target.port));
            /* Preserve the original handler's exact LOGIN consumption and
             * complete players0 response. Add these four source packets to
             * its reliable response cache in the same network send order. */
            unsigned slot=reply_cursor[0]%16;ReplyCache prefix={0};
            CHECK(!recording);recording=&prefix;
            unsigned indices[]={0,1,1};
            for(unsigned i=0;i<3;i++) {
                unsigned n=indices[i];CHECK(!account_fixtures[n].aligned&&!account_fixtures[n].legacy);
                ui_message(&u->db,u->db_target,account_fixtures[n].data,
                    account_fixtures[n].bits,input.id,0);
                initial_inventory_controls_sent++;
            }
            unsigned n=8; /* Source direct sender: three actual serialized rows. */
            CHECK(!inventory_fixtures[n].aligned&&!inventory_fixtures[n].legacy&&
                inventory_fixtures[n].items==3&&!inventory_fixtures[n].authoritative&&
                !inventory_fixtures[n].free_only);
            ui_message(&u->db,u->db_target,inventory_fixtures[n].data,
                inventory_fixtures[n].bits,input.id,0);
            initial_inventory_sent++;
            CHECK(prefix.count==4);recording=NULL;handle(u,0);
            ReplyCache *saved=&reply_cache[0][slot];
            CHECK(saved->request_id==input.id&&saved->count+prefix.count<=16);
            memmove(saved->replies+prefix.count,saved->replies,
                saved->count*sizeof(*saved->replies));
            memcpy(saved->replies,prefix.replies,prefix.count*sizeof(*saved->replies));
            saved->count+=prefix.count;
            CHECK(initial_inventory_controls_sent==3&&initial_inventory_sent==1);return;
        }
    }
    handle(u,0);
}
