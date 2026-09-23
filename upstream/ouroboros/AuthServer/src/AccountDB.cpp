// AccountDB.cpp: implementation of the AccountDB class.
//
//////////////////////////////////////////////////////////////////////

#include "PreComp.h"


bool SendWantedServerLogout( char *name, int uid, ServerId gameserver )
{
_BEFORE
    if ( (!config.UseWantedSystem) || WantedServerReconnect || ( !gameserver.IsValid()) )
        return true;

    char sndmsg[24];
    memset(sndmsg,0, 24);
    
    switch( config.gameId ) {
    case LINEAGE2_GAME_CODE :
        sndmsg[0]=2;
        break;
    default:
        return true;
        break;
    }

    memcpy( sndmsg+1, &uid, 4 );
    strcpy( sndmsg+5, name );
    sndmsg[19] = gameserver.GetValueChar();
    time_t stime = time(NULL);
    memcpy( sndmsg+20, &stime, 4 );

    if (pWantedSocket && config.UseWantedSystem && (!WantedServerReconnect)) {
        logger.AddLog( LOG_WARN, "Wanted User LogOut, %s", name );
        gWantedLock.ReadLock();
        pWantedSocket->AddRef();
        pWantedSocket->Send("cb", AW_QUIT, 24, sndmsg );
        pWantedSocket->ReleaseRef();
        gWantedLock.ReadUnlock();
    }
_AFTER_FIN
    return true;
}

BOOL SendSocketEx(SOCKET s, const char *format, ...);

AccountDB::AccountDB()
{
}

AccountDB::~AccountDB()
{
}


bool AccountDB::FindAccount( int uid, char *account, ServerId & lastServer, int regions[MAX_REGIONS])
{
    HANDLE hTimer=NULL;
    m_lock.Enter();
    UserMap::iterator it = usermap.find(uid);
    if ( it != usermap.end()) {
        strncpy( account, it->second.account, MAX_ACCOUNT_LEN+1 );
        hTimer = it->second.timerHandle;
        it->second.timerHandle = NULL;
        lastServer = it->second.lastworld;
        memcpy(regions,it->second.regions,sizeof(it->second.regions));
        m_lock.Leave();
    }else{
        m_lock.Leave();
        lastServer.SetInvalid();
        return false;
    }

    if ( hTimer != NULL  )
        DeleteTimerQueueTimer( NULL, hTimer, NULL );

    return true;
}


bool  AccountDB::FindAccount( int uid, char *account, int *loginflag, int *warnflag, int *pay_stat, int *md5key, int *queueLevel, int *loyalty, int *loyatyLegacy)
{
    bool result=false;
    //int smd5key = 0;
    HANDLE hTimer=NULL;
    
    m_lock.Enter();
    UserMap::iterator it = usermap.find(uid);
    if ( it != usermap.end()) {
        strncpy( account, it->second.account, MAX_ACCOUNT_LEN+1 );
        *loginflag = it->second.loginflag;
        *warnflag = it->second.warnflag;
        *pay_stat = it->second.stat;
        hTimer = it->second.timerHandle;
        *md5key = it->second.md5key;
        *queueLevel = it->second.queueLevel;
        *loyalty = it->second.loyalty;
        *loyatyLegacy = it->second.loyaltyLegacy;
        it->second.timerHandle = NULL;
        result = true;
    }
    m_lock.Leave();
    
    if ( hTimer != NULL  )
        DeleteTimerQueueTimer( NULL, hTimer, NULL );

    return result;
}

int AccountDB::UpdateSocket( int uid, SOCKET s, int md5key, ServerId serverid  )
{
_BEFORE
    m_lock.Enter();
    UserMap::iterator it = usermap.find(uid);
    if ( it != usermap.end())
    {
        if ( md5key == it->second.md5key )
        {
            if (  it->second.um_mode != UM_IN_GAME ) {
                it->second.s = s;
                it->second.selectedServerid = serverid;
                it->second.serverid.SetInvalid();
                m_lock.Leave();

                return S_ALL_OK;
            } else {
                m_lock.Leave();
                return S_ALREADY_PLAY_GAME;
            }
        } else{
            m_lock.Leave();
            return S_INCORRECT_MD5Key;
        }
    } else{
        m_lock.Leave();
        return S_NO_LOGININFO;
    }
_AFTER_FIN
    return S_NO_LOGININFO;
}

bool AccountDB::RegAccount( LoginUser *loginuser, int uid, CSocketServerEx *sEx, int remainTime, int quotaTime )
{
    bool result=false;

    m_lock.Enter();
    std::pair<UserMap::iterator, bool> r = usermap.insert(UserMap::value_type(uid, *loginuser));
    result = r.second;
    m_lock.Leave();
    
    if ( result == false ){
        KickAccount( uid,S_ALREADY_LOGIN, true );
        sEx->Send( "cc", AC_LOGIN_FAIL, S_ALREADY_LOGIN );
    }  else {
        sEx->um_mode = UM_LOGIN;
        //sEx->Send( "cddddddddd", AC_LOGIN_OK, uid, sEx->GetMd5Key(), 
        //                         g_updateKey, 
        //                         g_updateKey2, 
        //                         loginuser->stat, 
        //                         remainTime, 
        //                         quotaTime, loginuser->warnflag, loginuser->loginflag );

        if (config.useQueue || config.sendQueueLevel)
        {
            if (config.ProtocolVer >= GR_REACTIVATION_PROTOCOL_VERSION) {
                sEx->Send( "cdddddddddddd", AC_LOGIN_OK, uid, sEx->GetMd5Key(), 
                                g_updateKey, 
                                g_updateKey2, 
                                loginuser->stat, 
                                loginuser->loyalty,
                                remainTime, 
                                quotaTime, 
                                loginuser->warnflag, 
                                loginuser->loginflag,
                                config.IsReactivationActive(),
                                loginuser->queueLevel );
            } else {
                sEx->Send( "cddddddddddddd", AC_LOGIN_OK, uid, sEx->GetMd5Key(), 
                    g_updateKey, 
                    g_updateKey2, 
                    loginuser->stat, 
                    loginuser->loyalty,
                    remainTime, 
                    quotaTime, 
                    loginuser->warnflag, 
                    loginuser->loginflag,
                    loginuser->queueLevel );
            }
        }
        else
        {
            if (config.ProtocolVer >= GR_REACTIVATION_PROTOCOL_VERSION) {
                sEx->Send( "cddddddddddd", AC_LOGIN_OK, uid, sEx->GetMd5Key(), 
                                g_updateKey, 
                                g_updateKey2, 
                                loginuser->stat, 
                                loginuser->loyalty,
                                remainTime, 
                                quotaTime, 
                                loginuser->warnflag, 
                                loginuser->loginflag,
                                config.IsReactivationActive() );
            } else {
                sEx->Send( "cdddddddddddd", AC_LOGIN_OK, uid, sEx->GetMd5Key(), 
                    g_updateKey, 
                    g_updateKey2, 
                    loginuser->stat, 
                    loginuser->loyalty,
                    remainTime, 
                    quotaTime, 
                    loginuser->warnflag, 
                    loginuser->loginflag,
                    config.IsReactivationActive() );
            }
        }


    }

    return result;
}

/**
 * Called when a user is done waiting in the queue and has actually logged into the game.
 * Update the login time to the current time (queue entered time stays as-is)
 */
void AccountDB::FinishedQueue( int uid )
{
    m_lock.Enter();
    UserMap::iterator it = usermap.find(uid);
    if ( it != usermap.end())
    {
        it->second.logintime=time(NULL);
    }
    m_lock.Leave();
}

bool AccountDB::KickAccount( int uid, char reasoncode, bool sendmsg )
{
    bool result = false;
    ServerId serverid;
    char account[MAX_ACCOUNT_LEN+1];

    SOCKET oldSocket=INVALID_SOCKET;
    UserMode usermode=UM_PRE_LOGIN;
    char gender=0;
    in_addr ip;
    account[0]=0;
    int ssn=0, ssn2=0, stat = 0;
    UINT warn_flag=0;
    char age=0;
    short int cdkind=0;
    time_t login_time;
    time_t queue_time;

    ip.S_un.S_addr = 0;
    login_time = 0;

    m_lock.Enter();
    UserMap::iterator it = usermap.find(uid);
    if ( it != usermap.end())
    {
        oldSocket = it->second.s;
        usermode  = it->second.um_mode;
        serverid  = it->second.serverid;
        gender    = it->second.gender;
        ssn       = it->second.ssn;
        ssn2      = it->second.ssn2;
        stat      = it->second.stat;
        ip        = it->second.loginIp;
        login_time= it->second.logintime;
        queue_time = it->second.queuetime;
        age          = it->second.age;
        cdkind    = it->second.cdkind;
        warn_flag = it->second.warnflag;
        strncpy( account, it->second.account, MAX_ACCOUNT_LEN+1 );
        usermap.erase(it);
        m_lock.Leave();
        result = true;
        account[MAX_ACCOUNT_LEN]=0;
    } else
        m_lock.Leave();
    
    if ( result == true ) {
        if ( config.UseWantedSystem ){
            if ( (warn_flag & 4) == 4 )
                SendWantedServerLogout( account, uid, serverid );
        }
        StdAccount( account );
        if ((strlen(account)>= 2) && (gender < 7))
            WriteLogD( LOG_ACCOUNT_LOGOUT2, account, ip, stat, age, gender, 0, 0, uid );

        if ( (usermode == UM_IN_GAME) || ( usermode == UM_PLAY_OK )) {
            if ( usermode == UM_IN_GAME ) {
                if ( serverid.IsValid() )
                    RecordLogout( reasoncode, uid, login_time, queue_time, serverid, ip, config.gameId, account, stat, ssn, ssn2, gender, age, cdkind );
            } 
            
            AS_LOG_VERBOSE( "SND: SQ_KICK_ACCOUNT,%d,uid:%d, account:%s", reasoncode, uid, account );

            if ( !g_ServerList.IsServerUp(serverid) )
            {
    #ifdef _DEBUG
                logger.AddLog( LOG_ERROR, "Invalid Serverid :%d, %s", serverid, account );
    #endif
                if ( (stat < 1000) && ( stat > 0)){
                    int sessionid = ipsessionDB.DelSessionID( uid );
                    if ( (sessionid > 0) && config.UseIPServer )
                        ipsessionDB.ReleaseSessionRequest( sessionid, ip, stat );
                }    

                return result;
            }
            else
                SendSocket( g_ServerList.GetInternalAddress(serverid), "cdcs", SQ_KICK_ACCOUNT, uid ,reasoncode, account ); // It is required
        
            if ( (stat < 1000) && ( stat > 0)){
                int sessionid = ipsessionDB.DelSessionID( uid );
                if ( (sessionid > 0) && config.UseIPServer )
                    ipsessionDB.ReleaseSessionRequest( sessionid, ip, stat );
            }    

            return result;
        }

        if ( (stat < 1000) && ( stat > 0)){
            int sessionid = ipsessionDB.DelSessionID( uid );
            if ( (sessionid > 0) && config.UseIPServer )
                ipsessionDB.ReleaseSessionRequest( sessionid, ip, stat );
        }    

        if ( oldSocket != INVALID_SOCKET && sendmsg ){
            SendSocketEx( oldSocket, "cc", AC_ACCOUNT_KICKED, reasoncode);
            AS_LOG_VERBOSE( "SND: AC_ACCOUNT_KICKED,%d,uid:%d,%x", reasoncode, uid, oldSocket );
        }
    }

    return result;
}

VOID CALLBACK TimerRoutine(PVOID lpParam, unsigned char TimerOrWaitFired)
{
_BEFORE
    int uid = PtrToInt( lpParam );
    accountdb.TimerCallback( uid );
_AFTER_FIN
    return;
}

void AccountDB::TimerCallback( int uid )
{
    HANDLE timer=NULL;
    UserMode um;
    bool result = false;
    ServerId serverid;
    ServerId preserverid;
    int stat=0;
    BYTE reasoncode = 0;
    char account[MAX_ACCOUNT_LEN+1];
    in_addr ip;
    UINT warn_flag=0;
_BEFORE
    m_lock.Enter();
    UserMap::iterator it = usermap.find(uid);
    if ( it != usermap.end())
    {
        um = it->second.um_mode;
        serverid = it->second.serverid;
        preserverid = it->second.selectedServerid;
        strncpy( account, it->second.account, MAX_ACCOUNT_LEN+1 );
        warn_flag = it->second.warnflag;
        if ( um != UM_IN_GAME ){
            stat = it->second.stat;
            ip.S_un.S_addr = it->second.loginIp.S_un.S_addr;
            usermap.erase(it);
            result = true;
        }
        else{
            it->second.timerHandle = NULL;
        }
    }
    m_lock.Leave();

    account[MAX_ACCOUNT_LEN] = 0;
    if (result){ 
        if ( config.UseWantedSystem ){
            if ( ( warn_flag & 4 ) == 4 )    
                SendWantedServerLogout( account, uid, serverid );
        }
        AS_LOG_DEBUG( "timer expire account erase %d", uid );
        if ( (stat < 1000) && ( stat > 0)) {
            int sessionid = ipsessionDB.DelSessionID( uid );
            if ( sessionid ){
                ipsessionDB.ReleaseSessionRequest( sessionid,  ip, stat );
            }
        }
    }

    if ( result && (um == UM_PLAY_OK) ) {
        if ( g_ServerList.IsServerUp(preserverid))
        {
            SendSocket( g_ServerList.GetInternalAddress(preserverid), "cdcs", SQ_KICK_ACCOUNT, uid ,reasoncode, account );
        }
        if ( !g_ServerList.IsServerUp(preserverid))
        {
#ifdef _DEBUG
            logger.AddLog( LOG_ERROR, "Invalid Serverid :%d, %s", serverid, account );
#endif 
        } else {
            SendSocket( g_ServerList.GetInternalAddress(serverid), "cdcs", SQ_KICK_ACCOUNT, uid ,reasoncode, account );
        }
    }
AFTER_FIN
    
    return;
}

void AccountDB::RemoveAll(ServerId s )
{
    int sessionid=0;
_BEFORE
    m_lock.Enter();
    for (UserMap::iterator it = usermap.begin(); it != usermap.end(); ) {
        if ( (it->second.serverid == s) || ( it->second.selectedServerid == s)) {
            if ( it->second.stat < 1000 ){
                sessionid = ipsessionDB.DelSessionID( it->first );
                if ( sessionid ) {
                    ipsessionDB.ReleaseSessionRequest( sessionid, (it->second.loginIp), it->second.stat );
                }
            }
            it = usermap.erase(it);
            InterlockedDecrement( &reporter.m_InGameUser );                
        }else
            it++;
    }
    m_lock.Leave();
_AFTER_FIN
}

SOCKET AccountDB::FindSocket( int uid, bool SetTimer )
{
    SOCKET s=NULL;
    HANDLE hTimer=NULL, tTimer=NULL;

    if (SetTimer)
        CreateTimerQueueTimer( &hTimer, NULL, TimerRoutine, (void *)(INT_PTR)uid, 300000, 0, 0 );

    m_lock.Enter();
    UserMap::iterator it = usermap.find(uid);
    if ( it != usermap.end()) {
        s = it->second.s;
        tTimer = it->second.timerHandle;
        it->second.timerHandle = hTimer;
    }
    m_lock.Leave();

    if ( tTimer != NULL ){
        DeleteTimerQueueTimer( NULL, tTimer, NULL );
    }
    
    return s;
}

SOCKET AccountDB::FindSocket( int uid, ServerId serverid, bool SetTimer, ServerId *preserverid, char *account )
{
    SOCKET s=NULL;
_BEFORE
    HANDLE hTimer=NULL, tTimer=NULL;

    if (SetTimer){
        CreateTimerQueueTimer( &hTimer, NULL, TimerRoutine, (void *)(INT_PTR)uid, 300000, 0, 0 );
    }
    
    preserverid->SetInvalid();
    m_lock.Enter();
    UserMap::iterator it = usermap.find(uid);
    if ( it != usermap.end()) {
        s = it->second.s;
        tTimer = it->second.timerHandle;
        it->second.timerHandle = hTimer;

        if ( serverid != it->second.selectedServerid ) {
            *preserverid = it->second.selectedServerid;
            strncpy( account, it->second.account, MAX_ACCOUNT_LEN);
        } else {
            it->second.serverid = serverid;
            it->second.um_mode = UM_PLAY_OK;
            strncpy( account, it->second.account, MAX_ACCOUNT_LEN);
        }
        it->second.selectedServerid.SetInvalid();
    }
    m_lock.Leave();

    if ( tTimer != NULL ){
        DeleteTimerQueueTimer( NULL, tTimer, NULL );
    }
_AFTER_FIN
    return s;
}

bool AccountDB::removeAccount( int uid, char *account )
{
    bool result=false;
    ServerId serverid;
    int stat=0;
    in_addr ip;
    UINT warn_flag = 0;
    m_lock.Enter();
    UserMap::iterator it = usermap.find(uid);
    if ( it != usermap.end()) {
        strncpy( account, it->second.account, 15 );
        warn_flag = it->second.warnflag;
        stat = it->second.stat;
        ip   = it->second.loginIp;
        usermap.erase(it);
        result = true;
    }
    m_lock.Leave();
    account[MAX_ACCOUNT_LEN]=0;
    if ( result ){
        if ( config.UseWantedSystem ) {
            if ( (warn_flag & 4) == 4 )
                SendWantedServerLogout( account, uid, serverid );
        }
        if (stat<1000) {
            int sessionid = ipsessionDB.DelSessionID( uid );
            if ( sessionid )
                ipsessionDB.ReleaseSessionRequest( sessionid,  ip, stat );
        }
    }
    return result;
}

bool AccountDB::removeAccountPreLogIn( int uid, SOCKET s )
{
_BEFORE
    bool result=false;
    int stat=0;
    in_addr ip;
    int age=0;
    int gender=0;
    ServerId serverid;
    UINT warn_flag = 0;
    char account[15];
    m_lock.Enter();
    UserMap::iterator it = usermap.find(uid);
    if ( it != usermap.end())
    {
        if ( it->second.um_mode != UM_PLAY_OK  && it->second.s == s){
            stat = it->second.stat;
            ip   = it->second.loginIp;
            strcpy( account, it->second.account);
            age = it->second.age;
            gender = it->second.gender;
            serverid = it->second.serverid;
            warn_flag = it->second.warnflag;
            usermap.erase(it);
            result = true;
        }
    }
    m_lock.Leave();
    account[14]=0;
    if ((stat<1000) && result ){
        int sessionid = ipsessionDB.DelSessionID( uid );
        if ( sessionid ){
            ipsessionDB.ReleaseSessionRequest( sessionid,  ip, stat );
        }
    }

    if ( result == true ){
        if ( config.UseWantedSystem ){
            if (( warn_flag & 4 ) == 4)
                SendWantedServerLogout( account, uid, serverid );
        }
        if ((strlen(account)>= 2) && (gender < 7))
            WriteLogD( LOG_ACCOUNT_LOGOUT2, account, ip, stat, age, gender, 0, 0, uid ); 
    }

_AFTER_FIN
    return true;
}

bool AccountDB::logoutAccount( int uid, int md5key )
{
    bool result=false;
_BEFORE
    char account[MAX_ACCOUNT_LEN+1];
    in_addr ip;
    char gender;
    int     stat=0;
    int  ssn = 0;
    int  age = 0;
    ServerId serverid;
    UINT warn_flag = 0;
    m_lock.Enter();
    UserMap::iterator it = usermap.find(uid);
    if ( it != usermap.end()){
        if ( it->second.md5key == md5key ){
            if ( it->second.um_mode == UM_IN_GAME ){
                m_lock.Leave();
                result = accountdb.quitGamePlay( uid, 0, ServerId::s_invalid );
                if ( result ) {
                    result = accountdb.logoutAccount(uid);
                }
                return result;
            }

            strncpy( account, it->second.account, MAX_ACCOUNT_LEN+1 );
            ip = it->second.loginIp;
            stat = it->second.stat;
            gender = it->second.gender;
            ssn = it->second.ssn;
            age = it->second.age;
            serverid = it->second.serverid;
            warn_flag = it->second.warnflag;
            usermap.erase(it);
            result = true;
        }
    }
    m_lock.Leave();
    account[MAX_ACCOUNT_LEN] = 0;
    if ( result ) {
        if ( config.UseWantedSystem ){
            if ( (warn_flag & 4 ) == 4 )
                SendWantedServerLogout( account, uid, serverid );
        }
        if ( (stat < 1000) && ( stat > 0)){
            int sessionid = ipsessionDB.DelSessionID( uid );
            if( sessionid ){
                ipsessionDB.ReleaseSessionRequest( sessionid, ip, stat );
            }
        }
        if ((strlen(account)>= 2) && (gender < 7))
            WriteLogD( LOG_ACCOUNT_LOGOUT2, account, ip, stat, age, gender, 0, 0, uid ); 
    }
_AFTER_FIN    
    return result;
}

bool AccountDB::logoutAccount( int uid )
{
    bool result=false;

    char account[MAX_ACCOUNT_LEN+1];
    in_addr ip;
    char gender=0;
    int stat=0;
    int ssn=0;
    int age=0;
    ServerId serverid;
    UINT warn_flag = 0;
    m_lock.Enter();
    UserMap::iterator it = usermap.find(uid);
    if ( it != usermap.end()){
        strncpy( account, it->second.account, MAX_ACCOUNT_LEN+1 );
        ip = it->second.loginIp;
        gender = it->second.gender;
        stat = it->second.stat;
        ssn  = it->second.ssn;
        age  = it->second.age;
        serverid = it->second.serverid;
        usermap.erase(it);
        m_lock.Leave();
        result = true;
    }else
        m_lock.Leave();
    account[MAX_ACCOUNT_LEN] = 0;
    if ( result ){
        if ( config.UseWantedSystem ){
            if (( warn_flag & 4 ) == 4 )
                SendWantedServerLogout( account, uid, serverid );
        }
        if ( (stat < 1000) && ( stat > 0)){
            int sessionid = ipsessionDB.DelSessionID( uid );
            if ( sessionid )
                ipsessionDB.ReleaseSessionRequest(sessionid, ip, stat);
        }
        if ((strlen(account)>= 2) && (gender < 7))
            WriteLogD( LOG_ACCOUNT_LOGOUT2, account, ip, stat, age, gender, 0, 0, uid );
    }

    return result;
}

bool AccountDB::recordGamePlayTime( int uid , ServerId serverid)
{
    bool result = false;
_BEFORE
    HANDLE mTimer=NULL;
    char account[MAX_ACCOUNT_LEN+1];
    memset( account, 0, MAX_ACCOUNT_LEN+1 );
    char gender=0;
    in_addr loginip;
    int ssn=0;
    int stat=0;
    int age=0;
    UINT warn_flag=0;
    m_lock.Enter();
    UserMap::iterator it = usermap.find(uid);
    if ( it != usermap.end()){
        it->second.logintime = time(0);
        it->second.serverid = serverid;
        it->second.um_mode = UM_IN_GAME;        
        mTimer = it->second.timerHandle;
        it->second.timerHandle = NULL;
        it->second.selectedServerid.SetInvalid();
        strncpy(account, it->second.account,MAX_ACCOUNT_LEN+1);
        loginip = it->second.loginIp;
        gender = it->second.gender;
        stat = it->second.stat;
        ssn =  it->second.ssn;
        age =  it->second.age;
        warn_flag = it->second.warnflag;
        result = true;
    }
    m_lock.Leave();

    if ( (stat < 1000) && ( stat > 0) && result ){
        ipsessionDB.ConfirmIPCharge( uid, loginip.S_un.S_addr, stat, serverid );
    }

    if ( mTimer != NULL)
        DeleteTimerQueueTimer( NULL, mTimer, NULL );

    if ( result ){
        InterlockedIncrement( &reporter.m_InGameUser );
        WriteLogD( LOG_ACCOUNT_LOGIN, account, loginip, stat, age, gender, 0, reporter.m_InGameUser, uid );
    }

    if ( pWantedSocket != NULL && config.UseWantedSystem && ( (warn_flag & 4) == 4 ) && result) {

        char sndmsg[28];
        memset(sndmsg,0, 28);
        if ( config.gameId == 8 )
            sndmsg[0]=2;
        memcpy( sndmsg+1, &uid, 4 );
        strncpy( sndmsg+5, account, 14 );
        sndmsg[19]=serverid.GetValueChar();
        time_t stime = time(NULL);
        memcpy( sndmsg+20, &stime, 4 );
        memcpy( sndmsg+24, &loginip, 4 );
        if ( config.UseWantedSystem && (!WantedServerReconnect) ){
            gWantedLock.ReadLock();
            pWantedSocket->AddRef();
            pWantedSocket->Send( "cb", AW_START, 28, sndmsg );
            pWantedSocket->ReleaseRef();
            gWantedLock.ReadUnlock();
        }
    }

_AFTER_FIN
    return result;
}

bool AccountDB::quitGamePlay( int uid, int usetime, ServerId serverID)
{
    bool result = false;
_BEFORE
    LoginUser lu;

    UserMap::iterator it;

    HANDLE hTimer=NULL;

    if ( config.OneTimeLogOut != true )
        CreateTimerQueueTimer( &hTimer, NULL, TimerRoutine, (void *)(INT_PTR)uid, config.SocketTimeOut, 0, 0 );

    m_lock.Enter();
    it = usermap.find(uid);
    if ( it != usermap.end()){
        if ( it->second.serverid == serverID || !serverID.IsValid()) {
            lu = it->second;
            it->second.um_mode = UM_LOGIN;    
            it->second.lastworld = it->second.serverid;
            it->second.serverid.SetInvalid();
            it->second.timerHandle = hTimer;
            result = true;
        } 
        m_lock.Leave();
    }else
        m_lock.Leave();
    
    if ( result )
    {
        lu.account[MAX_ACCOUNT_LEN] = '\0';
        if ( ( lu.warnflag & 4 ) == 4 )
            SendWantedServerLogout( lu.account, uid, lu.serverid );
        if ( lu.serverid.IsValid() )
        {
            AS_LOG_DEBUG( "quitgame, account:%s, ip:%d.%d.%d.%d, uid:%d", lu.account, lu.loginIp.S_un.S_un_b.s_b1,lu.loginIp.S_un.S_un_b.s_b2,lu.loginIp.S_un.S_un_b.s_b3,lu.loginIp.S_un.S_un_b.s_b4, uid );
            RecordLogout( 'L', uid, lu.logintime, lu.queuetime, lu.serverid, lu.loginIp, config.gameId, lu.account, lu.stat, lu.ssn, lu.ssn2, lu.gender, lu.age, lu.cdkind );
        }
    }
_AFTER_FIN
    return result;    
}

void AccountDB::transferPlayer(int uid, unsigned char shard)
{
    ServerId serverid(shard);
    m_lock.Enter();
    UserMap::iterator it = usermap.find(uid);
    if (it != usermap.end())
    {
        it->second.selectedServerid = serverid;
    }
    else
    {
        // error.  WTF do we do?
    }
    m_lock.Leave();
}

int AccountDB::checkInGame( int uid, int md5key )
{
_BEFORE
    m_lock.Enter();
    UserMap::iterator it = usermap.find(uid);
    if ( it != usermap.end()){
        if( it->second.um_mode == UM_IN_GAME ){
                m_lock.Leave();
                return S_ALREADY_LOGIN;
        }
        if ( it->second.md5key != md5key ){
            m_lock.Leave();
            return S_INCORRECT_MD5Key;
        }
    } else {
        m_lock.Leave();
        return S_NO_LOGININFO;
    }
    m_lock.Leave();
_AFTER_FIN
    return S_ALL_OK;
}

bool AccountDB::RecordLogout( char reasoncode, int uid, time_t loginTime, time_t enteredQueueTime, ServerId lastWorldId, in_addr LastIP, int LastGame, const char *account, int stat, int ssn1, int ssn2, char gender, int age, int cdkind )
{
    time_t logout_time;
    
    struct tm logoutTM;
    struct tm loginTM;
    struct tm queueloginTM;
    char szIP[16];
    unsigned long lastWorld = lastWorldId.GetValueChar();

    sprintf( szIP, "%d.%d.%d.%d", LastIP.S_un.S_un_b.s_b1,
                                  LastIP.S_un.S_un_b.s_b2,
                                  LastIP.S_un.S_un_b.s_b3,
                                  LastIP.S_un.S_un_b.s_b4);
    
    TIMESTAMP_STRUCT dblogout, 
                     dblogin,
                     dbqueuelogin;


    logout_time = time(0);
    
    int usetime = (int)(logout_time - loginTime);
    
    WriteLogD( LOG_ACCOUNT_LOGOUT, (char *)account, LastIP, stat, age, gender, 0, usetime, uid );  
    

    logoutTM = *localtime(&logout_time);
    loginTM  = *localtime(&loginTime);
    queueloginTM = *localtime(&enteredQueueTime);
    
    dblogout.year     = logoutTM.tm_year + 1900;
    dblogout.month    = logoutTM.tm_mon + 1;
    dblogout.day      = logoutTM.tm_mday;
    dblogout.hour     = logoutTM.tm_hour;
    dblogout.minute   = logoutTM.tm_min;
    dblogout.second   = logoutTM.tm_sec;
    dblogout.fraction = 0;

    dblogin.year     = loginTM.tm_year + 1900;
    dblogin.month    = loginTM.tm_mon + 1;
    dblogin.day      = loginTM.tm_mday;
    dblogin.hour     = loginTM.tm_hour;
    dblogin.minute   = loginTM.tm_min;
    dblogin.second   = loginTM.tm_sec;
    dblogin.fraction = 0;

    dbqueuelogin.year     = queueloginTM.tm_year + 1900;
    dbqueuelogin.month    = queueloginTM.tm_mon + 1;
    dbqueuelogin.day      = queueloginTM.tm_mday;
    dbqueuelogin.hour     = queueloginTM.tm_hour;
    dbqueuelogin.minute   = queueloginTM.tm_min;
    dbqueuelogin.second   = queueloginTM.tm_sec;
    dbqueuelogin.fraction = 0;

    {
        CDBConn conn(g_linDB);

        SQLLEN cbUid=0;
        SQLBindParameter( conn.m_stmt, 1, SQL_PARAM_INPUT, SQL_C_ULONG, SQL_INTEGER, 0, 0, (SQLPOINTER)(&uid), 0, &cbUid );
        
        SQLLEN cblastlogin=0;
        SQLBindParameter( conn.m_stmt, 2, SQL_PARAM_INPUT, SQL_C_TYPE_TIMESTAMP,SQL_TIMESTAMP, 19, 0, (SQLPOINTER)&dblogin, 0, &cblastlogin );
        
        SQLLEN cblastlogout=0;
        SQLBindParameter( conn.m_stmt, 3, SQL_PARAM_INPUT, SQL_C_TYPE_TIMESTAMP,SQL_TIMESTAMP, 19, 0, (SQLPOINTER)&dblogout, 0, &cblastlogout );
        
        SQLLEN cblastgame=0;
        SQLBindParameter( conn.m_stmt, 4, SQL_PARAM_INPUT, SQL_C_ULONG, SQL_INTEGER, 0, 0, (SQLPOINTER)(&LastGame), 0, &cblastgame );

        SQLLEN cblastworld=0;
        SQLBindParameter( conn.m_stmt, 5, SQL_PARAM_INPUT, SQL_C_UTINYINT, SQL_TINYINT, 0, 0, (SQLPOINTER)(&lastWorldId), 0, &cblastworld );

        SQLLEN cblastIP=SQL_NTS;
        SQLBindParameter( conn.m_stmt, 6, SQL_PARAM_INPUT, SQL_C_TCHAR, SQL_VARCHAR, 15, 0, (SQLPOINTER)szIP, (SQLINTEGER)strlen(szIP), &cblastIP );

        char buffer[256];
        sprintf( buffer, "{CALL dbo.ap_SLog (?,?,?,?,?,?) }" );
        RETCODE RetCode= SQLExecDirectA( conn.m_stmt, (SQLCHAR*)buffer, SQL_NTS );
        
        if ( RetCode == SQL_SUCCESS ) {
            conn.ResetHtmt();
        } else {
            conn.Error(SQL_HANDLE_STMT, conn.m_stmt, buffer);
            conn.ResetHtmt();
        }

    }

    { //NEW for NCAustin version of auth server, this allows us to have a login/logout history
      //instead of just the last login/logout record which is also the system does normally

        CDBConn conn(g_linDB);

        //Add logout entry to the activity log
        SQLLEN accountName_strLen=SQL_NTS;
        SQLBindParameter( conn.m_stmt, 1, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_CHAR, 14, 0, (SQLPOINTER)account, 14, &accountName_strLen);

        SQLLEN userIdLen = 4;
        SQLBindParameter( conn.m_stmt, 2, SQL_PARAM_INPUT, SQL_C_ULONG, SQL_INTEGER, 0, 0, (SQLPOINTER)(&uid), 0, &userIdLen);

 
        SQLLEN serverIdLen = 4;
        SQLBindParameter( conn.m_stmt, 3, SQL_PARAM_INPUT, SQL_C_ULONG, SQL_INTEGER, 0, 0, (SQLPOINTER)&lastWorld, 0, &serverIdLen);


        SQLLEN clientIPLen=SQL_NTS;
        SQLBindParameter( conn.m_stmt, 4, SQL_PARAM_INPUT, SQL_C_TCHAR, SQL_VARCHAR, 15, 0, (SQLPOINTER)szIP, (SQLINTEGER)strlen(szIP), &clientIPLen );


        SQLLEN lastLoginLen=0;
        SQLBindParameter( conn.m_stmt, 5, SQL_PARAM_INPUT, SQL_C_TYPE_TIMESTAMP,SQL_TIMESTAMP, 19, 0, (SQLPOINTER)&dblogin, 0, &lastLoginLen );

        SQLLEN queueLoginLen=0;
        SQLBindParameter( conn.m_stmt, 6, SQL_PARAM_INPUT, SQL_C_TYPE_TIMESTAMP,SQL_TIMESTAMP, 19, 0, (SQLPOINTER)&dbqueuelogin, 0, &queueLoginLen );
    
        //Current system doesnt keep track of different auth logins and game logins, it just overwrites
        //the same login value on the user account
        SQLLEN gameLoginLen=0;
        SQLBindParameter( conn.m_stmt, 7, SQL_PARAM_INPUT, SQL_C_TYPE_TIMESTAMP,SQL_TIMESTAMP, 19, 0, (SQLPOINTER)&dblogin, 0, &gameLoginLen );
    

        SQLLEN lastLogoutLen=0;
        SQLBindParameter( conn.m_stmt, 8, SQL_PARAM_INPUT, SQL_C_TYPE_TIMESTAMP,SQL_TIMESTAMP, 19, 0, (SQLPOINTER)&dblogout, 0, &lastLogoutLen );
    
        SQLLEN logoutTypeLen=0;
        SQLBindParameter( conn.m_stmt, 9, SQL_PARAM_INPUT, SQL_C_CHAR,SQL_CHAR, 1, 0, (SQLPOINTER)&reasoncode, 1, &logoutTypeLen );

        SQLLEN cdKindLen=0;
        SQLBindParameter( conn.m_stmt, 10, SQL_PARAM_INPUT, SQL_C_ULONG, SQL_INTEGER, 0, 0, (SQLPOINTER)&cdkind, 1, &cdKindLen );

        char buffer[256];
        sprintf( buffer, "{CALL dbo.sp_LogAuthActivity (?,?,?,?,?,?,?,?,?,?) }" );
        RETCODE RetCode= SQLExecDirectA( conn.m_stmt, (SQLCHAR*)buffer, SQL_NTS );
        
        if ( RetCode == SQL_SUCCESS ) {
            conn.ResetHtmt();
        } else {
            conn.Error(SQL_HANDLE_STMT, conn.m_stmt, buffer);
            conn.ResetHtmt();
        }
        
    }

    filelog.AddLog( LOG_NORMAL, "%d-%d-%d %d:%d:%d,%d-%d-%d %d:%d:%d,%s,%d,%s,%d,%d,%d,%06d%07d,%d,%d,%d,%d\r\n", 
                logoutTM.tm_year + 1900, logoutTM.tm_mon + 1, logoutTM.tm_mday,
                logoutTM.tm_hour, logoutTM.tm_min, logoutTM.tm_sec,
                loginTM.tm_year + 1900, loginTM.tm_mon + 1, loginTM.tm_mday,
                loginTM.tm_hour, loginTM.tm_min, loginTM.tm_sec,
                account,
                lastWorld,
                szIP, 
                stat,
                usetime,
                usetime,
                ssn1, ssn2,
                gender, logoutTM.tm_wday, age, cdkind);
    
    int OperationCode = (int)(( stat % 1000 ) / 100 );

    if ( (stat < 1000) && ( stat > 0)){
        ipsessionDB.StopIPCharge( uid, LastIP.S_un.S_addr, stat, usetime, loginTime, lastWorldId, account );
    
    } else if ( OperationCode == PERSONAL_SPECIFIC ) {

        CDBConn conn(g_linDB);
        SQLLEN cUseTime=0;
        SQLBindParameter( conn.m_stmt, 1, SQL_PARAM_INPUT, SQL_C_ULONG, SQL_INTEGER, 0, 0, (SQLPOINTER)(&usetime), 0, &cUseTime );
        SQLLEN cbUid=0;
        SQLBindParameter( conn.m_stmt, 2, SQL_PARAM_INPUT, SQL_C_ULONG, SQL_INTEGER, 0, 0, (SQLPOINTER)(&uid), 0, &cbUid );

        char buffer[256];
        sprintf( buffer, "{CALL dbo.ap_SUserTime (?,?) }" );
        RETCODE RetCode= SQLExecDirectA( conn.m_stmt, (SQLCHAR*)buffer, SQL_NTS );
        if ( RetCode == SQL_SUCCESS ) {
            conn.ResetHtmt();
        } else {
            conn.Error(SQL_HANDLE_STMT, conn.m_stmt, buffer);
            conn.ResetHtmt();
        }

    } else if ( OperationCode == PERSONAL_POINT ) {
        CDBConn conn(g_linDB);
        SQLLEN cbAccount=0;
        SQLINTEGER cbTime=0;
        char buffer[256];
        SQLBindParameter( conn.m_stmt, 1, SQL_PARAM_INPUT, SQL_C_TCHAR, SQL_VARCHAR, MAX_ACCOUNT_LEN, 0, (SQLPOINTER)account, (SQLINTEGER)strlen(account), &cbAccount );
        SQLLEN cblastlogin=0;
        SQLBindParameter( conn.m_stmt, 2, SQL_PARAM_INPUT, SQL_C_TYPE_TIMESTAMP,SQL_TIMESTAMP, 19, 0, (SQLPOINTER)&dblogin, 0, &cblastlogin );
        SQLLEN cblastlogout=0;
        SQLBindParameter( conn.m_stmt, 3, SQL_PARAM_INPUT, SQL_C_TYPE_TIMESTAMP,SQL_TIMESTAMP, 19, 0, (SQLPOINTER)&dblogout, 0, &cblastlogout );

        sprintf( buffer, "{CALL dbo.ap_LogoutWithPoint( ?,?,? )}" );
        RETCODE RetCode = SQLExecDirectA( conn.m_stmt, (SQLCHAR*)buffer, SQL_NTS);
        if ( RetCode == SQL_SUCCESS ){
            conn.ResetHtmt();
        } else {
            conn.Error( SQL_HANDLE_STMT, conn.m_stmt, buffer );
            conn.ResetHtmt();
        }
    }

    InterlockedDecrement( &reporter.m_InGameUser );    

    return true;
}

char AccountDB::UserTimeLogin( int uid, LoginUser *lu, int *RemainTime )
{
    char ErrorCode=S_ALL_OK;

    ErrorCode = accountdb.CheckUserTime( uid, RemainTime );

    if ( ErrorCode == S_ALL_OK ) {
    } else {
        ErrorCode = S_NO_SPECIFICTIME;
    }
    return ErrorCode;
}

char AccountDB::CheckPersonalPayStat(CSocketServerEx *pSocket, LoginUser *lu, int Uid)
{
    char result=S_ALL_OK;

    int OperationCode = (int)(( lu->stat% 1000 ) / 100 );
    int RemainTime=0;

    if ( lu->stat == 0 ) {
        result = S_NOT_PAID;
    } else if ( OperationCode == PERSONAL_SPECIFIC ) {
        result=UserTimeLogin( Uid, lu, &RemainTime );
    } else if ( OperationCode == PERSONAL_POINT ) {
        CDBConn dbconn(g_linDB);
        
    }

    if ( result != S_ALL_OK ) {
        pSocket->Send( "cc", AC_LOGIN_FAIL, result );
        return result;
    }
    
    if ( accountdb.RegAccount( lu, Uid, pSocket, RemainTime, 0 ) ){

        logger.AddLog( LOG_VERBOSE, "SND: AC_LOGIN_OK,uid:%d,account:%s", Uid, lu->account);

        pSocket->m_lastIO = GetTickCount();
//        WriteAction( "login", lu->account, lu->loginIp, lu->ssn, lu->gender, 0, lu->stat );
        WriteLogD( LOG_ACCOUNT_AUTHED, lu->account, lu->loginIp, lu->stat, lu->age, lu->gender, 0, reporter.m_UserCount, Uid );
    } else{
        
        logger.AddLog( LOG_WARN, "SND: AC_LOGIN_FAIL,uid:%d,account:%s,ip:%d.%d.%d.%d,%x", Uid, lu->account, lu->loginIp.S_un.S_un_b.s_b1, lu->loginIp.S_un.S_un_b.s_b2, lu->loginIp.S_un.S_un_b.s_b3, lu->loginIp.S_un.S_un_b.s_b4, pSocket->GetSocket() );
    }

    return result;
}

char AccountDB::CheckUserTime(int Uid, int *RemainTime)
{
    char ErrorCode=S_ALL_OK;

    CDBConn conn(g_linDB);
    
    SQLLEN cbUid=0;
    SQLBindParameter( conn.m_stmt, 1, SQL_PARAM_INPUT, SQL_C_ULONG, SQL_INTEGER, 0, 0, (SQLPOINTER)(&Uid), 0, &cbUid );
    
    SQLLEN cbUserTime=0;
    SQLBindParameter( conn.m_stmt, 2, SQL_PARAM_OUTPUT, SQL_C_ULONG, SQL_INTEGER, 0, 0, (SQLPOINTER)(RemainTime), 0, &cbUserTime );
    
    char buffer[256];
    sprintf( buffer, "{CALL dbo.ap_GUserTime (?,?) }" );
    RETCODE RetCode= SQLExecDirectA( conn.m_stmt, (SQLCHAR*)buffer, SQL_NTS );    
    
    bool nodata;
    if ( RetCode == SQL_SUCCESS ) {
        conn.Fetch(&nodata);
        if ( *RemainTime <= 0 ){
            ErrorCode = S_NO_SPECIFICTIME;
        }
    }else{
        ErrorCode = S_DATABASE_FAIL;
    }
    
    conn.ResetHtmt();

    return ErrorCode;
}

char AccountDB::AboutToPlay(int uid, char *account, int time_left, int loginflag, int warnflag, int md5key, CSocketServerEx *pSocket, ServerId serverid, int stat, int queueLevel, int loyalty, int loyaltyLegacy)
{
    char error = S_ALL_OK;

    int result=0;

    if (config.payStatOverride != -1)
    {
        stat = config.payStatOverride;
        logger.AddLog(LOG_WARN, "PayStatOverride is set to %d!", config.payStatOverride);
    }

    if ( config.UserData ){
        unsigned char userdata[MAX_USERDATA];
        
        memset( userdata, 0, MAX_USERDATA );

        // class CDBConn appears to have some global status that places severe limits on it's use.  In particular, it's best to blow the
        // first of these away before trying to instantiate the second.  Hence the enclosing of these two code blocks in braces, which
        // forces CDBConn::~CDBConn() to be called.
        {
        CDBConn dbconn(g_linDB);
        SQLLEN UserInd=0;
        SQLBindCol( dbconn.m_stmt, 1, SQL_C_BINARY, (char *)(userdata), MAX_USERDATA_ORIG, &UserInd );

        SQLLEN UserIndNew=0;
        SQLBindCol( dbconn.m_stmt, 2, SQL_C_BINARY, (char *)(&userdata[MAX_USERDATA_ORIG]), MAX_USERDATA_NEW, &UserIndNew );

        SQLLEN cbUid=0;
        SQLBindParameter( dbconn.m_stmt, 1, SQL_PARAM_INPUT, SQL_C_ULONG, SQL_INTEGER, 0, 0, (SQLPOINTER)(&uid), 0, &cbUid );

        dbconn.Execute( "SELECT user_data, user_data_new FROM user_data WHERE uid = ?" );
        dbconn.Fetch();
        }

        int len = MAX_USERDATA;

        if ( !g_ServerList.IsServerUp(serverid) )
        {
#ifdef _DEBUG
            logger.AddLog(LOG_ERROR, "Invalid Serverid :%d, %s", serverid, account );
#endif 
        } else {
            AS_LOG_VERBOSE( "User data from SQL for uid %d: %02x%02x%02x%02x-%02x%02x%02x%02x-%02x%02x%02x%02x-%02x%02x%02x%02x",
                uid,
                userdata[ 0], userdata[ 1], userdata[ 2], userdata[ 3],
                userdata[ 4], userdata[ 5], userdata[ 6], userdata[ 7],
                userdata[ 8], userdata[ 9], userdata[10], userdata[11],
                userdata[12], userdata[13], userdata[14], userdata[15]);
            char filler[32];
            _snprintf_s(filler, sizeof(filler), sizeof(filler) - 1, "%d", uid);
            int i;
            for (i = 0; filler[i]; i++)
            {
                filler[i] = ' ';
            }
            for (i = 16; i < MAX_USERDATA; i += 16)
            {
                AS_LOG_VERBOSE( "                           %s  %02x%02x%02x%02x-%02x%02x%02x%02x-%02x%02x%02x%02x-%02x%02x%02x%02x",
                    filler,
                userdata[i +  0], userdata[i +  1], userdata[i +  2], userdata[i +  3],
                userdata[i +  4], userdata[i +  5], userdata[i +  6], userdata[i +  7],
                userdata[i +  8], userdata[i +  9], userdata[i + 10], userdata[i + 11],
                userdata[i + 12], userdata[i + 13], userdata[i + 14], userdata[i + 15]);
            }
            if (config.useQueue || config.sendQueueLevel)
            {
                result = SendSocket( g_ServerList.GetInternalAddress(serverid),
                        "cdsdddbdc",
                        SQ_ABOUT_TO_PLAY, uid, account, time_left, loginflag, warnflag, len, userdata, stat, queueLevel );
            }
            else
            {
                result = SendSocket( g_ServerList.GetInternalAddress(serverid),
                    "cdsdddbddd",
                    SQ_ABOUT_TO_PLAY, uid, account, time_left, loginflag, warnflag, len, userdata, stat, loyalty, loyaltyLegacy );
            }
        }

    } else {
        if ( !g_ServerList.IsServerUp(serverid) )
        {
#ifdef _DEBUG
            logger.AddLog(LOG_ERROR, "Invalid Serverid :%d, %s", serverid, account );
#endif
        }else{
            result = SendSocket( g_ServerList.GetInternalAddress(serverid), "cdsdddd", SQ_ABOUT_TO_PLAY, uid, account, time_left, loginflag, warnflag, stat, queueLevel );
        }
    }

    if ( pSocket ) {
        if ( result == FALSE ){
            AS_LOG_VERBOSE( "SND: AC_PLAY_FAIL,server down", S_SERVER_DOWN );
            error = S_SERVER_DOWN;
            pSocket->Send( "cc", AC_PLAY_FAIL, error );        
        } else {

            AS_LOG_VERBOSE( "SND: SQ_ABOUT_TO_PLAY,account:%s", account );
        
            if( (error=UpdateSocket( uid, pSocket->GetSocket(), md5key, serverid )) != S_ALL_OK){
                AS_LOG_VERBOSE( "SND: AC_PLAY_FAIL,error:%d", error);
                pSocket->Send( "cc", AC_PLAY_FAIL, error );        
            }
        }
    }

    return error;
}

bool AccountDB::GetAccountInfo( int uid, char *account, int *loginflag, int *warnflag, int *md5key, SOCKET *s )
{
    bool result=false;

    HANDLE hTimer=NULL;

    m_lock.Enter();
    UserMap::iterator it = usermap.find(uid);
    if ( it != usermap.end()) {
        strncpy( account, it->second.account, MAX_ACCOUNT_LEN+1 );
        *loginflag = it->second.loginflag;
        *warnflag = it->second.warnflag;
        *s = it->second.s;
        *md5key = it->second.md5key;
        hTimer = it->second.timerHandle;
        it->second.timerHandle = NULL;
        result = true;
    }
    m_lock.Leave();
    
    if ( hTimer != NULL  )
        DeleteTimerQueueTimer( NULL, hTimer, NULL );

    return result;
}

bool AccountDB::GetAccountInfoForIPStop( int uid, char *account, int *stat, in_addr *loginip, time_t *loginTime )
{
    bool result = false;

    m_lock.Enter();
    UserMap::iterator it = usermap.find(uid);
    if ( it != usermap.end()){
        strncpy( account, it->second.account, MAX_ACCOUNT_LEN+1);
        *stat = it->second.stat;
        *loginip = it->second.loginIp;
        *loginTime = it->second.logintime;
        m_lock.Leave();
        result = true;
    } else
        m_lock.Leave();
    
    return result;
}

bool AccountDB::RegAccountByServer( LoginUser *loginuser, int uid, CSocketServer *s, int remainTime, int quotaTime )
{
    bool result = false;

    m_lock.Enter();
    std::pair<UserMap::iterator, bool> r = usermap.insert(UserMap::value_type(uid, *loginuser));
    result = r.second;
    m_lock.Leave();
    
    if ( result == false ){
        KickAccount( uid,S_ALREADY_LOGIN, true );
    }
    return result;
}    
