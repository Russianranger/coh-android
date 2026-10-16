/* Test-only projection of original consumer state. Not a production ABI. */
#ifndef COH_BADGE_OBSERVATION_H
#define COH_BADGE_OBSERVATION_H
#include "coh_badges.h"
#include <string.h>
typedef struct {
    uint32_t debug_mode;
    uint32_t player[COH_BADGE_PLAYER_MAX],supergroup[COH_BADGE_SUPERGROUP_MAX];
    uint32_t player_filename[COH_BADGE_PLAYER_MAX],supergroup_filename[COH_BADGE_SUPERGROUP_MAX];
    CohBadgeRecent recent[COH_BADGE_RECENT_MAX];
    CohBadgeMonitor monitor;
} BadgeObservation;
static uint32_t badge_text_hash(const char *s) {
    if(!s)return 0;
    uint32_t result=2166136261u;
    do {result=(result^(unsigned char)*s)*16777619u;}while(*s++);
    return result;
}
static void badge_prior(BadgeObservation *s) {
    memset(s,0,sizeof(*s));s->debug_mode=99;
    for(unsigned i=0;i<COH_BADGE_PLAYER_MAX;i++) {
        s->player[i]=(i%3u)*0x20000000u+(i&0xfffffu);
        s->player_filename[i]=badge_text_hash("prior-player");
    }
    for(unsigned i=0;i<COH_BADGE_SUPERGROUP_MAX;i++) {
        s->supergroup[i]=(i%3u)*0x20000000u+(i&0xfffffu);
        s->supergroup_filename[i]=badge_text_hash("prior-supergroup");
    }
    for(unsigned i=0;i<COH_BADGE_RECENT_MAX;i++)s->recent[i]=(CohBadgeRecent){i+17,123456u+i};
    for(unsigned i=0;i<COH_BADGE_MONITOR_MAX;i++)s->monitor.indices[i]=i+100;
}
#endif
