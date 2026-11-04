#ifndef COH_WINE_EXTERNAL_MAPS_H
#define COH_WINE_EXTERNAL_MAPS_H

/* On-demand zone starts without a Launcher (ArmPort device supervisor).
 *
 * With no Launcher connected, launcherCommStartProcess finds no link and a
 * static zone's container is deleted (mapxfer.c), so it cannot be entered again
 * until the DbServer restarts; missions fail. In this mode every map start
 * (character select, zone doors and trains, instances, missions, -start) is
 * published as one JSON record in the supervisor's request directory instead.
 * The DbServer keeps the map "starting" and waits exactly as it does for a
 * Launcher: the supervisor starts MapServer.exe with the record's map id and
 * cookie, the map registers (cookie checked) and reports ready, and waiting
 * players continue. A start the supervisor cannot complete is delinked by it
 * (MapServer.exe -dbquery -delink <id>), which resets the container.
 */

#define COH_DB_EXTERNAL_MAPS_ENVIRONMENT "COH_WINE_DB_EXTERNAL_MAPS"
#define COH_DB_EXTERNAL_MAPS_DIRECTORY "COH_WINE_DB_EXTERNAL_MAPS_DIR"
#define COH_DB_EXTERNAL_MAPS_ACK "COH_WINE_DB_EXTERNAL_MAPS=1 active: map starts are published to the supervisor; no Launcher is used"
#define COH_DB_EXTERNAL_MAPS_REQUEST_MARKER "COH_WINE_DB_EXTERNAL_MAP_REQUEST_V1"
#define COH_DB_EXTERNAL_MAPS_FORMAT 1

/* 0: absent (ordinary Launcher behaviour). 1: exactly "1" with manual Atlas
 * mode on and an existing request directory shorter than 200 characters
 * (prints COH_DB_EXTERNAL_MAPS_ACK once). -1: set but malformed or unsafe;
 * callers must refuse to start maps rather than fall back silently. */
int cohDbExternalMapsMode(void);

/* Write map-<id>-<cookie>.json (through a .tmp file renamed into place).
 * Strings are JSON-escaped and bounded by their container fields. Returns 1
 * when the record is in place, 0 otherwise (GetLastError is set). */
int cohDbPublishMapRequest(int map_id, int cookie, int base_map_id, int is_static, int transient,
    int dont_auto_start, int preload_transient, const char *map_name, const char *mission_info,
    const char *command);

#endif
