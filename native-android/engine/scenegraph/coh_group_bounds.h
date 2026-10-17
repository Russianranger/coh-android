#ifndef COH_GROUP_BOUNDS_H
#define COH_GROUP_BOUNDS_H
#include <stddef.h>
#include <stdint.h>
/* Pure source-qualified numerical kernel. No graph/resource admission is implied. */
typedef struct CohGroupBounds { float min[3], max[3], mid[3], radius; } CohGroupBounds;
typedef struct CohGroupBoundsChild {
    const CohGroupBounds *bounds; /* NULL preserves original absent-child semantics. */
    float matrix[4][3]; /* Original column-major Mat4: last column is translation. */
} CohGroupBoundsChild;
typedef struct CohGroupBoundsInput {
    uint32_t model_present, has_volume, pre_alloc;
    float model_min[3], model_max[3], box_scale[3];
    const CohGroupBoundsChild *children;
    size_t child_count;
    int (*cancelled)(void *context); /* Optional; nonzero aborts before publication. */
    void *context;
} CohGroupBoundsInput;
typedef enum CohGroupBoundsStatus {
    COH_GROUP_BOUNDS_OK = 0,
    COH_GROUP_BOUNDS_INVALID = 1,
    COH_GROUP_BOUNDS_LIMIT = 2,
    COH_GROUP_BOUNDS_CANCELLED = 3,
    COH_GROUP_BOUNDS_PREALLOC = 4
} CohGroupBoundsStatus;
#define COH_GROUP_BOUNDS_MAX_CHILDREN 262144u
/* Input spans must remain immutable for this synchronous call. No heap allocation.
 * Output is unchanged on refusal. Caller owns/charges input and output storage.
 * pre_alloc requires captured source bounds; this kernel never reconstructs it.
 * Does not set source bounds_valid, recurse, load models, or establish authority. */
CohGroupBoundsStatus coh_group_bounds_compute(const CohGroupBoundsInput *, CohGroupBounds *);
#endif
