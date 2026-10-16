#include "coh_costume.h"
#include "coh_taskforce.h"
/* C++ integration smoke: references every public costume/power API so missing
 * C linkage is caught at link time. Full parser behavior is tested in C99. */
int main() {
    CohEntCostumeDictionary *dictionary = nullptr;
    if (coh_ent_costume_dictionary_load(&dictionary, nullptr, 0, nullptr) != COH_STATE) return 1;
    if (coh_ent_costume_dictionary_bytes(dictionary) != 0) return 2;
    coh_ent_costume_dictionary_free(dictionary);
    if (coh_ent_costume(nullptr, nullptr, 0, nullptr, nullptr, nullptr) != COH_INVALID) return 3;
    if (coh_ent_custom_costume(nullptr, nullptr, nullptr) != COH_INVALID) return 4;
    if (coh_ent_costume_envelope(nullptr, nullptr, 0, 0, nullptr, nullptr, nullptr) != COH_INVALID) return 5;
    if (coh_ent_power_custom(nullptr, 0, nullptr, nullptr, nullptr) != COH_INVALID) return 6;
    if (coh_ent_taskforce(nullptr, nullptr, 0, nullptr, nullptr, nullptr) != COH_INVALID) return 7;
    return 0;
}
