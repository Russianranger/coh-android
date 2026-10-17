"""Project independent original consumer/raw fixture observations into native POD expectations.
No production parser is imported or executed when constructing expectations.
"""
import json
def cstring(value):
 return '{'+','.join(map(str,value.encode()+b'\0'))+'}'
def initializer(expected):
 pool=bytearray()
 def ref(text):
  offset=len(pool);raw=text.encode();pool.extend(raw+b'\0');return '{'+str(offset)+','+str(len(raw))+'}'
 def tokens(rows):return '{'+','.join('{'+ref(t['name'])+','+str(t['value'])+','+str(t['timer'])+'}' for t in rows)+'}'
 fields={};fields['reward_count']=str(len(expected['reward_tokens']));fields['active_reward_count']=str(len(expected['active_tokens']))
 if expected['reward_tokens']:fields['rewards']=tokens(expected['reward_tokens'])
 if expected['active_tokens']:fields['active_rewards']=tokens(expected['active_tokens'])
 for name,key in [('lfg','lfg'),('hidden','hidden'),('supergroup_mode','supergroup_mode'),('hide_emblem','hide_supergroup_emblem'),('skills_unlocked','skills_unlocked'),('team_buff_display','team_buff'),('dock_mode','dock_mode'),('inspiration_mode','inspiration_mode'),('new_features','new_features')]:fields[name]=str(expected[key])
 chat=expected['chat']
 for name,key in [('help_chat_added','help_added'),('chat_send_channel','send_channel'),('user_send_channel','user_send_channel'),('chat_options','options'),('primary_chat_minimized','primary_minimized')]:fields[name]=str(chat[key])
 fields['chat_windows']='{'+','.join('{'+','.join(str(w[k]) for k in ['selected_top','selected_bottom','tabs','divider_word'])+'}' for w in chat['windows'])+'}'
 fields['chat_tabs']='{'+','.join('{'+cstring(t['name'])+',{'+str(t['system0'])+','+str(t['system1'])+'},'+','.join(str(t[k]) for k in ['users','options','default_channel','default_type'])+'}' for t in chat['tabs'])+'}'
 fields['chat_channels']='{'+','.join('{'+cstring(c['name'])+','+str(c['options'])+',{'+str(c['color1'])+','+str(c['color2'])+'}}' for c in chat['channels'])+'}'
 for name in ['title_the','title_badge']:fields[name]=str(expected[name])
 fields['title_colors']='{'+str(expected['title_color0'])+','+str(expected['title_color1'])+'}'
 for name in ['title_the_text','title_common','title_origin','title_special','description','motto','comment']:fields[name]=cstring(expected[name])
 fields['key_profile']=cstring(expected['wire_key_profile'])
 fields['keybinds']='{'+','.join('{'+ref(k['command'])+','+str(k['wire_key'])+','+str(k['modifier'])+'}' for k in expected['keybinds'])+'}'
 fields['options_saved']=str(expected['options_saved'])
 if expected['options_saved']:fields['option_words']='{'+','.join(map(str,expected['option_words']))+'}'
 else:
  for name,word in zip(['mouse_invert','mouse_speed_word','turn_speed_word'],expected['option_words']):fields[name]=str(word)
 fields['dividers']='{'+','.join(map(str,expected['dividers']))+'}';fields['control_first']=str(expected['first']);fields['control_no_collision']=str(expected['nocoll']);fields['friends_full_update']='1';fields['friend_count']=str(len(expected['friends']))
 if expected['friends']:
  friends=[]
  for f in expected['friends']:
   fields_f=['1',str(f['dbid']),str(f['online']),str(f['class']),str(f['origin']),str(f.get('map_id',0)),cstring(f['name']),cstring(f.get('map_name',''))];friends.append('{'+','.join(fields_f)+'}')
  fields['friends']='{'+','.join(friends)+'}'
 fields['monitors']='{'+','.join('{'+str(int(bool(m['key'])))+','+str(m['key'])+','+str(int(bool(m['order'])))+','+str(m['order'])+'}' for m in expected['combat_monitors'])+'}'
 fields['rename']=str(expected['rename']);fields['text_bytes']=str(len(pool));fields['text']='{'+','.join(map(str,pool))+'}'
 return '{'+','.join('.'+name+'='+value for name,value in fields.items())+'}'
def generate(proof):
 lines=[];rows=[];expected_by_scenario={}
 for i,f in enumerate(proof['cases']):
  scenario=f['scenario'];expected=f['expected']
  if scenario not in expected_by_scenario:
   expected_by_scenario[scenario]=expected;lines.append('static const CohCharacterTail tail_expected_'+str(scenario)+'='+initializer(expected)+';')
  elif expected_by_scenario[scenario]!=expected:raise ValueError('Original observation changes with alignment')
  name='tail_'+str(i);raw=bytes.fromhex(f['wire_hex']);lines.append('static const uint8_t '+name+'[]={'+','.join(map(str,raw))+'};');rows.append('{'+name+',sizeof('+name+'),'+','.join(str(f[n]) for n in ['begin_bit','end_bit','aligned','scenario'])+',&tail_expected_'+str(scenario)+'}')
 lines.append('static const TailFixture tail_fixtures[]={'+',\n'.join(rows)+'};\n');return '\n'.join(lines)
