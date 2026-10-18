/* New account-control composition peer only. Old peer entrypoints are included
 * for setup but never called as a test suite. Generated fixture values remain
 * synthetic; actual run39092477566 supplied headers, never these bodies. */
#define COH_INITIAL_ACCOUNT_PEER 1
#include "test_initial_peer.c"
#include "account-fixtures.h"
static void initial_account_handle(UiPeer *u) {
    if(u->db_phase==2&&!initial_account_controls_sent) {
        uint8_t frame[COH_PROTOCOL_FRAME_MAX];struct sockaddr_in from;
        socklen_t length=sizeof(from);
        ssize_t bytes=recvfrom(u->db.fd,frame,sizeof(frame),MSG_PEEK,(struct sockaddr*)&from,&length);
        CHECK(bytes>0&&length==sizeof(from));CohNetPacket input;
        CHECK(coh_net_frame_decode(5,NULL,0,0,(CohBytes){frame,(size_t)bytes},&input)==COH_OK);
        CohProtocolBits bits;unsigned cmd=read_command(&input,&bits);
        if(cmd==COH_DB_LOGIN) {
            CHECK(ntohl(from.sin_addr.s_addr)==UINT32_C(0x7f000001)&&
                from.sin_port==htons(u->db_target.port));
            /* The original handler validates/consumes this exact datagram and
             * sends its complete unchanged players0 fixture afterwards. */
            unsigned slot=reply_cursor[0]%16;ReplyCache controls={0};
            CHECK(!recording);recording=&controls;
            unsigned indices[]={0,1,1};
            for(unsigned i=0;i<3;i++) {
                unsigned n=indices[i];CHECK(!account_fixtures[n].aligned&&!account_fixtures[n].legacy);
                ui_message(&u->db,u->db_target,account_fixtures[n].data,
                    account_fixtures[n].bits,input.id,0);
                initial_account_controls_sent++;
            }
            CHECK(controls.count==3);recording=NULL;handle(u,0);
            ReplyCache *saved=&reply_cache[0][slot];
            CHECK(saved->request_id==input.id&&saved->count+controls.count<=16);
            memmove(saved->replies+controls.count,saved->replies,
                saved->count*sizeof(*saved->replies));
            memcpy(saved->replies,controls.replies,controls.count*sizeof(*saved->replies));
            saved->count+=controls.count;
            CHECK(initial_account_controls_sent==3);return;
        }
    }
    handle(u,0);
}
