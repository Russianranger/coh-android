#ifndef _SERVER_MONITOR_ENTS_H
#define _SERVER_MONITOR_ENTS_H

#include <winsock2.h>
#include <windows.h>

typedef struct DbContainer DbContainer;
typedef struct ServerMonitorState ServerMonitorState;

void smentsShow(ServerMonitorState *state);
int smentsHook(PMSG pmsg);
void smentsSetFilterId(ServerMonitorState *state, int id);
int smentsFilter(DbContainer *dbcon, void *filterData);
int smentsVisible(ServerMonitorState *state);

#endif // _SERVER_MONITOR_ENTS_H
