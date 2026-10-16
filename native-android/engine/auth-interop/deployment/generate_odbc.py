"""Generate an x86 real-driver experiment with unchanged original account methods.

This is not AuthServer execution. A minimal statement-owner/logger shell replaces
the server connection pool. No passwords, account values or diagnostics are
printed. Fixture rows contain byte patterns, with no supplied login credential.
"""
from source_audit import AUTH, digest, extract, pinned_sources


def prepare(root, directory):
    values, identities = pinned_sources(root)
    account, dbc = values[AUTH + 'Account.cpp'], values[AUTH + 'DBConn.cpp']
    names = ['CAccount::CAccount', 'CAccount::~CAccount', 'CAccount::LoadPassword', 'CAccount::Load']
    # The generic source extractor deliberately cannot match destructor syntax.
    destructor = 'CAccount::~CAccount()\n{\n}'
    if destructor not in account:
        raise ValueError('original_destructor_changed')
    functions = [extract(account, name) if name != 'CAccount::~CAccount' else destructor for name in names]
    functions += [extract(dbc, 'CDBConn::Fetch'), extract(dbc, 'CDBConn::ResetHtmt')]
    prefix = r'''#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <sql.h>
#include <sqlext.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ServerId.h"
#include "Account.h"
#include "Protocol.h"
static_assert(sizeof(void*)==4,"actual x86 ODBC required");
static_assert(sizeof(unsigned int)==4 && sizeof(int)==4,"original integer ABI");
static_assert(sizeof(ServerId)==1,"original server ID binding ABI");
#define LOG_ERROR 1
struct QuietLogger {void AddLog(int,const char*,...) {}};
static QuietLogger logger;
static SQLHDBC fixture_dbc=SQL_NULL_HDBC;
static int g_linDB;
static unsigned sql_errors;
class CDBConn {
public:
 SQLHSTMT m_stmt=SQL_NULL_HSTMT; int m_colNum=1,m_paramNum=1;
 explicit CDBConn(int){if(!SQL_SUCCEEDED(SQLAllocHandle(SQL_HANDLE_STMT,fixture_dbc,&m_stmt)))exit(30);SQLSetStmtAttr(m_stmt,SQL_ATTR_QUERY_TIMEOUT,(SQLPOINTER)15,0);}
 ~CDBConn(){SQLFreeHandle(SQL_HANDLE_STMT,m_stmt);}
 bool Fetch(bool *nodata); void ResetHtmt();
 void Error(SQLSMALLINT,SQLHANDLE,const char*){sql_errors++;}
};
'''
    suffix = r'''
static bool hosted(void){const char *a=getenv("RUNNER_ENVIRONMENT"),*b=getenv("GITHUB_ACTIONS");return a&&b&&!strcmp(a,"github-hosted")&&!strcmp(b,"true");}
static bool instance_ok(const char *s){if(strlen(s)!=35||strncmp(s,"cohauth-ci-",11))return false;for(size_t i=11;i<35;i++)if(!((s[i]>='0'&&s[i]<='9')||(s[i]>='a'&&s[i]<='f')))return false;return true;}
static bool execute(const char *sql){SQLHSTMT stmt; if(!SQL_SUCCEEDED(SQLAllocHandle(SQL_HANDLE_STMT,fixture_dbc,&stmt)))return false;SQLSetStmtAttr(stmt,SQL_ATTR_QUERY_TIMEOUT,(SQLPOINTER)15,0);SQLRETURN r=SQLExecDirectA(stmt,(SQLCHAR*)sql,SQL_NTS);SQLFreeHandle(SQL_HANDLE_STMT,stmt);return SQL_SUCCEEDED(r);}
int main(int argc,char **argv){
 if(argc!=3||!hosted()||!instance_ok(argv[1])||(strcmp(argv[2],"ODBC Driver 17 for SQL Server")&&strcmp(argv[2],"ODBC Driver 18 for SQL Server")))return 2;
 SQLHENV env=SQL_NULL_HENV;SQLAllocHandle(SQL_HANDLE_ENV,SQL_NULL_HANDLE,&env);SQLSetEnvAttr(env,SQL_ATTR_ODBC_VERSION,(SQLPOINTER)SQL_OV_ODBC3,0);SQLAllocHandle(SQL_HANDLE_DBC,env,&fixture_dbc);
 SQLSetConnectAttr(fixture_dbc,SQL_ATTR_LOGIN_TIMEOUT,(SQLPOINTER)20,0);SQLSetConnectAttr(fixture_dbc,SQL_ATTR_CONNECTION_TIMEOUT,(SQLPOINTER)20,0);
 char connection[512];snprintf(connection,sizeof(connection),"Driver={%s};Server=(localdb)\\%s;Database=cohauth;Trusted_Connection=Yes;Encrypt=No;",argv[2],argv[1]);
 SQLRETURN connected=SQLDriverConnectA(fixture_dbc,NULL,(SQLCHAR*)connection,SQL_NTS,NULL,0,NULL,SQL_DRIVER_NOPROMPT);
 if(!SQL_SUCCEEDED(connected)){puts("{\"connection_succeeded\":false,\"real_account_login_verified\":false}");SQLFreeHandle(SQL_HANDLE_DBC,fixture_dbc);SQLFreeHandle(SQL_HANDLE_ENV,env);return 3;}
 CAccount account;char password[129]={0};unsigned char hash=0;unsigned int salt=0;
 int result=account.LoadPassword("odbcprobe",password,hash,salt);bool password_ok=result==S_ALL_OK&&hash==1&&salt==145;
 for(unsigned i=0;i<128;i++)password_ok=password_ok&&((unsigned char)password[i]==i);
 bool zero_ok=false;
 if(execute("UPDATE dbo.user_auth SET hash_type=0 WHERE account='odbcprobe'")){hash=255;salt=0;zero_ok=account.LoadPassword("odbcprobe",password,hash,salt)==S_ALL_OK&&hash==0&&salt==145;}
 bool missing_password_rejected=account.LoadPassword("missingprobe",password,hash,salt)==S_INVALID_ACCOUNT;
 int stats_result=account.Load("odbcprobe");
 bool stats_ok=stats_result==S_ALL_OK&&account.uid==424242&&account.pay_stat==1&&account.login_flag==2&&account.warn_flag==3&&account.block_flag==4&&account.block_flag2==5&&account.subscription_flag==6&&account.lastworld.GetValueChar()==7&&account.queueLevel==8&&account.loyalty==9&&account.loyaltyLegacy==10&&account.regions[0]==11&&account.regions[1]==-1;
 bool timestamp_ok=stats_result==S_ALL_OK&&account.block_end_date.year==2020&&account.block_end_date.month==2&&account.block_end_date.day==3&&account.block_end_date.hour==4&&account.block_end_date.minute==5&&account.block_end_date.second==6&&account.block_end_date.fraction==123000000;
 bool missing_stats_rejected=account.Load("missingprobe")!=S_ALL_OK;
 bool passed=password_ok&&zero_ok&&missing_password_rejected&&stats_ok&&timestamp_ok&&missing_stats_rejected;
 printf("{\"passed\":%s,\"pointer_bytes\":%u,\"connection_succeeded\":true,\"password_output_conversion\":%s,\"zero_hash_output_conversion\":%s,\"missing_password_rejected\":%s,\"stats_outputs\":%s,\"timestamp_conversion\":%s,\"missing_stats_rejected\":%s,\"original_error_callbacks\":%u,\"real_account_login_verified\":false}\n",passed?"true":"false",(unsigned)sizeof(void*),password_ok?"true":"false",zero_ok?"true":"false",missing_password_rejected?"true":"false",stats_ok?"true":"false",timestamp_ok?"true":"false",missing_stats_rejected?"true":"false",sql_errors);
 SecureZeroMemory(password,sizeof(password));SQLDisconnect(fixture_dbc);SQLFreeHandle(SQL_HANDLE_DBC,fixture_dbc);SQLFreeHandle(SQL_HANDLE_ENV,env);return passed?0:1;
}
'''
    code = prefix + '\n'.join(functions) + suffix
    (directory / 'original-odbc.cpp').write_text(code)
    fixture = "USE cohauth;\nSET NOCOUNT ON;\n"
    fixture += "INSERT INTO dbo.user_auth(account,password,salt,hash_type) VALUES('odbcprobe',0x" + bytes(range(128)).hex() + ",145,1);\n"
    fixture += "INSERT INTO dbo.user_account(account,uid,pay_stat,login_flag,warn_flag,block_flag,block_flag2,subscription_flag,last_world,block_end_date,queue_level,loyalty_points,loyalty_legacy_points) VALUES('odbcprobe',424242,1,2,3,4,5,6,7,'2020-02-03T04:05:06.123',8,9,10);\n"
    fixture += "INSERT INTO dbo.user_server_group(uid,server_group_id) VALUES(424242,11);\n"
    (directory / 'odbc-fixture.sql').write_text(fixture)
    return {'schema': 'coh-original-odbc-candidate-v1', 'generated_source_sha256': digest(code.encode()),
            'fixture_sha256': digest(fixture.encode()), 'source_identities': identities,
            'original_function_sha256': {name: digest(body.encode()) for name, body in zip(names + ['CDBConn::Fetch', 'CDBConn::ResetHtmt'], functions)},
            'scope': 'Unchanged account methods and Fetch/ResetHtmt with a minimal statement owner; actual x86 driver only when hosted runner executes.',
            'fixture_login_attempted': False, 'authserver_started': False, 'real_account_login_verified': False,
            'original_password_hash_algorithm_executed': False}
