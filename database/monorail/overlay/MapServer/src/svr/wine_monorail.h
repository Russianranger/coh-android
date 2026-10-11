#ifndef COH_WINE_MONORAIL_H
#define COH_WINE_MONORAIL_H
#include <windows.h>
#define COH_MONORAIL_SESSION_ENV "COH_WINE_MONORAIL_SESSION"
#define COH_MONORAIL_REPLY_ENV "COH_WINE_MONORAIL_REPLY"
int cohMonorailInit(void);
int cohMonorailEnabled(void);
int cohMonorailMapAllowed(int map_id);
void cohZoningEvent(const char *kind, int map_id, int db_id, DWORD auth_id,
    const char *name, const char *account, const char *peer, int port,
    float x, float y, float z);
int cohMonorailRequest(int map_id, int destination, int db_id, DWORD auth_id,
    const char *name, const char *account);
int cohMonorailPoll(int map_id, int db_id, DWORD auth_id);
void cohMonorailCancel(void);
void cohMonorailDoorTick(void);
#endif
