/* Standalone diagnostic bridge. Compile INSTEAD OF coh_scenegraph.c. Including
 * the exact qualified implementation keeps its private matrix grammar intact;
 * no production header, implementation or application linkage is changed. */
#include "../coh_scenegraph.c"
CohStatus coh_runtime_matrix_read(CohRepReader *reader,CohSgMatrix out)
{
    if(!reader||!out)return COH_INVALID;
    Build b={0};CohSgMatrix candidate;b.r=*reader;
    CohStatus status=matrix(&b,candidate);
    if(status!=COH_OK)return status;
    *reader=b.r;memcpy(out,candidate,sizeof(candidate));return COH_OK;
}
