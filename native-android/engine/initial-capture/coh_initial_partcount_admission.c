#include "coh_initial_partcount_admission.h"
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 1;
 return x<y+bn&&y<x+an;
}
static CohStatus finish(CohInitialCountAdmission*out,CohInitialCountAdmission*d,
 CohStatus status,size_t bit){d->status=status;d->failure_bit=bit;*out=*d;return status;}
CohStatus coh_initial_partcount_admission(const CohRepReader*input,
 const CohCostumeOwner*owner,const CohCostumePacketBinding*binding,CohInitialCountAdmission*out){
 if(!input||!binding||!out||overlap(input,sizeof(*input),out,sizeof(*out))||
    overlap(binding,sizeof(*binding),out,sizeof(*out))||
    overlap(input,sizeof(*input),binding,sizeof(*binding)))return COH_INVALID;
 if(coh_costume_owner_output_disjoint(owner,out,sizeof(*out))!=COH_OK)return COH_INVALID;
 CohRepReader r=*input;uint32_t unused=0;
 if(coh_rep_read(&r,0,&unused)!=COH_OK||r.bytes.size>COH_REP_BOUNDED_MESSAGE_MAX||
    overlap(r.bytes.data,r.bytes.size,input,sizeof(*input))||
    overlap(r.bytes.data,r.bytes.size,binding,sizeof(*binding))||
    overlap(r.bytes.data,r.bytes.size,out,sizeof(*out)))return COH_INVALID;
 CohInitialCountAdmission d;memset(&d,0,sizeof(d));d.begin_bit=r.cursor;
 d.stage=COH_INITIAL_COUNT_ADMISSION_INPUT;
 if(binding->packet.data!=r.bytes.data||binding->packet.size!=r.bytes.size||
    binding->bit_length!=r.bits||binding->compressed!=r.compressed)
  return finish(out,&d,COH_STATE,r.cursor);
 d.stage=COH_INITIAL_COUNT_ADMISSION_APPEARANCE;
 CohInitialAppearanceProbe a={0};CohStatus s=coh_initial_appearance_probe(&r,&a);
 if(!a.scalars_validated)return finish(out,&d,s,a.failure_bit);
 uint32_t bodytype=0;
 if(coh_rep_pack(&r,6,&bodytype)!=COH_OK)return finish(out,&d,COH_INVALID,r.cursor);
 r.cursor=a.end_bit;
 d.stage=COH_INITIAL_COUNT_ADMISSION_SGCOLORS;
 CohInitialSgcolorsProbe g={0};s=coh_initial_sgcolors_probe(&r,&g);
 if(!g.array_validated)return finish(out,&d,s,g.failure_bit);
 r.cursor=g.end_bit;
 d.stage=COH_INITIAL_COUNT_ADMISSION_SCALES;
 CohInitialScalesProbe f={0};s=coh_initial_scales_probe(&r,&f);
 if(!f.scales_validated)return finish(out,&d,s,f.failure_bit);
 r.cursor=f.end_bit;d.count_begin_bit=r.cursor;
 d.stage=COH_INITIAL_COUNT_ADMISSION_FRAMING;
 CohInitialPartcountProbe p={0};s=coh_initial_partcount_probe(&r,&p);
 if(!p.framing_validated)return finish(out,&d,s,p.failure_bit);
 d.end_bit=p.end_bit;d.explicit_count=p.explicit_count;
 d.stage=p.explicit_count?COH_INITIAL_COUNT_ADMISSION_EXPLICIT_CATALOG:
                         COH_INITIAL_COUNT_ADMISSION_DEFAULT_CATALOG;
 uint32_t parts=0,types=0;s=coh_costume_owner_query(owner,binding,&parts,&types);
 if(s!=COH_OK)return finish(out,&d,s,p.end_bit);
 /* Even a qualified provider may not widen the native bounded profile. */
 if(!parts||!types||parts>COH_COSTUME_PART_MAX||types>64u)
  return finish(out,&d,COH_LIMIT,p.end_bit);
 d.stage=COH_INITIAL_COUNT_ADMISSION_BODYTYPE;
 if(bodytype>=types)return finish(out,&d,COH_LIMIT,p.end_bit);
 d.stage=COH_INITIAL_COUNT_ADMISSION_COUNT;
 uint32_t count=p.explicit_count?p.part_count:parts;
 if(count>parts)return finish(out,&d,COH_LIMIT,p.end_bit);
 d.part_count=count;d.catalog_validated=1;d.stage=COH_INITIAL_COUNT_ADMISSION_PART_BODY;
 return finish(out,&d,COH_UNSUPPORTED,p.end_bit);
}
