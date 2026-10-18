/* NONSHIPPING observation overlay. Original main/policy/cleanup remain exact. */
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include "db_received_prefix.h"
static int received_printf(const char *,...);
#define printf received_printf
#include "db_development_probe.c"
#undef printf

static int received_printf(const char *format,...) {
    /* The exact admitted original main has one fixed JSON printf. Never retain
     * or publish another format, a partial record, or arbitrary string input. */
    char fixed[8192]={0};va_list arguments;va_start(arguments,format);
    int extent=vsnprintf(fixed,sizeof(fixed),format,arguments);va_end(arguments);
    static const char list[]="{\"schema\":\"coh-auth-db-development-list-probe-v1\"";
    static const char platform[]="{\"schema\":\"coh-auth-db-development-platform-preflight-v1\"";
    size_t schema_length=0;
    if(extent>0&&(size_t)extent<sizeof(fixed)) {
        if(!strncmp(fixed,list,sizeof(list)-1))schema_length=sizeof(list)-1;
        else if(!strncmp(fixed,platform,sizeof(platform)-1))schema_length=sizeof(platform)-1;
    }
    if(!schema_length||extent<2||strcmp(fixed+extent-2,"}\n")) {
        coh_auth_wipe(fixed,sizeof(fixed));
        return puts("{\"schema\":\"coh-auth-db-development-observation-refused-v1\",\"passed\":false}");
    }
    fixed[schema_length-2]='2';fixed[extent-2]=0;
    CohDevDbReceivedPrefix prefix={0};
    int available=coh_dev_db_received_prefix(&prefix)==COH_OK;
    if(!available)memset(&prefix,0,sizeof(prefix));
    /* Only fixed enums/booleans/bounded counters. No copied body, command
     * number, account, UID, cookie, pointer, generation or arbitrary text. */
    int written=printf("%s,\"db_received_prefix\":{\"schema\":\"coh-db-received-header-prefix-v1\","
        "\"available\":%s,\"context_verified\":%s,\"retired\":%s,\"truncated\":%s,"
        "\"instances\":%u,\"service_calls\":%u,\"total_seen\":%u,"
        "\"first_unsupported_attributed\":false,\"body_acceptance_observed\":false,\"entries\":[",
        fixed,available?"true":"false",prefix.context_verified?"true":"false",prefix.retired?"true":"false",
        prefix.truncated?"true":"false",prefix.instances,prefix.service_calls,prefix.total_seen);
    for(uint32_t i=0;i<prefix.count&&i<COH_DEV_DB_PREFIX_MAX;i++) {
        const CohDevDbPrefixEntry *entry=&prefix.entries[i];
        written+=printf("%s{\"command\":\"%s\",\"header_decoded\":%s,\"phase\":%u,\"legacy\":%s,\"compressed\":%s}",
            i?",":"",coh_dev_db_command_name(entry->kind),entry->header_decoded?"true":"false",
            entry->phase,entry->legacy?"true":"false",entry->compressed?"true":"false");
    }
    written+=puts("]}}");
    coh_auth_wipe(&prefix,sizeof(prefix));coh_auth_wipe(fixed,sizeof(fixed));return written;
}
