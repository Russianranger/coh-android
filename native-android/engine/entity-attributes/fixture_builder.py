"""Exact raw monitor slot projection from whole original source oracle."""
def build(proof):
 lines=[];rows=[]
 for c in proof['cases']:
  e=c['expected'];data=bytes.fromhex(c['wire_hex']);name='wire_'+str(len(rows));lines.append('static const uint8_t '+name+'[]={'+','.join(map(str,data))+'};');slots=[]
  for s in e['slots']:slots.append('{'+','.join(str(s.get(n,0)) for n in ['present','key','value_word','buff'])+'}')
  expected='{'+str(e['new_target'])+','+str(e['full'])+',{'+','.join(slots)+'},0,0}'
  rows.append('{'+name+',sizeof('+name+'),'+','.join(map(str,[c['begin_bit'],c['end_bit'],c['aligned'],c['scenario']]))+','+expected+'}')
 return '\n'.join(lines)+'\nstatic const Fixture fixtures[]={'+',\n'.join(rows)+'};\n'
