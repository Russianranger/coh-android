"""Raw dynamic source producer fixture projections; no authenticated world count."""
def build(proof):
 lines=[];rows=[];expected={}
 for c in proof['cases']:
  e=c['expected'];key=c['scenario']
  if key not in expected:
   name='expected_'+str(len(expected));expected[key]=name;fields=['.modified_count='+str(e['modified_count']),'.expected_count='+str(c['expected_world_count'])]
   if 'status' in e:
    fields+=['.raw_bytes='+str(e['raw_bytes']),'.full_status={'+','.join(str(hp|(repair<<7)) for hp,repair in e['status'])+'}'] if e['status'] else ['.raw_bytes=0']
   elif e['delta']:fields.append('.deltas={'+','.join('{'+','.join(map(str,row))+'}' for row in e['delta'])+'}')
   lines.append('static const CohDynamicDiagnostic '+name+'={'+','.join(fields)+'};')
  data=bytes.fromhex(c['wire_hex']);name='wire_'+str(len(rows));lines.append('static const uint8_t '+name+'[]={'+','.join(map(str,data))+'};');rows.append('{'+name+',sizeof('+name+'),'+','.join(map(str,[c['begin_bit'],c['end_bit'],c['aligned'],c['scenario'],c['expected_world_count']]))+',&'+expected[key]+'}')
 return '\n'.join(lines)+'\nstatic const Fixture fixtures[]={'+',\n'.join(rows)+'};\n'
