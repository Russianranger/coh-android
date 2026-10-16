/* Compile the existing controller unchanged. Compatibility headers below are
 * visible only to this translation unit, never the renderer or accepted APK. */
#define COH_WRAP_LOGIN 1
#include "winsock_compat.h"
#include "../../../login/coh_login.c"
