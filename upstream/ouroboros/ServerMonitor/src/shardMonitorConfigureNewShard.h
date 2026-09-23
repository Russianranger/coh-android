#ifndef _SHARD_MONITOR_CONFIGURE_NEW_SHARD_H
#define _SHARD_MONITOR_CONFIGURE_NEW_SHARD_H

#include <utilitieslib/utils/wininclude.h>

// Returns 1 if they pressed OK, 0 if they pressed Cancel
int shardMonConfigureNewShard(HINSTANCE hinst, HWND hwnd, char *name, U32 *ip);

#endif // _SHARD_MONITOR_CONFIGURE_NEW_SHARD_H
