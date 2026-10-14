#ifndef COH_FOLDER_CENSUS_OBSERVATION_H
#define COH_FOLDER_CENSUS_OBSERVATION_H
/* Qualification-only aggregate observations. No cached stat or query bypass. */
#include <stdint.h>
#if defined(_WIN32)
#define COH_CENSUS_THREAD_LOCAL __declspec(thread)
#else
#define COH_CENSUS_THREAD_LOCAL _Thread_local
#endif

enum CohCensusStatStage {
    COH_CENSUS_STAT_CREATE = 1,
    COH_CENSUS_STAT_FILE_INFORMATION = 2
};

extern COH_CENSUS_THREAD_LOCAL int coh_client_census_stat_scope;
void cohClientCensusObserveStatStage(int stage, int succeeded);
#endif
