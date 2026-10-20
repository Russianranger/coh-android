/* Whole unchanged pinned original functions; local symbol/storage shims only. */
int NPCcostume_receive(Packet *pak, CustomNPCCostume* costume)
{
    int i, j, count;

    StructInitFields(ParseCustomNPCCostume, costume);

    costume->skinColor.integer    = pktGetBits(pak, 32);
    count = pktGetBits(pak, 6);
    for(i=0; i < count; i++)
    {
        eaPush(&costume->parts, StructAllocRaw(sizeof(CustomNPCCostumePart)));
        for (j=0; j<2; j++) {
                costume->parts[i]->color[j].integer = pktGetBits(pak, 32);
        }
        costume->parts[i]->regionName = allocAddString(pktGetString(pak));
    }

    return 1;
}
static void entRecieveTaskforceArchitectInfo(Packet *pak, Entity *e)
{
    if( !pktGetBits(pak,1) ) // are we getting an update?
    {
        e->onArchitect = 0;
        return;
    }

    e->onArchitect = pktGetBits(pak, 1);
    if(e->onArchitect) 
    {
        Costume * costume = 0;
        char *contact_name;
        int architect_flags, architect_id, contact;
        devassert(e->taskforce);

        architect_flags = pktGetBitsAuto(pak);
        architect_id = pktGetBitsAuto(pak);
        contact = pktGetBitsAuto(pak);
        contact_name = pktGetString(pak);

        if (e->taskforce)
        {
            e->taskforce->architect_id = architect_id;
            e->taskforce->architect_flags = architect_flags;

            if (contact != e->taskforce->architect_contact_override)
            {
                e->taskforce->architect_useCachedCostume = 0;
                e->taskforce->architect_contact_override = contact;
            }
            if (stricmp(e->taskforce->architect_contact_name, contact_name) != 0)
            {
                e->taskforce->architect_useCachedCostume = 0;
                strcpy(e->taskforce->architect_contact_name, contact_name);
            }
        }

        if ( pktGetBits(pak,1) )
        {
            if( pktGetBits(pak, 1) )
            {
                costume = costume_create(GetBodyPartCount());
                costume_init(costume);
                costume_receive( pak, costume );
            }
            if (e->taskforce)
            {
                if (costume)
                {
                    if ( e->taskforce->architect_contact_costume ) 
                    {
                        costume_destroy(e->taskforce->architect_contact_costume);
                    }
                    e->taskforce->architect_contact_costume = costume;        
                    e->taskforce->architect_useCachedCostume = 0;
                }
            }

        }
        else
        {
            if ( e->taskforce->architect_contact_costume )
            {
                costume_destroy(e->taskforce->architect_contact_costume);
            }
            e->taskforce->architect_contact_costume = NULL;
        }
        if( pktGetBits(pak,1) )
        {
            CustomNPCCostume *costume = NULL;
            if ( pktGetBits(pak, 1) )
            {
                costume = StructAllocRaw(sizeof(CustomNPCCostume));
                NPCcostume_receive(pak, costume);
            }
            if (e->taskforce)
            {
                if (costume)
                {
                    if (e->taskforce->architect_contact_npc_costume)
                    {
                        StructDestroy(ParseCustomNPCCostume, e->taskforce->architect_contact_npc_costume);
                    }
                    e->taskforce->architect_contact_npc_costume = costume;
                    e->taskforce->architect_useCachedCostume = 0;
                }
            }
        }
        else
        {
            if ( e->taskforce->architect_contact_npc_costume )
            {
                StructDestroy(ParseCustomNPCCostume, e->taskforce->architect_contact_npc_costume);
            }
            e->taskforce->architect_contact_npc_costume = NULL;
        }
        if( pktGetBits(pak,1) )
        {
            char *pchName = strdup(pktGetString(pak));
            char *pchAuthor = strdup(pktGetString(pak));
            char *pchDescription = strdup(pktGetString(pak));
            int rating = pktGetBitsAuto(pak);
            int euro = pktGetBitsAuto(pak);

            e->architect_invincible = pktGetBitsAuto(pak);
            e->architect_untargetable = pktGetBitsAuto(pak);

            if (e->taskforce)
                missionReview_Set(e->taskforce->architect_id, e->taskforce->architect_flags, pchName, pchAuthor, pchDescription, rating, euro );
        
            SAFE_FREE(pchName);
            SAFE_FREE(pchAuthor);
            SAFE_FREE(pchDescription);
        }
    }
}
static int entReceiveTaskforceParameters(Packet *pak, Entity *e)
{
    U32 paramsSet;
    U32 count;
    U32 param;

     e->onFlashback = pktGetBitsPack(pak, 1);

    if(pktGetBits(pak, 1))
    {
        devassert(e->taskforce);

        paramsSet = pktGetBitsAuto(pak);

        if (e->taskforce)
        {
            e->taskforce->parametersSet = paramsSet;
        }

        for (count = 0; count < MAX_TASKFORCE_PARAMETERS; count++)
        {
            if (paramsSet & (1 << count))
            {
                param = pktGetBitsAuto(pak);

                if (e->taskforce)
                {
                    e->taskforce->parameters[count] = param;
                }
            }
        }

        // The server stores times in its own timebase. To send them to
        // us it subtracts its current time. We can then add back our
        // current time to get the right value, thereby compensating for
        // whatever different timezone or clock difference is between us.
        if (TaskForceIsParameterEnabled(e, TFPARAM_TIME_LIMIT))
        {
            e->taskforce->parameters[TFPARAM_TIME_LIMIT - 1] +=
                timerSecondsSince2000();
        }

        if (TaskForceIsParameterEnabled(e, TFPARAM_START_TIME))
        {
            e->taskforce->parameters[TFPARAM_START_TIME - 1] +=
                timerSecondsSince2000();
        }
    }


    return 1;
}
