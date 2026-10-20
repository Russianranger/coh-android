/* GENERATED from exact pinned LF source; regenerate with prepare_original_costume_receive.py. */
#ifdef COH_ORIGINAL_COSTUME_TYPES
typedef enum BodyType
{
    kBodyType_Male        = 0,  // All the values in body type MUST match the
    kBodyType_Female      = 1,  // ones which are read in the menu file.
    kBodyType_BasicMale   = 2,
    kBodyType_BasicFemale = 3,
    kBodyType_Huge        = 4,
    kBodyType_Enemy       = 5,
    kBodyType_Villain     = 6, // Except this one. This one is only set by code.
    kBodyType_Enemy2      = 7, // Except this one. This one is only set by code.
    kBodyType_Enemy3      = 8, // Except this one. This one is only set by code.

} BodyType;
typedef struct BodyTypeInfo
{
    BodyType bodytype;
    char *pchEntType;
    char *pchTexPrefix;
} BodyTypeInfo;
BodyTypeInfo g_BodyTypeInfos[] =
{
    // Make sure the kBodyType_... enums match the index in this list
    { kBodyType_Male         /* = 0 */,      "male",    "SM" },    // Default body type
    { kBodyType_Female       /* = 1 */,      "fem",     "SF" },
    { kBodyType_BasicMale    /* = 2 */,      "bm",      "BM" },
    { kBodyType_BasicFemale  /* = 3 */,      "bf",      "BF" },
    { kBodyType_Huge         /* = 4 */,      "huge",    "SH" },
    { kBodyType_Enemy        /* = 5 */,      "enemy",   "EY" },
    { kBodyType_Villain      /* = 6 */,      "enemy",    "EY" },
    { kBodyType_Enemy2       /* = 6 */,     "enemy2",    "EY" },
    { kBodyType_Enemy3       /* = 6 */,     "enemy3",    "EY" },
};
int getBodyTypeCount()
{
    return sizeof(g_BodyTypeInfos)/sizeof(BodyTypeInfo);
}

#else
F32 pktGetF(Packet *pak, int precision, F32 min, F32 max)
{
    int val = pktGetBits(pak, precision);
    return val * (max - min) / ((1<<precision)-1) + min;
}
const char *pktGetIndexedString(Packet *pak, cStashTable htStrings)
{
    if (pktGetBits(pak, 1))
    {
        int index;
        const char *debug_string="(no string)";
        const char *ret;
        int inTable = pktGetBits(pak, 1);
        if (pak->hasDebugInfo) {
            int debug_intable;
            debug_string = allocAddString(pktGetString(pak));
            debug_intable = stashFindIndexByKey(htStrings, debug_string, &index) || (strcmp(debug_string, "(null)")==0);
            assert(!g_bAssertOnBitStreamError || do_not_assert_on_bad_indexed_string_read || inTable == debug_intable);
        }
        if (inTable) {
            START_BIT_COUNT(pak, "stringIndex");
            index = pktGetBitsPack(pak, defaultBitsPack(htStrings));
            if (!stashFindKeyByIndex(htStrings, index, &ret))
                ret = NULL;
            STOP_BIT_COUNT(pak);

            if (pak->hasDebugInfo) {
                if (ret==NULL) {
                    assert(!g_bAssertOnBitStreamError || do_not_assert_on_bad_indexed_string_read || strcmp(debug_string, "(null)")==0);
                } else {                
                    assert(!g_bAssertOnBitStreamError || do_not_assert_on_bad_indexed_string_read || stricmp(ret, debug_string)==0);
                }
            }
            return ret;
        } else {
            START_BIT_COUNT(pak, "stringText");
            ret = (const char*)allocAddString(pktGetString(pak));
            STOP_BIT_COUNT(pak);
            return ret;
        }
    }
    else
    {
        return NULL;
    }
}
int pktGetIndexedGeneric(Packet *pak, cStashTable ht)
{
    U32 index;
    int inTable;
    int val;
    int debug_val=0;

    inTable = pktGetBits(pak, 1);
    if (pak->hasDebugInfo) {
        int debug_intable;
        debug_val = pktGetBitsPack(pak, 1);
        debug_intable = (debug_val && stashIntFindPointer(ht, debug_val, NULL) );
        assert(!g_bAssertOnBitStreamError || do_not_assert_on_bad_indexed_string_read || inTable == debug_intable);
    }
    if (inTable) {
        index = pktGetBitsPack(pak, defaultBitsPackGeneric(ht));
        if (!stashIntFindKeyByIndex(ht, index, &val) )
            val = 0;
        if (pak->hasDebugInfo) {
            assert(!g_bAssertOnBitStreamError || do_not_assert_on_bad_indexed_string_read || debug_val==val);
        }
        return val;
    } else {
        return pktGetBits(pak, 32);
    }
}
#define pktGetIndexedString(p,t) observed_indexed_string((p),(t))
static const char *getCachedIndexedString(Packet *pak)
{
    int cached = pktGetBits(pak, 1);
    const char *val;
    if (!cached) {
        val = pktGetIndexedString(pak, costume_HashTable);
        stringcache[stringcachecount] = val;
        if (stringcachecount > (1 << stringcacheorder) - 1) {
            stringcacheorder++;
        }
        stringcachecount++;
        assert(stringcachecount < ARRAY_SIZE(stringcache));
    } else {
        if (stringcachecount>1) {
            int index = pktGetBits(pak, stringcacheorder);
            val = stringcache[index];
        } else {
            val = stringcache[0];
        }
    }
    return val;
}
static int getCachedIndexedColor(Packet *pak)
{
    int cached = pktGetBits(pak, 1);
    int val;
    if (!cached) {
        val = pktGetIndexedGeneric(pak, costume_PaletteTable);
        colorcache[colorcachecount] = val;
        if (colorcachecount > (1 << colorcacheorder) - 1) {
            colorcacheorder++;
        }
        colorcachecount++;
        assert(colorcachecount < ARRAY_SIZE(colorcache));
    } else {
        if (colorcachecount>1) {
            int index = pktGetBits(pak, colorcacheorder);
            val = colorcache[index];
        } else {
            val = colorcache[0];
        }
    }
    return val;
}
#define getCachedIndexedString(p) observed_cached_string((p))
#define getCachedIndexedColor(p) observed_cached_color((p))
int costume_receive(Packet *pak, Costume* costume)
{
    int i, j, count;
    bool hasExtraInfo;

    // Reset the caches
    colorcachecount=0;
    colorcacheorder=0;
    stringcachecount=0;
    stringcacheorder=0;

    StructInitFields(ParseCostume, costume);

    if (pktGetBits(pak, 1))
        costume->appearance.entTypeFile = getCachedIndexedString(pak);

    if (pktGetBits(pak, 1))
        costume->appearance.costumeFilePrefix = getCachedIndexedString(pak);

    costume->appearance.bodytype            = pktGetBitsPack(pak, 6);
    costume->appearance.colorSkin.integer    = pktGetBits(pak, 32);
    costume->appearance.convertedScale        = pktGetBits(pak,1);
    costume->appearance.currentSuperColorSet = pktGetBits(pak, 3);
    hasExtraInfo                            = pktGetBits( pak, 1 );

    for (i = 0; i < NUM_SG_COLOR_SLOTS; i++)
    {
        costume->appearance.superColorsPrimaryU[i].SGBitSetLow = pktGetBits(pak, 32);
        costume->appearance.superColorsPrimaryU[i].SGBitSetHigh = pktGetBits(pak, 32);
        costume->appearance.superColorsSecondaryU[i].SGBitSetLow = pktGetBits(pak, 32);
        costume->appearance.superColorsSecondaryU[i].SGBitSetHigh = pktGetBits(pak, 32);
        costume->appearance.superColorsPrimary2U[i].SGBitSetLow = pktGetBits(pak, 32);
        costume->appearance.superColorsPrimary2U[i].SGBitSetHigh = pktGetBits(pak, 32);
        costume->appearance.superColorsSecondary2U[i].SGBitSetLow = pktGetBits(pak, 32);
        costume->appearance.superColorsSecondary2U[i].SGBitSetHigh = pktGetBits(pak, 32);
        costume->appearance.superColorsTertiaryU[i].SGBitSetLow = pktGetBits(pak, 32);
        costume->appearance.superColorsTertiaryU[i].SGBitSetHigh = pktGetBits(pak, 32);
        costume->appearance.superColorsQuaternaryU[i].SGBitSetLow = pktGetBits(pak, 32);
        costume->appearance.superColorsQuaternaryU[i].SGBitSetHigh = pktGetBits(pak, 32);
    }


    for(i=0;i<MAX_BODY_SCALES;i++) {
        if (i==0 || hasExtraInfo) {
            costume->appearance.fScales[i]    = pktGetF32(pak);
        } else {
            costume->appearance.fScales[i]    = pktGetF(pak, 6, -1, 1);
        }
    }

    if (pktGetBits(pak, 1)) {
        costume->appearance.iNumParts        = pktGetBitsPack(pak, 4);
    } else {
        costume->appearance.iNumParts        = GetBodyPartCount();
    }

    if (costume->appearance.bodytype >= getBodyTypeCount())
    {
#if SERVER
        LOG_ENT(NULL, LOG_ENTITY, LOG_LEVEL_IMPORTANT, 0, "costume_Validate Character Creation Failed: Invalid body type( %d )", costume->appearance.bodytype );
#endif
        return 0;
    }

    if( costume->appearance.iNumParts > GetBodyPartCount() )
    {
#if SERVER
        LOG_ENT(NULL, LOG_ENTITY, LOG_LEVEL_IMPORTANT, 0, "costume_Validate Character Creation Failed: Wrong too many parts( %d )", costume->appearance.iNumParts );
#endif
        return 0;
    }

     for(i=0; i < costume->appearance.iNumParts; i++)
    {
        costume->parts[i]->pchGeom = getCachedIndexedString(pak);
        costume->parts[i]->pchTex1 = getCachedIndexedString(pak);
        costume->parts[i]->pchTex2 = getCachedIndexedString(pak);
        costume->parts[i]->pchFxName = getCachedIndexedString(pak);

        count = num_colors_lookup[pktGetBits(pak, 1)];
        for (j=0; j<ARRAY_SIZE(costume->parts[i]->color); j++) {
            if (j < count)
                costume->parts[i]->color[j].integer = getCachedIndexedColor(pak);
            else
                costume->parts[i]->color[j].integer = 0;
        }

        if( hasExtraInfo )
        {
            costume->parts[i]->displayName = "None";
//            costume->parts[i]->displayName = (char*)pktGetIndexedString(pak, costume_HashTableExtraInfo);
            costume->parts[i]->regionName = pktGetIndexedString(pak, costume_HashTableExtraInfo);
            costume->parts[i]->bodySetName = pktGetIndexedString(pak, costume_HashTableExtraInfo);
        }
    }

    return 1;
}
#endif
