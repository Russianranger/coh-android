int original_tree_roundtrip(const unsigned char*input,unsigned size,unsigned begin,unsigned char*out,unsigned cap,unsigned*stats,unsigned char*digest,unsigned scenario){
 SimpleBuffer in={0},wr={0};CostumeMasterList tree={0};int sum=0,ok;assert(size<=32u*1024u*1024u&&begin<size&&cap<=32u*1024u*1024u);reset();
 in.data=(char*)input;in.filesize=size;in.capacity=size;in.curposition=begin;ok=ParserReadBinaryTable(&in,ParseCostumeSet,&tree,&sum);
 if(!ok||in.curposition!=(int)size){reset();return 0;}
 stats[0]=(unsigned)in.curposition;stats[1]=(unsigned)memory_peak;stats[2]=total_allocations;stats[3]=eaSize(&tree.bodySet);
 assert(scenario<=1);if(scenario){assert(eaSize(&tree.bodySet)>0);((CostumeBodySet*)tree.bodySet[0])->name="DiagnosticBody";}
 memset(project_counts,0,sizeof(project_counts));SHA256_Init(&project_hash);project_tree(ParseCostumeSet,&tree,0);SHA256_Final(digest,&project_hash);memcpy(stats+5,project_counts,sizeof(project_counts));
 wr.data=(char*)out;wr.capacity=cap;wr.filesize=begin;wr.curposition=begin;memcpy(wr.data,input,begin);sum=0;ok=ParserWriteBinaryTable(&wr,ParseCostumeSet,&tree,&sum,0,0);stats[4]=wr.filesize;
 reset();return ok;
}
