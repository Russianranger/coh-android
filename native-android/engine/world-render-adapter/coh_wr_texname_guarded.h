#ifndef COH_WR_TEXNAME_GUARDED_H
#define COH_WR_TEXNAME_GUARDED_H
#include "coh_wr_texname.h"
/* Explicit separately qualified repaired-source policy. Strict default and its
 * source bytes remain unchanged. Sole behavioral expansion: otherwise-bare
 * 4..7-byte composite keys retain their original bytes rather than executing
 * original texFixName's out-of-bounds res[-8] access. Corrected-original oracle
 * provenance is mandatory for this policy; these are not unchanged-source cases.
 * Existing ASCII/name/key/swap bounds, aliases and atomic refusals still apply.
 * No table contents, white fallback, asset/material/generation permit is supplied. */
CohStatus coh_wr_texname_project_guarded(const CohWrTexNameInput*,CohWrTexNameProjection*);
#endif
