/* Call-through observation around unchanged source body receiver: records only
 * destination and ending offset, and does not decode any field itself. */
static struct {Costume *body;size_t end;} body_receipts[12];static unsigned body_receipt_count;
static int observed_costume_receive(Packet *p,Costume *c){int r=costume_receive(p,c);assert(body_receipt_count<12);body_receipts[body_receipt_count].body=c;body_receipts[body_receipt_count++].end=bsGetCursorBitPosition(&p->stream);return r;}
#define costume_receive observed_costume_receive
static void expected_costume(CohEntCostume *r,Costume *c,unsigned extra,size_t end){
 r->generation=9;memset(r->manifest_sha256,0x42,32);expected_text(&r->entity_type_file,c->appearance.entTypeFile);expected_text(&r->prefix,c->appearance.costumeFilePrefix);
 r->body_type=c->appearance.bodytype;r->skin_color=c->appearance.colorSkin.integer;r->converted_scale=c->appearance.convertedScale;r->super_color_set=c->appearance.currentSuperColorSet;r->extra_info=extra;
 for(unsigned i=0;i<6;i++){
  SGColorBits *g[]={c->appearance.superColorsPrimaryU,c->appearance.superColorsSecondaryU,c->appearance.superColorsPrimary2U,c->appearance.superColorsSecondary2U,c->appearance.superColorsTertiaryU,c->appearance.superColorsQuaternaryU};
  for(unsigned j=0;j<6;j++){r->super_colors[i][j*2]=g[j][i].SGBitSetLow;r->super_colors[i][j*2+1]=g[j][i].SGBitSetHigh;}
 }
 memcpy(r->scales,c->appearance.fScales,sizeof(r->scales));r->part_count=c->appearance.iNumParts;
 for(unsigned i=0;i<r->part_count;i++){
  CohEntCostumePart *d=&r->parts[i];CostumePart *s=c->parts[i];
  expected_text(&d->geometry,s->pchGeom);expected_text(&d->texture1,s->pchTex1);expected_text(&d->texture2,s->pchTex2);expected_text(&d->fx,s->pchFxName);expected_text(&d->region,s->regionName);expected_text(&d->body_set,s->bodySetName);for(unsigned j=0;j<4;j++)d->colors[j]=s->color[j].integer;
 }
 r->end_bit=end;
}
