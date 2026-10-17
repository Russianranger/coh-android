/* Shared bounded source selection; instantiated only inside admitted owners. */
_Static_assert(2*sizeof(CohWrTrickModelSelection)+2*sizeof(CohWrTrickModelQuery)+2*sizeof(CohWrTrickModelLimits)+520+1024<COH_WR_TRICK_MODEL_QUERY_RESERVE,"bounded query, result, strings and own control reserve");
static CohStatus model_query_string(const char*s,int nonempty,size_t*out){
 if(!s)return COH_INVALID;
 for(size_t n=0;n<260;n++){
  unsigned x=(unsigned char)s[n];
  if(!x){if(nonempty&&!n)return COH_INVALID;*out=n;return COH_OK;}
  if(x<32||x>126)return COH_UNSUPPORTED;
 }
 return COH_LIMIT;
}
CohStatus MODEL_SELECT_FUNCTION(const MODEL_SELECT_OWNER*c,const CohWrTrickModelQuery*q,const CohWrTrickModelLimits*l,CohWrTrickModelSelection*out){
 if(!c||!q||!l||!out||!output(c,out,sizeof(*out))||!apart(q,sizeof(*q),out,sizeof(*out))||!apart(l,sizeof(*l),out,sizeof(*out)))return COH_INVALID;
 if(q->report_missing_suffix>1)return COH_INVALID;
 size_t minimum=MODEL_SELECT_OWNED(c);
 if(!add(&minimum,MODEL_SELECT_LOADER(c))||l->external_bytes<minimum)return COH_LIMIT;
 size_t aggregate=l->external_bytes;
 if(!add(&aggregate,COH_WR_TRICK_MODEL_QUERY_RESERVE)||aggregate>l->aggregate_limit)return COH_LIMIT;
 size_t name_length,path_length;CohStatus status=model_query_string(q->model_name,1,&name_length);
 if(status!=COH_OK)return status;
 status=model_query_string(q->source_geo_path,0,&path_length);if(status!=COH_OK)return status;
 if(!apart(q->model_name,name_length+1,out,sizeof(*out))||!apart(q->source_geo_path,path_length+1,out,sizeof(*out)))return COH_INVALID;
 CohWrTrickModelSelection result;memset(&result,0,sizeof(result));
 const char*suffix=strstr(q->model_name,"__");
 const char*key=suffix?suffix+2:q->model_name;size_t length=name_length-(size_t)(key-q->model_name);
 memcpy(result.lookup_key,key,length);result.lookup_key[length]=0;
 result.branch=suffix?COH_WR_TRICK_MODEL_FIRST_SUFFIX:COH_WR_TRICK_MODEL_WHOLE_NAME;
 result.source_ordinal=winner(c,(CohBytes){(const uint8_t*)key,length});
 result.matched=result.source_ordinal!=UINT32_MAX;
 if(suffix&&!result.matched&&q->report_missing_suffix)
  result.source_diagnostic=path_length?COH_WR_TRICK_MODEL_FILENAME_DIAGNOSTIC:COH_WR_TRICK_MODEL_GENERIC_DIAGNOSTIC;
 result.historical_input_generation=c->report.historical_input_generation;
 memcpy(result.cache_sha256,c->report.cache_sha256,32);result.aggregate_reserved_bytes=aggregate;
 *out=result;return COH_OK;
}
#undef MODEL_SELECT_FUNCTION
#undef MODEL_SELECT_OWNER
#undef MODEL_SELECT_OWNED
#undef MODEL_SELECT_LOADER
