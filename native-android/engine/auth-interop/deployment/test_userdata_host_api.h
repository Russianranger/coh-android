/* Host-only SQL/Win32 shim. It supplies synthetic result sets, never real ODBC. */
#pragma once
#include <cstdint>
#include <cstddef>
#include <cstring>
#include <cstdlib>
#include <cstdio>
#include <vector>
using ULONG=uint32_t;using SOCKET=int;using SQLSMALLINT=short;using SQLINTEGER=int;
using SQLRETURN=int;using SQLLEN=long;using SQLCHAR=unsigned char;using SQLPOINTER=void*;
using SQLHANDLE=void*;using SQLHDBC=void*;using SQLHENV=void*;using SQLHSTMT=void*;
#define SQL_NULL_HSTMT nullptr
#define SQL_NULL_HDBC nullptr
#define SQL_NULL_HENV nullptr
#define SQL_NULL_HANDLE nullptr
enum { SQL_HANDLE_STMT=1,SQL_HANDLE_ENV=2,SQL_HANDLE_DBC=3,SQL_ATTR_QUERY_TIMEOUT=4,
 SQL_ATTR_ODBC_VERSION=5,SQL_OV_ODBC3=6,SQL_ATTR_LOGIN_TIMEOUT=7,SQL_ATTR_CONNECTION_TIMEOUT=8,
 SQL_DRIVER_NOPROMPT=9,SQL_NTS=-3,SQL_SUCCESS=0,SQL_SUCCESS_WITH_INFO=1,SQL_NO_DATA=100,SQL_ERROR=-1,
 SQL_C_TINYINT=10,SQL_C_CHAR=11,SQL_C_LONG=12,SQL_C_SHORT=13,SQL_C_BINARY=14,
 SQL_PARAM_INPUT=15,SQL_C_ULONG=16,SQL_INTEGER=17,SQL_UNBIND=18,SQL_CLOSE=19,
 TRUE=1,FALSE=0,INVALID_SOCKET=-1 };
#define SQL_SUCCEEDED(x) ((x)==SQL_SUCCESS || (x)==SQL_SUCCESS_WITH_INFO)
struct in_addr {union {uint32_t S_addr;}S_un;};
#define s_addr S_un.S_addr
struct WSADATA{};
static int WSAStartup(int,WSADATA*){return 0;}static void WSACleanup(){}
#define MAKEWORD(a,b) ((a)|((b)<<8))
#define _snprintf std::snprintf
#define _snprintf_s(buf,size,count,...) std::snprintf(buf,size,__VA_ARGS__)
static uint32_t inet_addr(const char*s) {return !std::strcmp(s,"127.0.0.1")?0x0100007f:0x0200007f;}
struct hostent {char**h_addr_list;};
static hostent* gethostbyname(const char*s) {static uint32_t ip;static char*p[2];static hostent result;
 ip=inet_addr(s);p[0]=(char*)&ip;p[1]=nullptr;result.h_addr_list=p;return &result;}
struct HostColumn {int number,type;void*value;long size;SQLLEN*indicator;};
struct HostStatement {std::vector<HostColumn>columns;int kind=0,row=0;unsigned*uid=nullptr;};
static bool host_row_exists=true,host_row_null=false;
static int SQLAllocHandle(int kind,void*,void**out) {*out=kind==SQL_HANDLE_STMT?(void*)new HostStatement():(void*)1;return SQL_SUCCESS;}
static int SQLFreeHandle(int kind,void*handle) {if(kind==SQL_HANDLE_STMT)delete(HostStatement*)handle;return SQL_SUCCESS;}
static int SQLSetStmtAttr(void*,int,void*,int){return SQL_SUCCESS;}
static int SQLSetEnvAttr(void*,int,void*,int){return SQL_SUCCESS;}
static int SQLSetConnectAttr(void*,int,void*,int){return SQL_SUCCESS;}
static int SQLDriverConnectA(void*,void*,unsigned char*,int,void*,int,void*,int){return SQL_SUCCESS;}
static int SQLDisconnect(void*){return SQL_SUCCESS;}
static int SQLBindCol(void*handle,int number,int type,void*value,long size,SQLLEN*indicator) {
 ((HostStatement*)handle)->columns.push_back({number,type,value,size,indicator});return SQL_SUCCESS;}
static int SQLBindParameter(void*handle,int,int,int,int,int,int,void*value,int,SQLLEN*) {
 ((HostStatement*)handle)->uid=(unsigned*)value;return SQL_SUCCESS;}
static int SQLExecDirectA(void*handle,unsigned char*raw,int) {
 auto&s=*(HostStatement*)handle;const char*q=(char*)raw;s.row=0;
 if(std::strstr(q,"Select id, name"))s.kind=1;
 else if(std::strstr(q,"SELECT COUNT(*)"))s.kind=4;
 else if(std::strstr(q,"SELECT user_data,"))s.kind=2;
 else if(std::strstr(q,"SELECT user_game_data,"))s.kind=3;
 else if(std::strstr(q,"DELETE dbo.user_data")){host_row_exists=false;s.kind=0;}
 else if(std::strstr(q,"INSERT dbo.user_data")){host_row_exists=true;host_row_null=true;s.kind=0;}
 else return SQL_ERROR;return SQL_SUCCESS;
}
static int SQLFetch(void*handle) {
 auto&s=*(HostStatement*)handle;
 if(s.row++ || !s.kind || ((s.kind==2||s.kind==3)&&(!host_row_exists||!s.uid||*s.uid!=900001)))return SQL_NO_DATA;
 for(auto&c:s.columns) {
  if(s.kind==1) {
   const char*text=c.number==2?"Disposable SQL fixture":"127.0.0.1";
   if(c.type==SQL_C_CHAR)std::strncpy((char*)c.value,text,c.size);
   else if(c.type==SQL_C_TINYINT)*(char*)c.value=0;
   else if(c.type==SQL_C_SHORT)*(short*)c.value=23000;
   else *(int*)c.value=1;
  } else if(s.kind==4) *(int*)c.value=host_row_exists&&!host_row_null?1:0;
  else if(s.kind==2 && host_row_null) {if(c.indicator)*c.indicator=-1;}
  else {int offset=c.number==1?0:16;for(int i=0;i<c.size;++i)((unsigned char*)c.value)[i]=(unsigned char)(s.kind==2?offset+i:255-offset-i);
   if(c.indicator)*c.indicator=c.size;}
 }
 return SQL_SUCCESS;
}
static int SQLFreeStmt(void*handle,int option) {if(option==SQL_UNBIND)((HostStatement*)handle)->columns.clear();return SQL_SUCCESS;}
