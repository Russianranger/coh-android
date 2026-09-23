#ifndef _SHARD_MONITOR_CONFIGURE_H
#define _SHARD_MONITOR_CONFIGURE_H

#include <utilitieslib/utils/wininclude.h>
#include <utilitieslib/utils/textparser.h>

void shardMonConfigure(HINSTANCE hinst, HWND hwndParent, char *configfile);

void shardMonLoadConfig(char *configfile);

typedef struct ShardMonitorConfigEntry {
    char name[128];
    U32 ip;
} ShardMonitorConfigEntry;

typedef struct ShardMonitorConfig {
    ShardMonitorConfigEntry **shardList;    
} ShardMonitorConfig;

extern TokenizerParseInfo shardMonitorConfigEntryDispInfo[];
extern TokenizerParseInfo shardMonitorConfigInfo[];

extern ShardMonitorConfig shmConfig;

#endif // _SHARD_MONITOR_CONFIGURE_H
