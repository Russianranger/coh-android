#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
typedef float Vec3[3];
typedef struct BasePower { int id; } BasePower;
typedef struct PowerFX { int unused; } PowerFX;
typedef struct FxKey { int unused; } FxKey;
typedef struct Entity { int db_id; struct { struct { int bodytype; } appearance; } *costume; } Entity;
typedef struct PowerAnimEvent { int type; float time; } PowerAnimEvent;
enum { MENU_POWER_CUST = 24, POWERCUSTSET_COUNT = 3, POWERANIM_END, POWERANIM_LOOP,
       HYBRID_MENU_TAILOR, SHOW_TEMPLATE, POWERCUST_LINKED_COLORS_NONE };
#define CURRENT_POWER_CUST_MENU (current_menu() - MENU_POWER_CUST)
static const BasePower *sSelectedPowers[POWERCUSTSET_COUNT];
static const BasePower *queued, *observed;
static BasePower powers[3] = {{1}, {2}, {3}};
static PowerAnimEvent gAnimQueue[4];
static Entity player;
static int menu, nextMenu, queues, clears, gZoomedInForPowers, repositioningCamera;
static int s_outOfDate, gPowerColorsLinked, toolTipMatchPowerset, toolTipMatchAll, gCurrentGender;
static bool menuInitialized, gLoopNow;
static void *gCopyOfPowerCustList, *gOwnedCostume, *ZOOMED_OUT_POSITION;
static int current_menu(void) { return menu; }
static Entity *playerPtr(void) { return &player; }
static Entity *playerPtrForShell(int a) { return &player; }
static int playerTurn_GetTicks(void) { return 0; }
static void playerTurn(int n) {}
static void *avatar_getDefaultPosition(int a, int b) { return NULL; }
static void zoomAvatar(bool a, void *b) {}
static void resetCustomPowers(Entity *e) {}
static void randomizePowerCustColors(void) {}
static void initializeTokens(void) {}
static void costume_Apply(Entity *e) {}
static void addToolTip(int *t) {}
static int getLastNavMenuType(void) { return 0; }
static void costumeInit(void) {}
static void setDefaultCostume(bool a) {}
static void clearSS(void) {}
static void toggle_3d_game_modes(int a) {}
static int checkCostumeMatchesBody(int a, int b) { return 1; }
static void clearPowerCustomizationAnimation(void) { ++clears; }
static void compressAnimationQueue(void) {}
static void insertAnimEvent(PowerAnimEvent *e) {}
static void armportSelectedPowerTrace(const char *s, int m, const BasePower *p, const BasePower *a) {}
static PowerAnimEvent *createPowerAnimationEvents(PowerAnimEvent *e, Entity *p, const BasePower *power, float t)
{ ++queues; queued = power; return e; }
static const PowerFX *getSelectedPowerFX(const BasePower *p) { observed = p; return NULL; }
void restartPowerCustomizationAnimation(void);
void resetPowerCustomizationPreview(void);
/* SOURCE_FUNCTIONS */
int main(int argc, char **argv)
{
    int old = atoi(argv[1]), target = atoi(argv[2]), empty = atoi(argv[3]);
    struct { struct { int bodytype; } appearance; } costume = {{0}};
    player.costume = (void *)&costume;
    for (int i = 0; i < 3; ++i) sSelectedPowers[i] = empty ? NULL : &powers[i];
    menu = old;
    /* hybrid_start_menu invokes the entry callback while current_menu is old;
     * start_menu only assigns gNextMenu, committed by serve_menus next frame. */
    powerCustMenuEnter();
    nextMenu = target;
    assert(menu == old && queues == 0 && observed == NULL && gLoopNow);
    menu = nextMenu;
    powerCust_handleAnimation();
    assert(menuInitialized && !gLoopNow && clears == 2);
    assert(observed == sSelectedPowers[target - MENU_POWER_CUST]);
    assert(queues == !empty && queued == observed);
    powerCust_handleAnimation();
    assert(queues == !empty && clears == 2);
    puts("destination selection preserved");
    return 0;
}
