/* Test-only owner/earray shells. Original grammar functions are extracted
 * unchanged; no game dictionaries, power eligibility or UI are implemented. */
#include <stddef.h>
typedef struct { int size; int values[COH_GLOBAL_POWER_MODE_MAX+1]; } OracleModes;
typedef struct { int *pPowerModes; } Character;
typedef struct { Character *pchar; int power_modes_update; } Entity;
static OracleModes *array_owner(int **values) {
    return (OracleModes *)((unsigned char *)*values - offsetof(OracleModes,values));
}
static int eaiSize(int **values) { return array_owner(values)->size; }
static void eaiSetSize(int **values,int count) {
    assert(count>=0 && count<=COH_GLOBAL_POWER_MODE_MAX+1);
    array_owner(values)->size=count;
}
static void eaiPush(int **values,int value) {
    OracleModes *array=array_owner(values);
    assert(array->size<COH_GLOBAL_POWER_MODE_MAX+1);
    array->values[array->size++]=value;
}
