#ifndef _SHARD_MONITOR_CMD_RELAY_H
#define _SHARD_MONITOR_CMD_RELAY_H

#include <winsock2.h>
#include <windows.h>

LRESULT CALLBACK DlgShardRelayProc (HWND hDlg, UINT iMsg, WPARAM wParam, LPARAM lParam);

void shardRelayInit();

#endif // _SHARD_MONITOR_CMD_RELAY_H
