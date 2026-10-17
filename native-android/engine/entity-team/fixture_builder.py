"""Exact raw team/league fixture projections; no original applied-state authority."""
import json
def build(proof):
 lines=[];rows=[];expected={}
 for case in proof['cases']:
  e=case['expected'];key=(case['kind'],case['scenario']);kind=int(case['kind']=='league')
  if key not in expected:
   name='expected_'+str(len(expected));expected[key]=name
   fields=['.league='+str(kind),'.identity_present='+str(int(bool(e['id']))),'.id='+str(e['id'])]
   for field in ['taskforce','lfg','leader','level','mentor','active']:
    if field in e:fields.append('.'+field+'='+str(e[field]))
   fields.append('.count='+str(len(e['members'])));members=[]
   for row in e['members']:
    item=[]
    for src,dst in [('dbid','dbid'),('onmap','on_map'),('changed','changed'),('name','name'),('map','map'),('team_leader','team_leader'),('locked','locked')]:
     if src in row:item.append('.'+dst+'='+ (json.dumps(row[src]) if isinstance(row[src],str) else str(row[src])))
    members.append('{'+','.join(item)+'}')
   if members:fields.append('.members={'+','.join(members)+'}')
   lines.append('static const CohTeamList '+name+'={'+','.join(fields)+'};')
  data=bytes.fromhex(case['wire_hex']);name='wire_'+str(len(rows));lines.append('static const uint8_t '+name+'[]={'+','.join(map(str,data))+'};');rows.append('{'+name+',sizeof('+name+'),'+','.join(map(str,[case['begin_bit'],case['end_bit'],case['aligned'],kind,case['scenario']]))+',&'+expected[key]+'}')
 return '\n'.join(lines)+'\nstatic const Fixture fixtures[]={'+',\n'.join(rows)+'};\n'
