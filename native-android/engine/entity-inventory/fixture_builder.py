"""Expected metadata comes from independent unchanged-source oracles only."""
def bytes_c(raw):return '{'+','.join(map(str,raw))+'}'
def inventory(proof):
 lines=[];rows=[];expected={}
 for i,f in enumerate(proof['cases']):
  scenario=f['scenario'];v=f['expected'];name='inventory_'+str(i)
  if scenario not in expected:
   expected[scenario]=v;items=v['items'];lines.append('static const uint32_t inventory_items_'+str(scenario)+'[][8]={' +(','.join('{'+','.join(map(str,row))+'}' for row in items) if items else '{0}')+'};')
  elif expected[scenario]!=v:raise ValueError('inventory source changes by alignment')
  raw=bytes.fromhex(f['wire_hex']);lines.append('static const uint8_t '+name+'[]='+bytes_c(raw)+';');rows.append('{'+name+',sizeof('+name+'),'+','.join(str(f[n]) for n in ['begin_bit','end_bit','aligned','scenario'])+','+str(len(v['items']))+','+str(v['auction_updated'])+',inventory_items_'+str(scenario)+','+bytes_c(v['auction_text'].encode()+b'\0')+'}')
 lines.append('static const InventoryFixture inventory_fixtures[]={'+',\n'.join(rows)+'};');return '\n'.join(lines)+'\n'
def invention_initializer(e):
 fields={'status_change':str(e['status_change']),'original_consumer_compatible':str(int(not e['status_change']))};concepts=[];slots=[]
 if e['status_change']:
  fields['state']=str(e['state'])
  if e['state']:
   fields['recipe_id']=str(e['recipe']);fields['boost_inventory_index']=str(e['boost_index']);fields['variable_words']='{'+','.join(map(str,e['vars']))+'}';fields['powerups']='{'+','.join('{'+','.join(map(str,row))+'}' for row in e['powerups'])+'}'
   for slot in e['slots']:
    begin=len(concepts)
    for item in slot['concepts']:concepts.append('{'+str(item[0])+',{'+','.join(map(str,item[1:]))+'}}')
    slots.append('{'+','.join(map(str,[slot['state'],begin,len(slot['concepts'])]))+'}')
   fields['slots']='{'+','.join(slots)+'}';fields['concept_count']=str(len(concepts));fields['concepts']='{'+','.join(concepts)+'}'
 return '{'+','.join('.'+n+'='+v for n,v in fields.items())+'}'
def invention(proof):
 lines=[];rows=[];expected={}
 for i,f in enumerate(proof['cases']):
  scenario=f['scenario'];v=f['expected'];name='invention_'+str(i)
  if scenario not in expected:expected[scenario]=v;lines.append('static const CohInventionUpdate invention_expected_'+str(scenario)+'='+invention_initializer(v)+';')
  elif expected[scenario]!=v:raise ValueError('invention source changes by alignment')
  raw=bytes.fromhex(f['wire_hex']);lines.append('static const uint8_t '+name+'[]='+bytes_c(raw)+';');rows.append('{'+name+',sizeof('+name+'),'+','.join(str(f[n]) for n in ['begin_bit','end_bit','consumer_end_bit','aligned','scenario'])+',&invention_expected_'+str(scenario)+'}')
 lines.append('static const InventionFixture invention_fixtures[]={'+',\n'.join(rows)+'};');return '\n'.join(lines)+'\n'
