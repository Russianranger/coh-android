/* Unchanged source functions; bounded typed staging and no-I/O shims. */
#ifdef COH_ORIGINAL_COMMAND_TYPES
#define COMM_MAX_CMD 2
#define COMMAND_CONTACT_INDEX_LINE 220
#define COMMAND_CONTACT_SIZE_LINE 180
#define COMMAND_TASK_INDEX_LINE 511
#define COMMAND_TASK_SIZE_LINE 475
typedef enum ServerCommCmd
{
    SERVER_UPDATE = COMM_MAX_CMD,
    SERVER_ALLENTS,
    SERVER_CMDSHORTCUTS,
    SERVER_CONNECT_MSG,
    SERVER_GROUPS,
    SERVER_DYNAMIC_DEFS,
    SERVER_EDITMSG,
    SERVER_DEBUGCMD,
    SERVER_SENDENTDEBUGMENU,
    SERVER_MAP_XFER_WAIT,
    SERVER_MAP_XFER_LOADING,
    SERVER_MAP_XFER,
    SERVER_FORCE_LOGOUT,
    SERVER_GAME_CMDS,

    SERVER_RECEIVE_DIALOG,
    SERVER_RECEIVE_DIALOG_POWREQ,
    SERVER_RECEIVE_DIALOG_TEAMLEVEL,
    SERVER_RECEIVE_DIALOG_NAG,
    SERVER_RECEIVE_DIALOG_IGNORABLE,
    SERVER_RECEIVE_DIALOG_WIDTH,
    SERVER_RECEIVE_INFO_BOX,
    SERVER_DOOR_CMD,
    SERVER_SEND_CONSOLE_OUTPUT,

    SERVER_SET_CLIENT_STATE,
    SERVER_CON_PRINTF,
    SERVER_SEND_CHAT_MSG,
    SERVER_SEND_FLOATING_DAMAGE,

    SERVER_VISITED_MAP_CELLS,
    SERVER_ALL_STATIC_MAP_CELLS,
    SERVER_RESEND_WAYPOINT_REQUEST,
    SERVER_UPDATE_WAYPOINT,
    SERVER_SET_WAYPOINT,

    // team commands
    SERVER_TEAM_OFFER,

    // taskforce
    SERVER_TASKFORCE_KICK,
    SERVER_TASKFORCE_QUIT,

    // sg commands
    SERVER_SUPERGROUP_OFFER,
    SERVER_SGROUP_CREATE_REPLY,
    SERVER_SUPERGROUP_COSTUME,
    SERVER_HIDE_EMBLEM_UPDATE,

    // alliance commands
    SERVER_ALLIANCE_OFFER,

    // league commands
    SERVER_LEAGUE_OFFER,
    SERVER_LEAGUE_TEAM_KICK,
    SERVER_LEAGUE_ER_QUIT,

    // cutscene commands
    SERVER_CUTSCENE_UPDATE,

    // trade
    SERVER_TRADE_OFFER,
    SERVER_TRADE_INIT,
    SERVER_TRADE_CANCEL,
    SERVER_TRADE_UPDATE,
    SERVER_TRADE_SUCESS,

    SERVER_SEND_FRIENDS,

    SERVER_CONTROL_PLAYER,            // Tell a client that it can take control of another player.
    SERVER_CONTACT_DIALOG_OPEN,        // open the contact dialog box
    SERVER_CONTACT_DIALOG_CLOSE,    // close the contact dialog box
    SERVER_CONTACT_DIALOG_OK,        // simple ok dialog
    SERVER_CONTACT_DIALOG_YESNO,    // simple yes/no dialog
    SERVER_CONTACT_STATUS,            // Mapserver sending contact info update to the client
    SERVER_ACCESSIBLE_CONTACT_STATUS,    // Mapserver sending accessible contact info to the client
    SERVER_CONTACT_SELECT,            // Mapserver causing selection of contact
    SERVER_TASK_STATUS,                // mapserver sending task info update to the client
    SERVER_TASK_SELECT,                // mapserver asking client to select a task
    SERVER_TASK_REMOVE_TEAMMATE_TASKS,    // mapserver sending task info update to the client
    SERVER_MISSION_ENTRY,            // Mapserver is sending mission entry dialog
    SERVER_MISSION_EXIT,            // Mapserver is sending mission exit dialog
    SERVER_MISSION_KICKTIMER,        // tell client it will be kicked from mission at specified time
    SERVER_TEAMCOMPLETE_PROMPT,        // Prompt the client to chose to complete their task
    SERVER_BROKER_CONTACT,            // Alert player he can receive a new contact
    SERVER_DEAD_NOGURNEY,            // show dialog before resurrection
    SERVER_DOORANIM,                // server is requesting client animate into door
    SERVER_DOOREXIT,                // server is requesting client fade in again after door anim
    SERVER_FACE_ENTITY,
    SERVER_FACE_LOCATION,
    SERVER_SEND_FLOATING_INFO,
    SERVER_SEND_PLAY_SOUND,
    SERVER_SEND_FADE_SOUND,
    SERVER_SEND_DESATURATE_INFO,
    SERVER_SET_STANCE,
    SERVER_MAP_XFER_LIST,
    SERVER_MAP_XFER_LIST_INIT,
    SERVER_MAP_XFER_LIST_APPEND,
    SERVER_MAP_XFER_LIST_CLOSE,
    SERVER_ENABLE_CONTROL_LOG,

    SERVER_LEVEL_UP,
    SERVER_LEVEL_UP_RESPEC,
    SERVER_NEW_TITLE,

    SERVER_PERFORMANCE_UPDATE,

    SERVER_CSR_BUG_REPORT,        // allows CSR to send bug report for another player

    SERVER_SEND_EMAIL_HEADERS,
    SERVER_SEND_EMAIL_MESSAGE,
    SERVER_SEND_EMAIL_MESSAGE_STATUS,

    // Visit location task related commands
    SERVER_TASK_VISITLOCATION_UPDATE,    // Tell the client the full list of location group names they are to visit.

    SERVER_SEND_PLAYER_INFO,
    SERVER_SEND_COMBAT_STATS,
    SERVER_CLUE_UPDATE,
    SERVER_KEYCLUE_UPDATE,
    SERVER_SOUVENIRCLUE_UPDATE,
    SERVER_SOUVENIRCLUE_DETAIL,
    SERVER_MISSION_OBJECTIVE_TIMER_UPDATE,

    SERVER_REGISTER_SUPERGROUP,
    SERVER_SUPERGROUP_LIST,
    SERVER_TASK_DETAIL,

    SERVER_BROWSER_TEXT,
    SERVER_BROWSER_CLOSE,

    SERVER_STORE_OPEN,
    SERVER_STORE_CLOSE,

    SERVER_BUG_REPORT,    // server sends /bugqa report to client for local logging (QA purposes)

    SERVER_MISSION_SURVEY,
    SERVER_SEND_TRAY_ADD,

    SERVER_COMBINE_RESPONSE,
    SERVER_BOOSTER_RESPONSE,
    SERVER_CATALYST_RESPONSE,

    // Arena stuff
    SERVER_ARENA_KIOSK,
    SERVER_ARENA_EVENTS,
    SERVER_ARENA_EVENTUPDATE,
    SERVER_ARENA_UPDATE_TRAY_DISABLE,
    SERVER_ARENAKIOSK_SETOPEN,
    SERVER_ARENA_OFFER,
    SERVER_ARENA_ERROR,

    SERVER_SGRAID_COMPASS_STRING,
    SERVER_SGRAID_UPDATE,
    SERVER_SGRAID_ERROR,
    SERVER_SGRAID_OFFER,
    SERVER_SGRAID_INFO,

    SERVER_TAILOR_OPEN,
    SERVER_RESPEC_OPEN,
    SERVER_AUCTION_OPEN,
    SERVER_SEARCH_RESULTS,

    SERVER_VALIDATE_RESPEC,
    SERVER_SEND_REWARD_CHOICE,

    SERVER_SALVAGE_IMMEDIATE_USE_STATUS,

    SERVER_SEND_PACKAGEDENT,

    SERVER_LARGE_PACKET,

    SERVER_SCRIPT_DEBUGINFO,

    SERVER_SHARDCOMM,

    SERVER_ARENA_UPDATE_PLAYER,
    SERVER_ARENA_REQRESULTS,
    SERVER_ARENA_START_COUNT,
    SERVER_ARENA_COMPASS_STRING,
    SERVER_ARENA_VICTORY_INFORMATION,
    SERVER_ARENA_SCHEDULED_TELEPORT,
    SERVER_ARENA_RUN_EVENT_WINDOW,
    SERVER_ARENA_NOTIFY_FINISH,

    SERVER_SCRIPT_UI,
    SERVER_SCRIPT_UI_UPDATE,

    SERVER_MISSION_WAYPOINT,
    SERVER_MISSION_KEYDOOR,

    SERVER_PET_UI_UPDATE,

    SERVER_ARENA_MANAGEPETS,
    SERVER_UPDATE_PET_STATE,
    SERVER_BASE_CREATE,

    //map generation
    SERVER_MAP_GENERATION,

    SERVER_UPDATE_BASE_INTERACT,
    SERVER_UPDATE_BASE_MODE,
    SERVER_UPDATE_RAID_STATE,
    SERVER_UPDATE_NAME,
    SERVER_UPDATE_PRESTIGE,

    SERVER_MISSION_CONTROL,
    SERVER_DEBUG_LOCATION,
    SERVER_EDIT_VILLAIN_COSTUME,

    SERVER_PLAQUE_DIALOG,
    SERVER_RAID_RESULT,
    SERVER_AUCTION_HISTORY,
    SERVER_AUCTION_ITEMSTATUS,
    SERVER_AUCTION_BATCH_ITEMSTATUS,
    SERVER_AUCTION_LIST_ITEMSTATUS,
    SERVER_AUCTION_BANNED_UPDATE,
    SERVER_ACCOUNTSERVER_CHARCOUNT,
    SERVER_ACCOUNTSERVER_CATALOG,
    SERVER_ACCOUNTSERVER_CLIENTAUTH,
    SERVER_ACCOUNTSERVER_PLAYNC_AUTH_KEY,
    SERVER_ACCOUNTSERVER_NOTIFYREQUEST,
    SERVER_ACCOUNTSERVER_INVENTORY,

    SERVER_FLASHBACK_LIST,
    SERVER_FLASHBACK_DETAILS,
    SERVER_FLASHBACK_IS_ELIGIBLE,
    SERVER_FLASHBACK_CONFIRM,

    SERVER_TASKFORCE_TIME_LIMITS,
    SERVER_SETDEBUGPOWER,
    SERVER_AUTH_BITS,
    SERVER_SELECT_BUILD,

    SERVER_MISSIONSERVER_SEARCHPAGE,
    SERVER_MISSIONSERVER_ARCINFO,
    SERVER_MISSIONSERVER_ARCDATA,
    SERVER_ARCHITECTKIOSK_SETOPEN,

    SERVER_SG_COLOR_DATA,
    SERVER_RENAME_BUILD,
    SERVER_COSTUME_CHANGE_EMOTE_LIST,
    SERVER_CONFIRM_SG_PROMOTE,
    SERVER_LEVELINGPACT_INVITE,

    SERVER_ARCHITECT_COMPLETE,
    SERVER_ARCHITECT_SOUVENIR,
    SERVER_ARCHITECT_INVENTORY,

    SERVER_UPDATE_BADGE_MONITOR_LIST,
    SERVER_SEND_DIALOG,
    SERVER_SEND_TOKEN,
    SERVER_SG_PERMISSIONS,
    // Not yet
    //SERVER_ENABLE_ASSERT_ON_BS_ERRORS,

    SERVER_BEGIN_BYTE_ALIGNED_DATA,
    SERVER_SEND_ITEMLOCATIONS,
    SERVER_SEND_CRITTERLOCATIONS,
    SERVER_SEND_MORAL_CHOICE,
    SERVER_DETACH_SCRIPT_UI,

    SERVER_SEND_POP_HELP_TAG,
    SERVER_SEND_POP_HELP_RESET,
    SERVER_SEND_POP_HELP_N,

    SERVER_SEND_KARMA_STATS,

    // Turnstile server
    SERVER_EVENT_LIST,
    SERVER_QUEUE_STATUS,
    SERVER_EVENT_READY,
    SERVER_EVENT_READY_ACCEPT,
    SERVER_EVENT_START_STATUS,
    SERVER_EVENT_STATUS,
    SERVER_EVENT_JOIN_LEADER,

    SERVER_MISSIONSERVER_ARCDATA_OTHERUSER,
    SERVER_GOINGROGUE_NAG,
    SERVER_INCARNATE_TRIAL_STATUS,
    SERVER_POPHELP_EVENT_HAPPENED_BY_TAG,
    
    SERVER_VISITOR_SHARD_XFER_DATA,
    SERVER_VISITOR_SHARD_XFER_JUMP,

    SERVER_CHANGE_WINDOW_COLORS,

    SERVER_UPDATE_TURNSTILE_STATUS,
    SERVER_ENDGAMERAID_VOTE_KICK,

    SERVER_COMBAT_MESSAGE,

    SERVER_SHOW_CONTACT_FINDER_WINDOW,
    
    SERVER_OPEN_SALVAGE_REQUEST,
    SERVER_OPEN_SALVAGE_RESULTS,

    SERVER_WEB_STORE_OPEN_PRODUCT,

    SERVER_CONVERT_ENHANCEMENT_RESULT,

    SERVER_SUPPORT_HOME,
    SERVER_SUPPORT_KB,
    SERVER_DISPLAY_PRODUCT_PAGE,
    SERVER_FORCE_QUEUE_FOR_EVENT,

    SERVER_START_FORCED_MOVEMENT,

    // MS: ATTENTION: SERVER_CMD_COUNT is the _LAST_ thing in this list.
    //     Putting anything afterwards is an instantaneous dunce-cap offense.
    //     And I don't mean DUNC cap, because putting something below SERVER_CMD_COUNT
    //     doesn't make you cool enough to be the DUNC.
    SERVER_CMD_COUNT,
    // MS: What?  You were thinking of putting something down here?
    //     Think again, Einstein.  You might want to read the previous comment
    //     about how incredibly lame it is to put something down here.
} ServerCommCmd;
#elif defined(COH_ORIGINAL_COMMAND_SENDERS)
#line 913 "MapServer/src/storyarc/storySend.c"
void ContactStatusSendEmpty(Packet* pak)
{
    // The fields sent here must match the ones in ContactStatusSend()
    // and ContactStatusAccessibleSend() which are immediately below,
    // and also the ones in ContactStatusReceive() in the client! 
    // If they do not, things like taskforces will break and there will be gloom and unhappiness!
    pktSendBits(pak, 1, 0);            // no filename coming
    pktSendString(pak, "");            // name
    pktSendString(pak, "");            // location
    pktSendBits(pak, 1, 0);            // call override
    pktSendBits(pak, 1, 0);            // ask about override
    pktSendBits(pak, 1, 0);            // leave override
    pktSendBits(pak, 1, 0);            // image override
    pktSendBitsAuto(pak, 0);        // costume
    pktSendBitsAuto(pak, 0);        // handle
    pktSendBitsAuto(pak, 0);        // no task
    pktSendBitsAuto(pak, 0);        // no task
    pktSendBits(pak, 1, 0);            // notify player
    pktSendBits(pak, 1, 0);            // has tasks
    pktSendBits(pak, 1, 0);            // can use cell
    pktSendBits(pak, 1, 0);            // is the newspaper
    pktSendBits(pak, 1, 0);            // no story arcs
    pktSendBits(pak, 1, 0);            // no mini arcs
    pktSendBitsPack(pak, 1, 0);            // tip type
    pktSendBits(pak, 1, 0);            // won't interact
    pktSendBits(pak, 1, 0);            // is meta contact
    pktSendBitsAuto(pak, 0);        // current contact points
    pktSendBitsAuto(pak, 0);        // friend level
    pktSendBitsAuto(pak, 0);        // confidant level
    pktSendBitsAuto(pak, 0);        // complete level
    pktSendBitsAuto(pak, 0);        // heist level
    pktSendBitsAuto(pak, 0);        // no alliance
    pktSendBits(pak, 1, 0);            // no location
}
#line 1702 "MapServer/src/storyarc/storySend.c"
void ClueSend(const StoryClue* clue, ScriptVarsTable* vars, Packet* pak, Entity * e)
{
    const char* s;

    pktSendString(pak, clue->name);

    pktSendBits(pak, 1, server_state.clickToSource);
    if (server_state.clickToSource)
        pktSendString(pak, saUtilDirtyFileName(clue->filename));

    s = saUtilTableAndEntityLocalize(clue->displayname, vars, e);
    pktSendString(pak, s);

    s = saUtilTableAndEntityLocalize(clue->detailtext, vars, e);
    pktSendString(pak, s);

    pktSendString(pak, ClueIconFile(clue));
}
#else
#line 1066 "Game/src/clientcomm/clientcomm.c"
static void receiveByteAlignmentTag(Packet* pak)
{
    pktAlignBitsArray(pak);
}
#line 982 "Game/src/clientcomm/clientcommreceive.c"
void receiveStaticMapCells(Packet *pak)
{
    int        i;
    int db_id = pktGetBitsAuto(pak);
    int numMaps = pktGetBitsAuto(pak);
    VisitedStaticMap *vsm = automap_getMapStruct(db_id);
    automap_clearStaticMaps(vsm);
    for (i= 0; i < numMaps; ++i)
    {
        int map_id = pktGetBitsAuto(pak);
        if (map_id)
        {
            int opaque_fog = pktGetBits(pak, 1);
            int cell_array_size = (MAX_MAPVISIT_CELLS+31)/32;
            U32 cell_array[4*(MAX_MAPVISIT_CELLS+31)/32];
            int j;
            for (j = 0; j < cell_array_size; j++)
                cell_array[j] = pktGetBits(pak, 32);
            automap_addStaticMapCell(vsm, db_id, map_id, opaque_fog, cell_array_size, cell_array);
        }
    }
}
#line 304 "Game/src/storyarc/contactClient.c"
void ContactStatusReceive(ContactStatus* status, int index, Packet* pak)
{
    int overheadState = status->currentOverheadIconState;

    ContactStatusClear(status);
    status->currentOverheadIconState = overheadState;

    if (pktGetBits(pak, 1))
        status->filename = strdup(pktGetString(pak));
    status->name = strdup(pktGetString(pak));
    status->locationDescription = strdup(pktGetString(pak));

    status->callOverride = (pktGetBits(pak, 1))?strdup(pktGetString(pak)):NULL;
    status->askAboutOverride = (pktGetBits(pak, 1))?strdup(pktGetString(pak)):NULL;
    status->leaveOverride = (pktGetBits(pak, 1))?strdup(pktGetString(pak)):NULL;
    status->imageOverride = (pktGetBits(pak, 1))?strdup(pktGetString(pak)):NULL;

    status->npcNum = pktGetBitsAuto(pak);
    status->handle = pktGetBitsAuto(pak);
    status->taskcontext = pktGetBitsAuto(pak);
    status->tasksubhandle = pktGetBitsAuto(pak);
    //    status->timeAutoRemokes = pktGetBitsAuto(pak);//+ SecondsSince2000();

    status->notifyPlayer = pktGetBits(pak, 1);
    status->hasTask = pktGetBits(pak, 1);
    status->canUseCell = pktGetBits(pak, 1);
    status->isNewspaper = pktGetBits(pak, 1);
    status->onStoryArc = pktGetBits(pak, 1);
    status->onMiniArc = pktGetBits(pak, 1);
    status->tipType = pktGetBitsPack(pak, 1);
    status->wontInteract = pktGetBits(pak, 1);
    status->metaContact = pktGetBits(pak, 1);

    status->currentCP = pktGetBitsAuto(pak);
    status->friendCP = pktGetBitsAuto(pak);
    status->confidantCP = pktGetBitsAuto(pak);
    status->completeCP = pktGetBitsAuto(pak);
    status->heistCP = pktGetBitsAuto(pak);
    if (status->completeCP && (status->currentCP > status->completeCP))
        status->currentCP = status->completeCP; // just clamp this for display
    else if (!status->completeCP && status->currentCP > status->heistCP) 
        status->currentCP = status->heistCP; // just clamp this for display

    status->alliance = pktGetBitsAuto(pak);

    status->hasLocation = pktGetBits(pak, 1);

    if (status->hasLocation)
    {
        int temp;

        assignContactIcon(status);
        status->location.handle = status->handle;

        status->location.destPNPC = 0;
        if (pktGetBits(pak, 1))
        {
            char pnpcName[500];
            strcpy(pnpcName, pktGetString(pak));
            status->location.destPNPC = PNPCFindDef(pnpcName);
        }

        status->location.destEntity = 0;
        if (pktGetBits(pak, 1))
        {
            temp = pktGetBitsAuto(pak);
            if (temp)
            {
                int i;

                for (i = 1; i < entities_max; i++)
                {
                    if (entities[i]->id == temp)
                    {
                        status->location.destEntity = entities[i];
                        break;
                    }
                }
            }
        }

        status->location.world_location[3][0] = pktGetF32(pak);
        status->location.world_location[3][1] = pktGetF32(pak);
        status->location.world_location[3][2] = pktGetF32(pak);
        strcpy(status->location.mapName, pktGetString(pak));
        strcpy(status->location.name, pktGetString(pak));
        if (index != -1)
        {
            status->location.id = CONTACT_LOCATIONS + index;
        }
    }
    else if (index != -1) // we may have lost this location, make sure we don't have waypoint
    {
        memset(&status->location, 0, sizeof(status->location));
        compass_ClearAllMatchingId(CONTACT_LOCATIONS + index);
    }

    contactsDirty = true;
}
#line 150 "Game/src/storyarc/contactClient.c"
void ContactStatusListReceive(Packet* pak)
{
    int contactCount;
    int contactIndex;
    int deleteCount;
    int deleteIndex;
    int desiredSize;
    int contactSize;
    int pointIndex;
    U32 now = timerServerTime();

    // init global list if necessary
    if (!contacts)
    {
        eaCreate(&contacts);
        eaPush(&contacts, ContactStatusCreate()); // always must have mission status
    }

    for (pointIndex = 0; pointIndex < ALIGNMENT_POINT_MAX_COUNT; pointIndex++)
    {
        timeWhenCanEarnAlignmentPoint[pointIndex] = now + pktGetBitsAuto(pak);
        earnedAlignments[pointIndex] = pktGetBitsAuto(pak);
    }
    heroAlignmentPoints_self = pktGetBitsAuto(pak);
    vigilanteAlignmentPoints_self = pktGetBitsAuto(pak);
    villainAlignmentPoints_self = pktGetBitsAuto(pak);
    rogueAlignmentPoints_self = pktGetBitsAuto(pak);

    // How many contacts are there, NOT including the mission info?
    //        -1 can be passed in here, and the contact list size will not be adjusted
    contactSize = pktGetBitsAuto(pak);
    if (contactSize >= 0)
        desiredSize = contactSize+1;
    else
        desiredSize = eaSize(&contacts);

    // Handle any manual deletions first (used in change-only updates)
    deleteCount = pktGetBitsAuto(pak);

    for (deleteIndex = 0; deleteIndex < deleteCount; deleteIndex++)
    {
        int deleteHandle = pktGetBitsAuto(pak);
        for (contactIndex = 0; contactIndex < eaSize(&contacts); contactIndex++)
        {
            if (contacts[contactIndex]->handle == deleteHandle)
            {
                ContactStatusDestroy(eaRemove(&contacts, contactIndex));
                break;
            }
        }
    }

    // Handle automatic deletions next (used in full updates)
    while (eaSize(&contacts) > desiredSize)
    {
        ContactStatusDestroy(eaPop(&contacts));
    }
    while (eaSize(&contacts) < desiredSize)
    {
        eaPush(&contacts, ContactStatusCreate());
    }

    // How many incoming contact status updates are there?
    contactCount = pktGetBitsAuto(pak);
    for(contactIndex = 0; contactIndex < contactCount; contactIndex++)
    {
        ContactStatus* status;
        int contactNumber;

        //    Which contact is being updated?
        contactNumber = pktGetBitsAuto(pak);
        status = contacts[contactNumber];

        //    Unpack contact status.
        ContactStatusReceive(status, contactNumber, pak);
    }

    TaskUpdateDestination(&waypointDest);
    TaskUpdateDestination(&activeTaskDest);
#if !TEST_CLIENT
    contactReparse();
#endif
}
#line 235 "Game/src/storyarc/contactClient.c"
static void ContactStatusDestroyAdapter(void* arg0)
{
    ContactStatusDestroy((ContactStatus*)arg0);
}
#line 240 "Game/src/storyarc/contactClient.c"
void ContactStatusAccessibleListReceive(Packet *pak)
{
    int contactIndex, contactCount;

    if (!contactsAccessibleNow)
    {
        eaCreate(&contactsAccessibleNow);
    }
    else
    {
        eaClearEx(&contactsAccessibleNow, ContactStatusDestroyAdapter);
    }

    // How many incoming contact status updates are there?
    contactCount = pktGetBitsAuto(pak);
    for(contactIndex = 0; contactIndex < contactCount; contactIndex++)
    {
        ContactStatus* status = ContactStatusCreate();

        //    Unpack contact status.
        ContactStatusReceive(status, -1, pak);

        eaPush(&contactsAccessibleNow, status);
    }
}
#line 804 "Game/src/clientcomm/clientcommreceive.c"
void receiveVisitLocations(Packet *pak)
{
    if(visitLocations)
    {
        eaClearEx(&visitLocations, NULL);
        eaSetSize(&visitLocations, 0);
    }
    else
    {
        eaCreate(&visitLocations);
    }

    {
        int locationCount;
        int i;

        locationCount = pktGetBitsPack(pak, 1);

        for(i = 0; i < locationCount; i++)
        {
            char* locationName;
            locationName = pktGetString(pak);
            eaPush(&visitLocations, strdup(locationName));
        }
    }
}
#line 551 "Game/src/storyarc/contactClient.c"
void TaskStatusReceive(TaskStatus* task, int index, int listid, Packet* pak)
{
    if (pktGetBits(pak, 1))
        strcpy(task->filename, pktGetString(pak));
    strncpyt(task->description, pktGetString(pak), 256);
    strncpyt(task->owner, pktGetString(pak), MAX_NAME_LEN);

    task->ownerDbid = pktGetBitsPack(pak, 1);                        // task UID
    task->context = pktGetBitsPack(pak, 1);
    task->subhandle = pktGetBitsPack(pak, 1);
    task->level = pktGetBitsPack(pak, 1);


    task->difficulty.levelAdjust = pktGetBitsAuto(pak);
    task->difficulty.teamSize = pktGetBitsAuto(pak);
    task->difficulty.dontReduceBoss = pktGetBits(pak,1);
    task->difficulty.alwaysAV = pktGetBits(pak,1);

    task->alliance = pktGetBitsPack(pak, 2);

    strncpyt(task->state, pktGetString(pak), 256);

    task->timeout = pktGetBitsPack(pak, 1);
    task->timezero = pktGetBitsAuto(pak);
    task->timerType = pktGetBitsAuto(pak);
    task->failOnTimeout = pktGetBitsAuto(pak);
    task->isComplete = pktGetBits(pak, 1);
    task->isMission = pktGetBits(pak, 1);
    task->hasRunningMission = pktGetBits(pak, 1);
    task->isSGMission = pktGetBits(pak, 1);
    task->zoneTransfer = pktGetBits(pak, 1);
    task->teleportOnComplete = pktGetBits(pak, 1);
    task->enforceTimeLimit = pktGetBits(pak, 1);
    task->isAbandonable = pktGetBits(pak, 1);
    task->isZowie = pktGetBits(pak, 1);
    task->hasLocation = pktGetBits(pak, 1);
    if (task->hasLocation)
    {
        task->location.type = ICON_MISSION;
        task->location.icon = atlasLoadTexture("map_enticon_mission_a");
        task->location.iconB = atlasLoadTexture("map_enticon_mission_b");
        task->location.iconBInCompass = 1;
        task->location.dbid = task->ownerDbid;
        task->location.context = task->context;
        task->location.subhandle = task->subhandle;

        task->location.angle = PI/4;
        task->location.world_location[3][0] = pktGetF32(pak);
        task->location.world_location[3][1] = pktGetF32(pak);
        task->location.world_location[3][2] = pktGetF32(pak);
        task->location.contactType = pktGetBitsAuto(pak);
        strncpyt(task->location.mapName, pktGetString(pak), ARRAY_SIZE(task->location.mapName));
        strncpyt(task->location.name, pktGetString(pak), ARRAY_SIZE(task->location.name));
    }
    else // we may have lost this location, make sure we don't have waypoint
    {
        memset(&task->location, 0, sizeof(task->location));
        // don't clear if it's a zowie task, because we don't have legit data until after updateAutomapZowies().
        if (!task->isZowie) 
        {
            if (task->isSGMission && (index < 0))
                compass_ClearAllMatchingId(SG_LOCATION);
            else
                compass_ClearAllMatchingId(TASK_LOCATIONS + index + TASK_SET_LOCATIONS * listid);
        }

        // if we have a taskLocationMap on another map
         if (pktGetBits(pak, 1))
         {
            task->location.contactType = pktGetBitsAuto(pak);
             strncpyt(task->location.mapName, pktGetString(pak), ARRAY_SIZE(task->location.mapName));
         }
    }

    // always set the location id even if !hasLocation. This is needed for zowie tasks.
    if (task->isSGMission && (index < 0))
        task->location.id = SG_LOCATION;
    else
        task->location.id = TASK_LOCATIONS + index + TASK_SET_LOCATIONS * listid;

    if (task->isZowie)
    {
        int i;
        char *poolSize;

        task->zinfo = pktGetBitsPack(pak, 1);
        task->zseed = pktGetBits(pak, 32);
        task->zmap_id = pktGetBitsPack(pak, 1);
        strncpyt(task->ztype, pktGetString(pak), MAX_ZOWIE_NAME);
        strncpyt(task->zname, pktGetString(pak), MAX_ZOWIE_NAME);
        poolSize = pktGetString(pak);
        // Decomposition of the pool sizes string is much simpler here, since the mapserver has already vetted the data in zowie_setup(...) in zowie.c
        // Also, it is safe to hand the string returned from PktGetString directly to strtok.  Sure, strtok, damages the passed string, but this is
        // not a problem since it lives in a static buffer maintained by PktGetString, and can be safely treated as non-const.  it'll get totalled on
        // the next call to PktgetString anyways, so we really don't care.
        poolSize = strtok(poolSize, " ");
        i = 0;
        while (poolSize != NULL)
        {
            task->zpoolSize[i++] = atoi(poolSize);
            poolSize = strtok(NULL, " ");
        }
    }

    // invalidate the detail field whenever we get an update
    task->detail[0] = 0;
    task->detailInvalid = 1;
}
#line 443 "Game/src/storyarc/contactClient.c"
void TaskStatusListReceive(Packet* pak)
{
    int taskCount;
    int desiredSize;
    int taskSize;
    int i;
    int taskSetCount, currentSet;
    TaskStatus*** taskList;
    TaskStatus* activetask;

    // Since tasks are stored in a 2D earray of earrays, it'd be a ton too much work to figure all the edge cases of tasks getting added,
    // removed, and changed.  So we take the safe approach and simply blow everything away here, receive the update, and then turn on all
    // glow flags at the bottom.
    TaskProcessZowieGlowFlags(0);

    taskSetCount = pktGetBitsPack(pak, 1);
    for(currentSet = 0; currentSet < taskSetCount; currentSet++)
    {
        int level = 256, teamsize, boss, av;
        int dbid = pktGetBitsPack(pak, 1);
        int forme = pktGetBits(pak, 1);

        if( pktGetBits(pak,1) )
        {
            level = pktGetBitsAuto(pak);
            teamsize = pktGetBitsAuto(pak);
            boss = pktGetBits(pak, 1);
            av = pktGetBits(pak, 1);
        }

        // How many tasks are there, NOT including the mission info?
        //        -1 can be passed in here, and the task list size will not be adjusted
        taskSize = pktGetBitsPack(pak, 1);

        // How many incoming task status updates are there?
        taskCount = pktGetBitsPack(pak, 1);

        // What kind of update is in this set?
        // Does it contain the player's own task list?
        taskList = TaskStatusListGetOrAdd(dbid);
        if(!eaSize(taskList))
        {
            eaPush(taskList, TaskStatusCreate()); // always must have mission status
        }

        if( level != 256)
            TaskStatusSetDifficulty(dbid, level, teamsize, boss, av);

        if (taskSize >= 0)
            desiredSize = taskSize+1;
        else
            desiredSize = eaSize(taskList);

        while (eaSize(taskList) > desiredSize)
        {
            TaskStatusDestroy(eaPop(taskList));
        }
        while (eaSize(taskList)< desiredSize)
        {
            eaPush(taskList, TaskStatusCreate());
        }

        for(i = 0; i < taskCount; i++)
        {
            TaskStatus* status;
            int taskIndex;

            //    Which task is being updated?
            taskIndex = pktGetBitsPack(pak, 1);
            status = (*taskList)[taskIndex];

            //    Unpack contact status.
            TaskStatusReceive(status, taskIndex, TaskStatusSetIndex(dbid), pak);
        }

        // Empty task list?
        if(eaSize(taskList) == 1 && !(*taskList)[0]->description[0])
        {
            TaskStatusListRemove(dbid);
        }
    }

    TaskStatusSetsSort();
    // Turn zowie glow flags on.  See comment at the top of this routine for details on what is going on.
    TaskProcessZowieGlowFlags(1);
    // Update automap zowies in case one got turned off during this update
    // DGNOTE 7/22/2010
    // The second parameter to updateAutomapZowies(...) determines if the first is to be cached or not.  Setting it to 0 causes this routine to
    // ignore the first parameter and use the cached copy instead.
    updateAutomapZowies(NULL, USE_CACHED);
    // need to auto-select active task whenever we get an update
    activetask = PlayerGetActiveTask();
    if (activetask)
    {
        compass_SetTaskDestination(&activeTaskDest, activetask);
    }
    else
    {
        clearDestination(&activeTaskDest);
    }

    TaskUpdateDestination(&waypointDest);
#if !TEST_CLIENT
    missionReparse();
#endif
}
#line 18 "Game/src/storyarc/storyarcClient.c"
void ClueReceive(StoryClue* clue, Packet* pak)
{
    char* s;

    s = pktGetString(pak);
    clue->name = strdup(s);

    if (pktGetBits(pak, 1))
        clue->filename = strdup(pktGetString(pak));

    s = pktGetString(pak);
    clue->displayname = strdup(s);

    s = pktGetString(pak);
    clue->detailtext = strdup(s);

    s = pktGetString(pak);
    clue->iconfile = strdup(s);
}
#line 38 "Game/src/storyarc/storyarcClient.c"
static void StoryClueDestroyAdapter(void* arg0)
{
    StoryClueDestroy((StoryClue*)arg0);
}
#line 43 "Game/src/storyarc/storyarcClient.c"
void ClueListReceive(Packet* pak)
{
    int clueCount;
    int i;

    if(!storyClues)
    {
        eaCreate(&storyClues);
    }
    else
    {
        eaClearEx(&storyClues, StoryClueDestroyAdapter);
    }

    // How many clues are we receving?
    clueCount = pktGetBitsPack(pak, 1);

    for(i = 0; i < clueCount; i++)
    {
        StoryClue* clue = StoryClueCreate();
        ClueReceive(clue, pak);
        eaPush(&storyClues, clue);
    }
}
#line 73 "Game/src/storyarc/storyarcClient.c"
void KeyClueListReceive(Packet* pak)
{
    int clueCount;
    int i;

    if(!keyClues)
    {
        eaCreate(&keyClues);
    }
    else
    {
        eaClearEx(&keyClues, StoryClueDestroyAdapter);
    }

    // How many clues are we receving?
    clueCount = pktGetBitsPack(pak, 1);

    for(i = 0; i < clueCount; i++)
    {
        StoryClue* clue = StoryClueCreate();
        ClueReceive(clue, pak);
        eaPush(&keyClues, clue);
    }
}
#line 129 "Game/src/storyarc/storyarcClient.c"
void scReceiveHeader(SouvenirClue* clue, Packet* pak)
{
    //    Get and set the clue uid.
    clue->uid = pktGetBitsPack(pak, 1);

    // Get the filename(only sent in dev mode)
    if (pktGetBits(pak, 1))
        clue->filename = strdup(pktGetString(pak));

    //    Get and set the clue displayName.
    clue->displayName = strdup(pktGetString(pak));

    //    Get and set the clue iconName.
    clue->icon = strdup(pktGetString(pak));
}
#line 104 "Game/src/storyarc/storyarcClient.c"
void scReceiveAllHeaders(Packet* pak)
{
    int clueCount;
    int i;

    souvenirCluePrepareUpdate();

    // reset flashback cache
    flashbackListClear();

    // Get the number of clues in this update.
    clueCount = pktGetBitsPack(pak, 1);

    // For each clue to be received...
    for(i = 0; i < clueCount; i++)
    {
        //    Create a new SouvenirClue.
        SouvenirClue* clue = scCreate();

        scReceiveHeader(clue, pak);

        souvinerClueAdd( clue );
    }
}
#endif
