"""Exact producer raw supergroup projections, with absent fields zeroed."""
import json
def build(proof):
 lines=[];rows=[];expected={}
 for case in proof['cases']:
  e=case['expected'];key=case['scenario']
  if key not in expected:
   name='expected_'+str(len(expected));expected[key]=name;fields=['.count='+str(e['count'])]
   for field in ['financial','update','colors_tithe_spaces','demote_timeout','entry_permission','alliance_min_talk_rank']:
    if field in e:fields.append('.'+field+'='+('{'+','.join(map(str,e[field]))+'}' if isinstance(e[field],list) else str(e[field])))
   if 'members' in e:
    members=[]
    for m in e['members']:members.append('{'+','.join('.'+n+'='+(json.dumps(v) if isinstance(v,str) else str(v)) for n,v in m.items())+'}')
    fields.append('.members={'+','.join(members)+'}')
    for n,v in zip(['name','motto','message','emblem','description'],e['strings']):fields.append('.'+n+'='+json.dumps(v))
    fields.append('.ranks={'+','.join('{.name='+json.dumps(r['name'])+',.permission_bytes={'+','.join(map(str,r['permission_bytes']))+'}}' for r in e['ranks'])+'}')
    fields.append('.memberrank_count='+str(len(e['memberranks'])))
    if e['memberranks']:fields.append('.memberranks={'+','.join('{'+','.join(map(str,r))+'}' for r in e['memberranks'])+'}')
    fields.append('.allies={'+','.join('{'+','.join('.'+n+'='+(json.dumps(v) if isinstance(v,str) else str(v)) for n,v in ally.items())+'}' for ally in e['allies'])+'}')
   lines.append('static const CohSuperStats '+name+'={'+','.join(fields)+'};')
  data=bytes.fromhex(case['wire_hex']);name='wire_'+str(len(rows));lines.append('static const uint8_t '+name+'[]={'+','.join(map(str,data))+'};');rows.append('{'+name+',sizeof('+name+'),'+','.join(map(str,[case['begin_bit'],case['end_bit'],case['aligned'],case['scenario']]))+',&'+expected[key]+'}')
 return '\n'.join(lines)+'\nstatic const Fixture fixtures[]={'+',\n'.join(rows)+'};\n'
