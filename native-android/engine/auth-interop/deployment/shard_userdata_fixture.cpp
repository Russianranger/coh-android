/* The surrounding ownership/SQL/send shells are diagnostic, never a service. */
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <winsock2.h>
#include <windows.h>
#include <sql.h>
#include <sqlext.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdarg>
#include <cwchar>
#include <map>
#include <vector>
#include <algorithm>
static_assert(sizeof(void*) == 4, "actual x86 ODBC required");
static_assert(sizeof(unsigned)==4 && sizeof(int)==4, "original SQL ABI");
/* ORIGINAL_SERVER_ID */
/* ORIGINAL_PROTOCOL */
enum { MAX_USERDATA=128, MAX_USERDATA_ORIG=16, MAX_USERDATA_NEW=112,
       MAX_ACCOUNT_LEN=14, MAX_SERVER_NAME=25 };
enum { LOG_NORMAL, LOG_ERROR, LOG_WARN };
#define AS_LOG_VERBOSE(...) ((void)0)
struct QuietLogger { void AddLog(int,const char*,...) {} };
static QuietLogger logger;
static SQLHDBC fixture_dbc=SQL_NULL_HDBC;
static int g_linDB;
static unsigned sql_errors, update_socket_calls, send_calls;
static std::vector<unsigned char> captured;
struct Profile { int worldPort=23000,payStatOverride=-1;
 bool dbHasClientPorts=true,allowUnknownServers=false,UserData=true,useQueue=false,sendQueueLevel=false; };
static Profile config;
class CDBConn {
public:
 SQLHSTMT m_stmt=SQL_NULL_HSTMT; int m_colNum=1,m_paramNum=1;
 explicit CDBConn(int) { if(!SQL_SUCCEEDED(SQLAllocHandle(SQL_HANDLE_STMT,fixture_dbc,&m_stmt))) std::exit(30);
  SQLSetStmtAttr(m_stmt,SQL_ATTR_QUERY_TIMEOUT,(SQLPOINTER)15,0); }
 ~CDBConn() { SQLFreeHandle(SQL_HANDLE_STMT,m_stmt); }
 bool Execute(const char*,...); bool Fetch(bool *nodata=nullptr); void ResetHtmt();
 void Bind(char*); void Bind(unsigned char*); void Bind(char*,int); void Bind(unsigned*); void Bind(int*); void Bind(short*);
 void Error(SQLSMALLINT,SQLHANDLE,const char*) { ++sql_errors; }
};
static int Assemble(char*,int,const char*,va_list);
static int capture_send(const char*format,va_list args) {
 char body[1024]; int n=Assemble(body,sizeof(body),format,args); ++send_calls;
 if(n<0 || n>(int)sizeof(body)) std::exit(31);
 captured.assign((unsigned char*)body,(unsigned char*)body+n); return TRUE;
}
class CSocketServerEx {
public: SOCKET GetSocket() { ++update_socket_calls; return INVALID_SOCKET; }
 int Send(const char*,...) { ++update_socket_calls; return FALSE; }
};
class CSocketServer {
public:
 ServerId serverid; unsigned closed=0;
 void CloseSocket() { ++closed; }
 int Send(const char*format,...) { va_list args;va_start(args,format);int n=capture_send(format,args);va_end(args);return n; }
};
typedef char ServerStatus;
/* ORIGINAL_WORLD_SERVER */
struct QuietLock { void WriteLock(){} void WriteUnlock(){} void ReadLock()const{} void ReadUnlock()const{} };
class CServerList {
public:
 typedef std::map<ServerId,WorldServer> ServerListType;
 ServerListType m_serverList; mutable QuietLock mylock;
 void Load(); ServerId SetServerSocketByAddress(in_addr,CSocketServer*);
 void SetServerStatus(ServerId,ServerStatus); bool IsServerUp(ServerId)const;
 in_addr GetInternalAddress(ServerId)const; ServerId GetFreeServerId()const;
};
static CServerList g_ServerList;
static int SendSocket(in_addr,const char*format,...) {
 va_list args;va_start(args,format);int n=capture_send(format,args);va_end(args);return n;
}
class AccountDB {
public:
 char AboutToPlay(int,char*,int,int,int,int,CSocketServerEx*,ServerId,int,int,int,int);
 char UpdateSocket(int,SOCKET,int,ServerId) { ++update_socket_calls;return S_SERVER_DOWN; }
 SOCKET FindSocket(int,ServerId,bool,ServerId*,char*) { return INVALID_SOCKET; }
};
static AccountDB accountdb;
static int GetIntFromPacket(const unsigned char*&packet) { int v;std::memcpy(&v,packet,4);packet+=4;return v; }
/* ORIGINAL_FUNCTIONS */
static bool hosted() { const char*a=std::getenv("RUNNER_ENVIRONMENT"),*b=std::getenv("GITHUB_ACTIONS");
 return a&&b&&!std::strcmp(a,"github-hosted")&&!std::strcmp(b,"true"); }
static bool instance_ok(const char*s) { if(std::strlen(s)!=35 || std::strncmp(s,"cohauth-ci-",11))return false;
 for(size_t i=11;i<35;++i)if(!((s[i]>='0'&&s[i]<='9')||(s[i]>='a'&&s[i]<='f')))return false;return true; }
static bool execute(const char*sql) { CDBConn c(g_linDB);return c.Execute(sql); }
static bool userdata_present() {
 CDBConn c(g_linDB);int count=-1;c.Bind(&count);
 if(!c.Execute("SELECT COUNT(*) FROM dbo.user_data WHERE uid=900001 AND user_data IS NOT NULL AND user_data_new IS NOT NULL AND DATALENGTH(user_data)=16 AND DATALENGTH(user_data_new)=112 AND DATALENGTH(user_game_data)=16 AND DATALENGTH(user_game_data_new)=112"))return false;
 return c.Fetch() && count==1;
}
static unsigned u32(const std::vector<unsigned char>&v,size_t at) {
 if(at+4>v.size())return 0xffffffffu;unsigned value;std::memcpy(&value,v.data()+at,4);return value;
}
static bool about_bytes(bool zero) {
 const char*name="sourcefixture";size_t off=5+std::strlen(name)+1;
 if(captured.size()!=off+12+128+12 || captured[0]!=SQ_ABOUT_TO_PLAY || u32(captured,1)!=900001
   || std::memcmp(captured.data()+5,name,std::strlen(name)+1) || u32(captured,off)!=0
   || u32(captured,off+4)!=2 || u32(captured,off+8)!=3 || u32(captured,off+140)!=1
   || u32(captured,off+144)!=123 || u32(captured,off+148)!=456)return false;
 for(unsigned i=0;i<128;++i)if(captured[off+12+i]!=(zero?0:i))return false;
 return true;
}
static bool game_bytes(bool zero) {
 if(captured.size()!=133 || captured[0]!=SQ_GAME_DATA || u32(captured,1)!=900001)return false;
 for(unsigned i=0;i<128;++i)if(captured[5+i]!=(zero?0:255-i))return false;return true;
}
int main(int argc,char**argv) {
 if(argc!=3 || !hosted() || !instance_ok(argv[1]) || std::strcmp(argv[2],"ODBC Driver 17 for SQL Server"))return 2;
 WSADATA sockets;if(WSAStartup(MAKEWORD(2,2),&sockets))return 3;
 SQLHENV env=SQL_NULL_HENV;SQLAllocHandle(SQL_HANDLE_ENV,SQL_NULL_HANDLE,&env);
 SQLSetEnvAttr(env,SQL_ATTR_ODBC_VERSION,(SQLPOINTER)SQL_OV_ODBC3,0);SQLAllocHandle(SQL_HANDLE_DBC,env,&fixture_dbc);
 SQLSetConnectAttr(fixture_dbc,SQL_ATTR_LOGIN_TIMEOUT,(SQLPOINTER)20,0);
 SQLSetConnectAttr(fixture_dbc,SQL_ATTR_CONNECTION_TIMEOUT,(SQLPOINTER)20,0);
 char connection[512];std::snprintf(connection,sizeof(connection),"Driver={%s};Server=(localdb)\\%s;Database=cohauth;Trusted_Connection=Yes;Encrypt=No;",argv[2],argv[1]);
 if(!SQL_SUCCEEDED(SQLDriverConnectA(fixture_dbc,nullptr,(SQLCHAR*)connection,SQL_NTS,nullptr,0,nullptr,SQL_DRIVER_NOPROMPT)))return 4;
 g_ServerList.Load();bool loaded=g_ServerList.m_serverList.size()==1;
 if(loaded) { const auto&w=g_ServerList.m_serverList.begin()->second;
  loaded=w.serverid.GetValueChar()==1 && !std::strcmp(w.name,"Disposable SQL fixture")
   && !std::strcmp(w.ip,"127.0.0.1") && !std::strcmp(w.inner_ip,"127.0.0.1")
   && w.outer_port==23000 && w.status==0 && w.s==nullptr && w.region_id==1; }
 CSocketServer transport;in_addr loop,unknown;loop.s_addr=inet_addr("127.0.0.1");unknown.s_addr=inet_addr("127.0.0.2");
 bool unknown_ok=!g_ServerList.SetServerSocketByAddress(unknown,&transport).IsValid() && g_ServerList.m_serverList.size()==1;
 ServerId shard=g_ServerList.SetServerSocketByAddress(loop,&transport);
 bool address_ok=shard.GetValueChar()==1 && !g_ServerList.IsServerUp(shard);
 // A test-owned in-memory transport is activated only for these source routines.
 // There is no socket, registered DbServer, client session or authentication grant.
 g_ServerList.SetServerStatus(shard,1);transport.serverid=shard;
 char account[]="sourcefixture";unsigned uid=900001;
 bool auth_ok=loaded && address_ok && unknown_ok && userdata_present();
 if(auth_ok) {accountdb.AboutToPlay(uid,account,0,2,3,0,nullptr,shard,1,0,123,456);auth_ok=about_bytes(false);}
 bool game_ok=auth_ok;if(game_ok) {ServerReadGameData(&transport,(unsigned char*)&uid);game_ok=game_bytes(false);}
 bool deleted=execute("DELETE dbo.user_data WHERE uid=900001"),missing_guard=deleted&&!userdata_present();
 accountdb.AboutToPlay(uid,account,0,2,3,0,nullptr,shard,1,0,123,456);bool missing_zero=about_bytes(true);
 ServerReadGameData(&transport,(unsigned char*)&uid);bool game_zero=game_bytes(true);
 bool inserted=execute("INSERT dbo.user_data(uid,user_data,user_data_new,user_game_data,user_game_data_new) VALUES(900001,NULL,NULL,0x00,0x00)");
 bool null_guard=inserted&&!userdata_present();
 bool no_queue=!config.useQueue&&!config.sendQueueLevel;
 bool passed=loaded&&address_ok&&unknown_ok&&auth_ok&&game_ok&&missing_guard&&null_guard&&missing_zero&&game_zero&&no_queue&&!sql_errors&&!update_socket_calls&&send_calls==4;
 const char*t="true",*f="false";
 std::printf("{\"schema\":\"coh-original-shard-userdata-odbc-v1\",\"passed\":%s,\"pointer_bytes\":%u,\"sql_connected\":true,\"shard_sql_loaded\":%s,\"source_address_lookup\":%s,\"unknown_address_refused\":%s,\"full_auth_sql_to_wire\":%s,\"full_game_sql_to_wire\":%s,\"missing_userdata_guard\":%s,\"null_userdata_guard\":%s,\"source_missing_userdata_zero_filled\":%s,\"source_game_missing_zero_filled\":%s,\"source_queue_disabled\":%s,\"source_sql_errors\":%u,\"network_registration_verified\":false,\"authentication_grant_generated\":false,\"authenticated_db_map_handoff_verified\":false}\n",passed?t:f,(unsigned)sizeof(void*),loaded?t:f,address_ok?t:f,unknown_ok?t:f,auth_ok?t:f,game_ok?t:f,missing_guard?t:f,null_guard?t:f,missing_zero?t:f,game_zero?t:f,no_queue?t:f,sql_errors);
 SQLDisconnect(fixture_dbc);SQLFreeHandle(SQL_HANDLE_DBC,fixture_dbc);SQLFreeHandle(SQL_HANDLE_ENV,env);WSACleanup();return passed?0:1;
}
