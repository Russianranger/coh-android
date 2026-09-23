#ifndef MONITOR_H__
#define MONITOR_H__

#include <utilitieslib/network/netio.h>


typedef struct
{
    NetLink    *link;

} MonitorLink;

extern NetLinkList monitor_links;

void chatMonitorInit();
void monitorTick();

#endif  // MONITOR_H__