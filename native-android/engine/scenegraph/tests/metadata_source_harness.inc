/* Trusted original sendDef input variations; function body remains unchanged.
 * Expected values are read directly from these source structs independently
 * after serialization. This does not execute receiveDef or client loaders. */
static GroupDef *metadata_definition;
int metadata_original(U32 which,U32 aligned,U8 *out,U32 *bits){
 U32 footer[4];if(which>6||!groups_original(2,aligned,0,out,bits,footer))return 0;
 GroupDef *d=&oracle_defs[0];
 if(which==1)oracle_simple(d,0,"oracle_plain_metadata");
 if(which>=2&&which<=4){
  if(!groups_original(9,aligned,0,out,bits,footer))return 0;
  d=&oracle_defs[which-2];
 }
 if(which==5){d->has_light=1;d->light_radius=0;d->sound_script_filename="";d->has_alpha=1;d->groupdef_alpha=0;}
 if(which==6){strcpy(oracle_prop_entries[0][0].name_str,"TexWordLayout");oracle_prop_entries[0][0].value_str="layouts/original_fixture.texword";}
 metadata_definition=d;Packet *p=pktCreate();sendDef(p,d);
 *bits=p->stream.bitLength;memcpy(out,p->stream.data,(*bits+7)/8);return 1;
}
