"""Hash-bound original outer-character ordering ledger, separate from executed fixtures."""
import json,re
from pathlib import Path
import qualify_outer as q

def make():
 extra=['Common/entity/entVarUpdate.h','Common/entity/chatSettings.c','MapServer/src/entity/friends.c','Game/src/UI/uiChat.c']
 texts={p:q.source(p) for p in q.PATHS+extra};proof=json.loads((q.HERE/'host-proof.json').read_text())
 # Independently derive fixed chat/system counts from hash-pinned source.
 chat=texts['Common/entity/chatSettings.h']
 for key,expected in [('MAX_CHAT_WINDOWS',5),('MAX_CHAT_TABS',20),('MAX_CHAT_CHANNELS',15)]:
  assert int(re.search(r'^#define\s+'+key+r'\s+(\d+)',chat,re.M).group(1))==expected
 info=re.search(r'typedef enum INFO_BOX_MSGS\s*\{(.*?)\}\s*INFO_BOX_MSGS;',texts['Common/entity/entVarUpdate.h'],re.S).group(1)
 info=re.sub(r'/\*.*?\*/|//[^\n]*','',info,flags=re.S);counter=-1;values={}
 for item in info.split(','):
  if not item.strip():continue
  pair=item.strip().split('=');counter=int(pair[1].strip(),0) if len(pair)==2 else counter+1;values[pair[0].strip()]=counter
 assert (values['INFO_TOTAL']+31)//32==2
 functions={}
 for path,names in {
 'MapServer/src/entity/entserver.c':['sendCharacterToClient'],
 'Game/src/entity/entrecv.c':['receiveCharacterFromServer','receiveFullPopHelp'],
 'Common/entity/chatSettings.c':['sendChatSettings','receiveChatSettings'],
 'MapServer/src/entity/friends.c':['sendFriendsList'],
 'Game/src/UI/uiChat.c':['receiveChatSettingsFromServer'],
 'Game/src/UI/uiNet.c':['receiveOptions','receiveTitles','receiveDescription','receiveDividers','receiveFriendsList','keybinds_recieve'],
 'MapServer/src/entity/keybinds.c':['keybinds_send'],
 'Common/entity/attrib_description.c':['sendCombatMonitorStats','receiveCombatMonitorStats']}.items():
  for name in names:functions[name]={'source':path,'sha256_lf':q.sha(q.extract(texts[path],name).encode())}
 enum=re.search(r'typedef enum EUserOptions\s*\{(.*?)\}EUserOptions;',texts['Game/src/UI/uiOptions_Type.h'],re.S).group(1)
 enum=re.sub(r'/\*.*?\*/|//[^\n]*','',enum,flags=re.S);names=re.findall(r'\b(kUO_\w+)\b',enum)
 assert names[0]=='kUO_NotAnOption' and names[-1]=='kUO_OptionTotal' and len(names)-2==len(proof['constants']['option_widths_in_enum_order'])
 widths=[{'id':i+1,'name':name,'bits':width,'float32':width<0} for i,(name,width) in enumerate(zip(names[1:-1],proof['constants']['option_widths_in_enum_order']))]
 return {'schema':'coh-original-character-outer-order-v1','original_revision':q.PIN,'source_sha256_lf':{p:q.sha(t.encode()) for p,t in texts.items()},'functions':functions,'scope':'Exact original wire ordering/schema ledger. Only helper/group4 receipts establish execution; unexecuted helpers remain explicit dependencies. No native full-tail or actor admission.',
 'group4':[
 {'field':'tray.current_trays','count':4,'wire':'U32 each'},
 {'field':'tray.trayIndexes','wire':'U32'},
 {'field':'tray.slots','builds':8,'trays_per_build':9,'slots_per_tray':10,'count':720,'wire':'type5; power(type1):U32 set,U32 power; inspiration(type2):Pack3 column,Pack3 row; macro(type6/17):string command[256],short[32],icon[256]; other types:no body','ordering':'build first,then flat tray/slot; null emits type0'},
 {'field':'default_power','wire':'presence1; if present U32set,U32power'},
 {'field':'tray_mode','wire':'mode1,mode_alt2:1'},
 {'field':'entity.name','wire':'string','original_consumer_copy_bytes':32},
 {'field':'entity.strings','wire':'motto string then description string','source_array_bytes':[128,1024],'consumer_side_effect':'receiveEntStrings changes description angle brackets to square; raw native staging must preserve wire'},
 {'field':'popHelpStatus','count':128,'wire':'U32 each'},
 {'field':'popHelpLatest','count':5,'wire':'U32 each'},
 {'field':'windows','count':128,'wire':'Pack1idx,xp,yp,mode,locked,color,backcolor; maximized1; dimensions_present1 then Pack1wd,Pack1ht; scale_present1 then F32','source_semantics':'ALWAYS_CLOSED(2) forces WINDOW_DOCKED(4); draggable_frame or idx4 sends dimensions; absent/zero scale maps1.f in original consumer'}],
 'group5':[
 {'field':'rewardTokens','wire':'Auto count; reverse source array order each string name,Pack1value,Pack1timer'},
 {'field':'activePlayerRewardTokens','wire':'Auto count; reverse source array order each string name,Pack1value,Pack1timer'},
 {'field':'lfg,hidden','wire':'10bits each'},
 {'field':'supergroup_mode,hide_supergroup_emblem,skillsUnlocked,teambuff_display','wire':'1bit each'},
 {'field':'dock_mode,inspiration_mode,newFeaturesVersion','wire':'32bits each'}],
 'group6':[
 {'field':'chatSettings','wire':'SERVER help-added-now1; Pack1chatSendChannel,userSendChannel,options,primaryChatMinimized;5windows each Pack1selectedtop,selectedbot,tabListBF,F32divider;20tabs each stringname,64bit array,Pack1userBF,optionsBF,defaultChannel,defaultType;15channels each stringname,Pack1optionsBF,U32color1,U32color2','source_counts':{'windows':5,'tabs':20,'channels':15,'system_words':2},'status':'schema only; original migration/default/UI wrapper side effects not executed in this fixture'},
 {'field':'titles','wire':'Pack5titleThe; stringtitleTheText,titleCommon,titleOrigin; Autocolor0,Autocolor1; U32badge; stringtitleSpecial'},
 {'field':'description,motto,comment','wire':'stringdescription,stringmotto,stringcomment','note':'description/motto repeat prior group4 values; original receiveDescription copies these again without breakHTMLtags'},
 {'field':'keybinds','wire':'stringprofile;256records each stringcommand,U32key,U32modifier','consumer_semantics':'copy command bound256; key&0xff and key&0xf00 secondary retained separately; development mode substitutes Dev profile','status':'schema only; full original helper remains to execute'},
 {'field':'options','wire':'saved1; if saved114ordered option fields below; otherwise mouse_invert1,F32mouse_speed,F32turn_speed','status':'original producer/consumer and independent byte model executed'},
 {'field':'dividers','count':8,'wire':'Pack9 each','ordering':['superName','superMap','superTitle','emailFrom','emailSubject','friendName','lfgName','lfgMap'],'application_rule':'original only applies saved dividers when first nonzero'},
 {'field':'control','wire':'first1,nocoll2'},
 {'field':'friends','wire':'Pack1full_update,Pack1count; per index present1; if present Pack1dbid,online1,stringname,Pack1class,Pack1origin; online addsPack1mapid,stringmapname','source_semantics':'full character sender always sendsfull_update1; -1 class/origin sentinel is full unsigned packed word; original consumer resolves dictionary indices and prior packet state','status':'schema only; exact original helper remains to execute'},
 {'field':'combatMonitorStats','count':10,'wire':'IfSetPack8key;IfSet4order','status':'schema only; exact original helper remains to execute'},
 {'field':'rename','wire':'1bit','boundary':'end of this packet body within sendCharacterToClient; subsequent Contact/Task/Clue/Mission calls send their own separate packets'}],
 'option_fields':widths,'complete_groups4to6_native_parser':False,'full_update_complete':False,'actor_publication':False,'acknowledgments_enabled':False}
if __name__=='__main__':
 out=make();(q.HERE/'outer-grammar.json').write_text(json.dumps(out,indent=2)+'\n')
