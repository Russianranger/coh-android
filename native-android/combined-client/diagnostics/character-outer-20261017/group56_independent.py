"""Independent bounded raw group5/6 model; source fixtures remain separate."""
from independent import Reader,Refused

def decode(case,widths):
 r=Reader(bytes.fromhex(case['wire_hex']),case['end_bit'],case['aligned'],case['begin_bit'])
 def auto():
  tag=r.scalar(2)
  if tag>3:raise Refused('auto tag')
  return r.scalar((2,10,24,32)[tag])
 def text(cap=1024):return r.string(cap).decode()
 def count(n,cap):
  v=r.packed(n)
  if v>cap:raise Refused('local count')
  return v
 out={}
 for key in ['reward_tokens','active_tokens']:
  n=auto()
  if n>512:raise Refused('tokens')
  out[key]=[{'name':text(),'value':r.packed(1),'timer':r.packed(1)} for _ in range(n)]
 for key in ['lfg','hidden']:out[key]=r.scalar(10)
 for key in ['supergroup_mode','hide_supergroup_emblem','skills_unlocked','team_buff']:out[key]=r.scalar(1)
 for key in ['dock_mode','inspiration_mode','new_features']:out[key]=r.scalar(32)
 chat={};out['chat']=chat
 chat['help_added']=r.scalar(1)
 for key in ['send_channel','user_send_channel','options','primary_minimized']:chat[key]=r.packed(1)
 chat['windows']=[{'selected_top':r.packed(1),'selected_bottom':r.packed(1),'tabs':r.packed(1),'divider_word':r.scalar(32)} for _ in range(5)]
 chat['tabs']=[]
 for _ in range(20):
  tab={'name':text(19)}
  # pktGetBitsArray unconditionally rounds cursor to the next byte.
  r.cursor=(r.cursor+7)//8*8
  tab.update(system0=r.scalar(32),system1=r.scalar(32))
  for key in ['users','options','default_channel','default_type']:tab[key]=r.packed(1)
  chat['tabs'].append(tab)
 chat['channels']=[{'name':text(22),'options':r.packed(1),'color1':r.scalar(32),'color2':r.scalar(32)} for _ in range(15)]
 out['title_the']=r.packed(5)
 for key,cap in [('title_the_text',10),('title_common',32),('title_origin',32)]:out[key]=text(cap)
 out['title_color0']=auto();out['title_color1']=auto();out['title_badge']=r.scalar(32)
 for key,cap in [('title_special',128),('description',1024),('motto',128),('comment',128),('wire_key_profile',32)]:out[key]=text(cap)
 out['applied_key_profile']='Dev' if case['scenario']%3==0 else out['wire_key_profile']
 out['keybinds']=[]
 for _ in range(256):
  command=text(256);key=r.scalar(32);modifier=r.scalar(32)
  out['keybinds'].append({'command':command,'wire_key':key,'modifier':modifier,'applied_key':key&255,'applied_secondary':key&0xf00})
 out['options_saved']=r.scalar(1)
 out['option_words']=[r.scalar(32 if n<0 else n) for n in widths] if out['options_saved'] else [r.scalar(1),r.scalar(32),r.scalar(32)]
 out['dividers']=[r.packed(9) for _ in range(8)];out['first']=r.scalar(1);out['nocoll']=r.scalar(2)
 full=r.packed(1);n=count(1,16)
 if full!=1:raise Refused('fixture requires full friends')
 out['friends']=[]
 for _ in range(n):
  if r.scalar(1)!=1:raise Refused('fixture requires present friend')
  f={'dbid':r.packed(1),'online':r.scalar(1),'name':text(32),'class':r.packed(1),'origin':r.packed(1)}
  if f['online']:f.update(map_id=r.packed(1),map_name=text(256))
  out['friends'].append(f)
 out['combat_monitors']=[]
 for _ in range(10):out['combat_monitors'].append({'key':r.packed(8) if r.scalar(1) else 0,'order':r.scalar(4) if r.scalar(1) else 0})
 out['rename']=r.scalar(1)
 if r.cursor!=case['end_bit']:raise Refused('trailing bits')
 return out

def qualify(cases,widths):
 for case in cases:
  actual=decode(case,widths)
  if actual!=case['expected']:
   differences=[k for k in actual if actual[k]!=case['expected'][k]]
   raise ValueError('independent raw model differs:'+str(differences)+str([case['scenario'],case['aligned'],case['begin_bit']]))
 return {'passed':True,'original_per_field_comparisons':len(cases),'original_malformed_input_executed':False,'native_parser_qualified':False}
