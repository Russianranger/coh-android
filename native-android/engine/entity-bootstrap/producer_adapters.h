/* Fixture storage shells for full unchanged original producer. */
#define INLINEDBG inline
#define DBGAMESERVER_MAP_CONNECT 4
#define DBSERVER_MAP_XFER_OK 29 /* Source enum value; Map-to-map route excluded */
#define CONTAINER_MAPS 3
#define LOG_OLD_ERR(...) ((void)0)
typedef struct{unsigned nonQueueIP;int linkId;}GameClientLink;
typedef struct{NetLink*callback_link;int is_gameclient,handed_to_mapserver,map_id,id;char*account;U32 client_ip;int logging_in,active;}EntCon;
typedef struct{int id;U32 ip_list[2];int udp_port,tcp_port;}MapCon;
static struct{unsigned advertisedIp;int queue_server;}server_cfg;
static GameClientLink game_fixture;static MapCon map_fixture;
static Packet*pktCreateEx(void*link,int cmd){(void)link;memset(storage,0,sizeof(storage));memset(&packet,0,sizeof(packet));initBitStream(&packet.stream,(U8*)storage,sizeof(storage),Write,old_profile&1,0);pktSendBitsPack(&packet,1,cmd+((old_profile&2)?5:0));return &packet;}
static GameClientLink*dbClient_getGameClientByName(const char*account,NetLink*link){assert(account&&link);return &game_fixture;}
static Packet*dbClient_createPacket(int type,GameClientLink*game){assert(game==&game_fixture);return pktCreateEx(game,type);}
static void*dbListPtr(int type){assert(type==CONTAINER_MAPS);return &map_fixture;}
static MapCon*containerPtr(void*list,int id){assert(list==&map_fixture&&id==map_fixture.id);return &map_fixture;}
static U32 getMatchingIpType(const U32*ips,U32 client){(void)client;return ips[0];}
static int mpReclaimed(const void*p){assert(p);return 0;}
static unsigned source_sends;
static void pktSend(Packet**p,NetLink*link){assert(p&&*p==&packet&&link);source_sends++;}
