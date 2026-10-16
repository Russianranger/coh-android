#include "../../replication/coh_replication.h"
#include <stddef.h>
#include <string.h>
CohStatus __real_coh_rep_reader_bounded(CohRepReader *,CohBytes,size_t,int,size_t);
CohStatus __wrap_coh_rep_reader_bounded(CohRepReader *r,CohBytes b,size_t bits,int compressed,size_t max_bytes){
    static unsigned calls;
    CohStatus status=__real_coh_rep_reader_bounded(r,b,bits,compressed,max_bytes);
    /* Only padding between unsigned compressed and size_t max_bytes changes.
     * Every member value remains that produced by the real initializer. */
    if(status==COH_OK){size_t first=offsetof(CohRepReader,compressed)+sizeof(r->compressed),last=offsetof(CohRepReader,max_bytes);memset((unsigned char *)r+first,++calls&255u,last-first);}
    return status;
}
