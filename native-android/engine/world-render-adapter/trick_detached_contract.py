"""Mechanical private decoder/getter slices of frozen whole-cache Trick reader."""
from pathlib import Path

def core(root,extract):
 s=(Path(root)/'native-android/engine/world-render-adapter/coh_wr_trick.c').read_text();pieces=[s[s.index('#define COUNT'):s.index('typedef struct{uint32_t name,length,stamp;}FileRow;')]]
 pieces.append(s[s.index('typedef struct{uint32_t offset,size,name,'):s.index('struct CohWrTrickCache{')])
 pieces.append(s[s.index('typedef struct{CohBytes bytes;'):s.index('static int apart(')])
 names=['static int apart(','static int add(','static int stop(','static unsigned fold(','static int compare(','static int take(','static int word(','static int string(','static int ascii(','static CohStatus table(','static CohBytes name(','static int order(','static void sift(','static uint32_t winner(','static int output(']
 pieces.append('#include "coh_wr_trick_detached_storage_internal.h"\n')
 pieces += [extract(s,n) for n in names]
 pieces.append('#pragma GCC diagnostic push\n#pragma GCC diagnostic ignored "-Wunused-variable"\n#pragma GCC diagnostic ignored "-Wunused-parameter"\n#include "coh_wr_trick_post_source.inc"\n#pragma GCC diagnostic pop\n')
 pieces += [extract(s,n) for n in ['static CohStatus view(','CohStatus coh_wr_trick_view(','CohStatus coh_wr_trick_numeric_projection(','CohStatus coh_wr_trick_find(','static CohStatus child(','CohStatus coh_wr_trick_stanim(','CohStatus coh_wr_trick_autolod(']]
 text='\n'.join(pieces).replace('CohWrTrickCache','CohWrTrickDetached').replace('coh_wr_trick_','coh_wr_trick_detached_').replace('coh_wr_trick_detached_post_source.inc','coh_wr_trick_post_source.inc').replace('coh_wr_trick_detached_tables_internal.inc','coh_wr_trick_tables_internal.inc').replace('coh_wr_trick_detached_detached_storage_internal.h','coh_wr_trick_detached_storage_internal.h').replace('coh_asset_bytes(c->blob)','c->bytes')
 return '/* Mechanical frozen-reader slices; exact transformation checked by qualifier. */\n'+text
