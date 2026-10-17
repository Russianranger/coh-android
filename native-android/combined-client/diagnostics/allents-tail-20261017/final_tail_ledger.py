"""Pinned source boundaries for the dictionary-dependent final ALLENTS tails."""
import json,re
from pathlib import Path
import inventory_oracle as inv
q=inv.q;HERE=Path(__file__).resolve().parent
SPECS={'Common/entity/attrib_description.c':['sendAttribDescription','receiveAttribDescription','sendAllMatchingMods','getAllMatchingMods','attrib_GetVal','attribDescriptionGet','attribDescriptionPreprocess','attribDescriptionCreateStash'],'MapServer/src/group/groupdynsend.c':['groupDynSend'],'Game/src/group/groupdynrecv.c':['groupDynReceive'],'MapServer/src/entity/entsend.c':['sendSkyFade'],'Game/src/entity/entrecv.c':['receiveSkyFade'],'Common/group/groupdyn.c':['groupDynBuildBreakableList'],'Common/entity/load_def.c':['load_AttribDescriptions'],'Common/entity/attrib_description.h':[]}
def extract(text,name):
 try:return q.extract(text,name)
 except ValueError:
  m=re.search(r'^[^\n{};]+?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*//[^\n]*\n\s*\{',text,re.M)
  if not m:raise
  at=text.index('{',m.start())+1;depth=1
  while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
  return text[m.start():at]+'\n'
def build():
 pins={};functions={}
 for path,names in SPECS.items():
  text=q.source(path);pins[path]=q.sha(text.encode())
  for name in names:
   body=extract(text,name);functions[name]={'path':path,'sha256_lf':q.sha(body.encode())}
 header=q.source('Common/group/groupdyn.h');pins['Common/group/groupdyn.h']=q.sha(header.encode())
 return {'schema':'coh-final-allents-tail-source-ledger-v1','source_pin':q.PIN,'original_source_sha256_lf':pins,'functions':functions,'attributes':{'entry':'outer1bit present; body new-target1bit,full-mode1bit','monitor_mode':'exactMAX_COMBAT_STATS+1 (11) repetitions:1present,ifpresent32key,F32value,2buffOrDebuff','full_mode':'1targetpresent then32entityID ifset; reverse category and reverse member order withF32+2buffwords for every dictionaryentry; then contributorlist','full_mode_entry_count_on_wire':False,'load_path':'defs/attrib_descriptions.def plus MakeBinFilename cache; ParserLoadFiles/Shared with attribDescriptionPreprocess', 'stash_key':'sizeof(CharacterAttributes)*eType+offAttrib; source predefined-name offsets are rewritten by preprocessing','full_mode_predicate':'player->pl && player->pl->winLocs && player->pl->winLocs[WDW_COMBATNUMBERS].mode==WINDOW_DISPLAYING; independent of full_update','authentic_dictionary_found':False,'dictionary':'g_AttribCategoryList.ppCategories and each ppAttrib MUST be identically ordered; attribDescriptionGet key map; attrib_GetVal class/stat schemas; contributors basepower identities','contributors':'while1present:Pack10attributehash,basepower_Receive,2sourceType;ifcritter/player NULsourceName+Pack20serverID;F32chance,F32magnitude','source_hazard':'original receive full-mode consumes contributors only get_mod true; ALLENTS uses get_mod1. Do not scan to sentinel or omit dictionary-length value records.'},'dynamic_groups':{'prefix':'Pack1modifiedCount;0=none;0xffffffff=full;otherwisedelta list','delta':'modifiedCount recordsPack16index,7HP,1repair','full':'pktSendZipped of dyn_group_count*sizeof(DynGroupStatus) original native bitfieldbytes','status_abi':'original U8 hp:7;U8repair:1; exact sizeof+bitorder require original compiler/target qualification','ownership':'groupDynBuildBreakableList defines ordered dyn_group_status from world-tracker traversal; source graph generation/order must match, count alone insufficient','original_consumer':'full byte_count/sizeof integerdivision, thenrealloc/copy; native must reject partial records and enforce bounded decompression/exact sizes'},'sky':{'wire':'1interesting;ifsetF32weight,Pack2sky1,Pack2sky2','original_absent_defaults':{'weight':0,'sky1':0,'sky2':1},'resources':'raw index metadata does not resolve map sky-file catalog'},'slave':{'wire':'1slavepresent;ifset3F32PYR','scope':'source exact outer inline statements still need selected control/entity ownership'},'complete_initial_update':False,'dictionary_authority':False,'actor_publication':False,'acknowledgments_enabled':False}
if __name__=='__main__':
 result=build();(HERE/'final-tail-ledger.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'functions':len(result['functions']),'files':len(result['original_source_sha256_lf'])}))
