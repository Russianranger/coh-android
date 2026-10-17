// Exact original DB startup functions with bounded ODBC/platform fixtures.
#include <cstdio>
#include <cstdlib>
#include <cstddef>
#include <cstring>
using SQLRETURN=int; using SQLHENV=int; using SQLHDBC=int; using SQLSMALLINT=short;
using SQLCHAR=unsigned char; using SQLPOINTER=void*;
#define SQL_SUCCESS 0
#define SQL_SUCCESS_WITH_INFO 1
#define SQL_HANDLE_ENV 1
#define SQL_HANDLE_DBC 2
#define SQL_HANDLE_STMT 3
#define SQL_NULL_HANDLE 0
#define SQL_NULL_HENV 0
#define SQL_ATTR_CONNECTION_POOLING 1
#define SQL_CP_ONE_PER_DRIVER 1
#define SQL_IS_INTEGER 0
#define SQL_ATTR_ODBC_VERSION 2
#define SQL_OV_ODBC3 3
#define SQL_ATTR_LOGIN_TIMEOUT 3
#define SQL_ATTR_CONNECTION_TIMEOUT 4
#define SQL_DRIVER_NOPROMPT 0
#define TRUE 1
#define FALSE 0
#define LOG_ERROR 1
#define AS_LOG_VERBOSE(...) ((void)0)
struct {template<class...A>void AddLog(int,const char*,A...){}} logger;
static bool env_ok=true,attr_ok=true,login_ok=true,pool_ok=false;
static unsigned sleeps=0, locks=0, calls=0;
static int SQLSetEnvAttr(int handle,int,...){return handle&&!attr_ok?-1:SQL_SUCCESS;}
static int SQLAllocHandle(int kind,int,int*value){*value=kind;return kind==SQL_HANDLE_ENV&&!env_ok?-1:SQL_SUCCESS;}
static int SQLSetConnectAttr(int,int,...){return SQL_SUCCESS;}
static int SQLDriverConnectA(int,void*,unsigned char*,short,unsigned char*,size_t,short*,int){++calls;return pool_ok?SQL_SUCCESS:-1;}
static int SQLFreeHandle(int,int){return SQL_SUCCESS;}
struct Stop{};
static void Sleep(int milliseconds){if(milliseconds!=100)std::abort();if(++sleeps==3)throw Stop{};}
struct Lock {void Enter(){++locks;}void Leave(){--locks;}};
struct SQLPool {SQLPool*pNext=nullptr;int hdbc=0,stmt=0;bool reset=false;};
class DBEnv {public:int m_connCount=0,m_henv=0;SQLPool*m_pSqlPool=nullptr,*m_pFreeSqlPool=nullptr,*m_pFreeSqlPoolEnd=nullptr;Lock m_lock;unsigned char m_connStr[2]={};
 bool Init(int);bool Login(){return login_ok;}void AllocSQLPool();~DBEnv(){delete[]m_pSqlPool;}};
class CDBConn {public:DBEnv*m_pEnv=nullptr;SQLPool*m_pCurSql=nullptr;int m_stmt=0,m_colNum=0,m_paramNum=0;CDBConn(DBEnv*);};
/* EXACT_FUNCTIONS */
static unsigned checks;
#define CHECK(x) do{++checks;if(!(x)){std::fprintf(stderr,"check failed line %d\n",__LINE__);return 1;}}while(0)
int main(){
 {DBEnv env;env_ok=false;CHECK(!env.Init(2));env_ok=true;}
 {DBEnv env;attr_ok=false;CHECK(!env.Init(2));attr_ok=true;}
 // Exact Init deletes its array on Login failure. Clear only dangling fixture field before its destructor.
 {DBEnv env;login_ok=false;CHECK(!env.Init(2));env.m_pSqlPool=nullptr;login_ok=true;}
 {DBEnv env;pool_ok=false;calls=0;CHECK(env.Init(2));CHECK(calls==2);CHECK(env.m_pFreeSqlPool==nullptr);
  bool stopped=false;try{CDBConn connection(&env);}catch(const Stop&){stopped=true;}
  CHECK(stopped);CHECK(sleeps==3);CHECK(locks==0);}
 {DBEnv env;pool_ok=true;CHECK(env.Init(2));CHECK(env.m_pFreeSqlPool!=nullptr);unsigned before=sleeps;
  CDBConn connection(&env);CHECK(connection.m_stmt==SQL_HANDLE_STMT);CHECK(connection.m_colNum==1&&connection.m_paramNum==1);CHECK(sleeps==before);CHECK(locks==0);}
 std::printf("{\"passed\":true,\"checks\":%u,\"empty_pool_init_returns_true\":true,\"empty_pool_wait_observed\":3,\"healthy_pool_constructs\":true,\"windows_executed\":false,\"live_service_executed\":false}\n",checks);
}
