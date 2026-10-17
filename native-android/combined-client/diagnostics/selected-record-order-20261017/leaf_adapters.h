typedef uint16_t U16;
typedef struct{const void*ppowBase;}LeafStance;
typedef struct{LeafStance*ppowStance;int*piStickyAnimBits;}LeafSeqCharacter;
typedef struct{unsigned sticky_state[8];}LeafSequence;
typedef struct{LeafSeqCharacter*pchar;LeafSequence*seq;int move_idx,net_move_change_time;}LeafSeqEntity;
typedef struct{int*piModeBits;}PowerFX;
static const PowerFX*power_GetFX(LeafStance*p){(void)p;assert(0);return NULL;}
static int leaf_seq_count;
static int leaf_eaiSize(int*const*p){assert((*p!=NULL)==(leaf_seq_count!=0));return leaf_seq_count;}
#define eaiSize leaf_eaiSize
#define SAFE_MEMBER2(p,m,n) ((p)&&(p)->m&&(p)->m->n)
/* STATUS_ADAPTERS */
typedef struct{float fHeld,fStunned,fSleep,fTerrorized,fImmobilized,fConfused,fOnlyAffectsSelf,fMeter,fPerceptionRadius;}LeafStatusAttributes;
typedef struct{int identity;}CharacterClass;
typedef struct{float fMagnitude;}LeafStatusMod;
typedef struct{unsigned bitfieldVisionPhases,exclusiveVisionPhase;}LeafStatusParent;
typedef struct{LeafStatusAttributes attrCur,attrMod;CharacterClass*pclass;LeafStatusMod*pmodTaunt;LeafStatusParent*entParent;char**designerStatuses;}LeafStatusCharacter;
static CharacterClass leaf_classes[3];static int g_CharacterClasses;
static LeafStatusAttributes g_attrModBase;
static const CharacterClass*classes_GetPtrFromName(int*g,const char*name){assert(g==&g_CharacterClasses);if(!strcmp(name,"Class_Stalker"))return leaf_classes;if(!strcmp(name,"Class_Arachnos_Widow"))return leaf_classes+1;if(!strcmp(name,"Class_Arachnos_Soldier"))return leaf_classes+2;assert(0);return NULL;}
#define ATTRIB_GET_PTR(p,o) ((float*)((char*)(p)+(o)))
static int leaf_designer_count;
#define eaSize(p) (leaf_designer_count)
