"""Compose exact source fragments at actual absolute bit offsets."""
def build(team,sg):
 lines=[];rows=[]
 tlookup={(c['scenario'],c['aligned'],c['begin_bit'],c['kind']):i for i,c in enumerate(team['cases'])}
 slookup={(c['scenario'],c['aligned'],c['begin_bit']):i for i,c in enumerate(sg['cases'])}
 for base in team['cases']:
  if base['kind']!='team':continue
  for variant in range(4):
   mode=base['aligned'];bits=[0]*base['begin_bit'];start=len(bits);ts=variant&1;ls=variant>>1
   def scalar(v,n):bits.extend((v>>i)&1 for i in range((n+7)//8*8 if mode else n))
   def append(c):
    data=bytes.fromhex(c['wire_hex']);bits.extend((data[i//8]>>(i%8))&1 for i in range(c['begin_bit'],c['end_bit']))
   scalar(ts,1);ti=None
   if not ts:ti=tlookup[(base['scenario'],mode,len(bits)%8,'team')];append(team['cases'][ti])
   tend=len(bits);si=slookup[(base['scenario']%18,mode,len(bits)%8)];append(sg['cases'][si]);send=len(bits);scalar(ls,1);li=None
   if not ls:li=tlookup[(base['scenario'],mode,len(bits)%8,'league')];append(team['cases'][li])
   data=bytearray((len(bits)+7)//8)
   for i,b in enumerate(bits):data[i//8]|=b<<(i%8)
   name='social_wire_'+str(len(rows));lines.append('static const uint8_t '+name+'[]={'+','.join(map(str,data))+'};')
   rows.append('{'+name+',sizeof('+name+'),'+','.join(map(str,[start,tend,send,len(bits),mode,ts,ls]))+','+('NULL' if ti is None else '&team_fixtures['+str(ti)+']')+',&sg_fixtures['+str(si)+'],'+('NULL' if li is None else '&team_fixtures['+str(li)+']')+'}')
 return '\n'.join(lines)+'\nstatic const SocialFixture social_fixtures[]={'+',\n'.join(rows)+'};\n'
