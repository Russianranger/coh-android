"""Compose sky and slave source fragments at matching bit offsets."""
def build(sky,slave):
 lookup={(c['scenario'],c['aligned'],c['begin_bit']):c for c in slave['cases']};lines=[];rows=[]
 for s in sky['cases']:
  for variant in (0,1):
   v=lookup[(s['scenario']//2%5*2+variant,s['aligned'],s['end_bit']%8)];bits=[0]*s['begin_bit']
   for c in (s,v):
    data=bytes.fromhex(c['wire_hex']);bits.extend((data[i//8]>>(i%8))&1 for i in range(c['begin_bit'],c['end_bit']))
   data=bytearray((len(bits)+7)//8)
   for i,b in enumerate(bits):data[i//8]|=b<<(i%8)
   name='wire_'+str(len(rows));lines.append('static const uint8_t '+name+'[]={'+','.join(map(str,data))+'};');e=s['expected'];words=v['expected']['words'];expected='{'+','.join(map(str,[e['interesting'],e['sky1'],e['sky2'],e['weight_word'],v['expected']['present']]))+',{'+','.join(map(str,words))+'},0,0,0}'
   rows.append('{'+name+',sizeof('+name+'),'+','.join(map(str,[s['begin_bit'],s['end_bit'],len(bits),s['aligned'],s['scenario'],variant]))+','+expected+'}')
 return '\n'.join(lines)+'\nstatic const Fixture fixtures[]={'+',\n'.join(rows)+'};\n'
