"""Source pinned remaining ALLENTS dependency inventory; this is not admission."""
import json,re
from pathlib import Path
import inventory_oracle as inv
q=inv.q;HERE=Path(__file__).resolve().parent
SPECS={
'MapServer/src/player/inventory_server.c':['entity_SendInvUpdate'],
'Game/src/player/inventory_client.c':['entity_ReceiveInvUpdate'],
'Common/entity/character_net.c':['conceptitem_Send','character_inventory_Send','character_inventory_Receive'],
'Common/entity/character_inventory.c':['GetItemsByIdArrayRef','character_SetInventory','character_SetConcept'],
'Common/auction/Auction.c':['AuctionInventory_Send','AuctionInventory_Recv','AuctionInventory_ToStr','AuctionInventory_FromStr'],
'Common/entity/Invention.c':['invention_Send','invention_Receive','entity_SendInventionUpdate','entity_ReceiveInventionUpdate'],
'MapServer/src/container/team.c':['sendMemberCommon','sendTeammate','team_sendList'],
'MapServer/src/entity/SgrpServer.c':['sgroup_sendList'],
'MapServer/src/container/league.c':['sendLeagueMate','league_sendList'],
'Game/src/UI/uiNet.c':['recieveMemberCommon','receiveTeamList','receiveSuperStats','receiveLeagueList'],
'Game/src/entity/entrecv.c':['entReceiveUpdate'],
'MapServer/src/entity/entsend.c':['entSendUpdate'],
}
def build():
 records={};pins={}
 for path,names in SPECS.items():
  text=q.source(path);pins[path]=q.sha(text.encode())
  for name in names:
   body=q.extract(text,name);records[name]={'path':path,'sha256_lf':q.sha(body.encode()),'wire_calls_lexical_only':re.findall(r'\b(pkt(?:Send|Get)\w+)\s*\(',body),'lines':body.count('\n')}
 return dict(schema='coh-allents-tail-source-ledger-v1',source_pin=q.PIN,original_source_sha256_lf=pins,functions=records,
 order_after_badges=['entity_ReceiveInvUpdate','entity_ReceiveInventionUpdate','workshop string','team skip bit then receiveTeamList','receiveSuperStats','league skip bit then receiveLeagueList','attrib description present bit','groupDynReceive','receiveSkyFade','slave present bit then3F32'],
 inventory={'item':'Pack5 type,index,amount,id; type Concept adds4F32','update':'Pack1 item count; ordered items; BitsAuto auction updated; if nonzero one NUL string','dictionary_by_type':{'Salvage':'g_SalvageDict.itemsById','StoredSalvage':'g_SalvageDict.itemsById','Concept':'g_ConceptDict.itemsById','Recipe':'g_DetailRecipeDict.itemsById','BaseDetail':'g_DetailDict.itemsById'},'raw_auction_string_is_not_parsed':'AuctionInventory_FromStr uses original escaped text parser; item dictionary semantics remain separate'},
 invention={'status_width':'Pack1','receiver':'invention_Receive body wholly commented out','sender':'status true sends invention state Pack1 even stateNone; nonzero state has recipe/boost/powerup slots/concept slots','qualification_policy':'false status safe raw profile; true status cannot be admitted as matching original consumer without explicit source incompatibility policy'},
 workshop={'wire':'one NUL string','original_destination_capacity':32,'policy':'bound full wire string before preserving raw; no workshop lookup/application'},
 team={'wire':'ifset PackDBID team ID;2bit taskforce mode;10bit LFG; nonzeroID addsPack32leader,Pack1count,3BitsAuto(level,mentor,activeDBID),members','member':'32DBID,1onmap; offmap adds1changed and if changed name+translated map strings','order':'mentor first then other members in source order','max_members':8,'name_capacity':64,'state_dependencies':'unchanged offmap names require previous generation; onmap names resolved separately from entity DBID'},
 league={'wire':'ifsetPackDBID leagueID; nonzero addsPack32leader,Pack1count,membercommon+32teamLeaderID+32lockStatus each','order':'leader first then others','max_members':48},
 superstats={'wire':'Pack1count;zero stops;nonzero adds7Pack1financial/playerType words then1update;false stops;true per-member records,group strings/colors/ranks/permissions/memberranks/allies','details':'Exact whole source function hashes and lexical calls retained; loop counts and byte-array sizes require original supergroup headers, not guessed caps','dictionary':'arch/origin transmitted strings; raw storage can retain without dictionary application; UI/unescape/sideeffects separate'},
 boundary={'transport_end_not_proven':True,'reason':'entSendUpdate may append SERVER_BEGIN_BYTE_ALIGNED_DATA and entityPacket bits; parser must use command framing'},
 remaining=['auction escaped parser semantics','active invention producer/consumer incompatibility','team/league complete source fixtures','superstats rank/permission/allies header sizes and fixtures','attribute-description dictionary/full tail','dynamic group graph ownership','skyfade source grammar','slave/outer command boundary'],
 full_initial_update_complete=False,actor_publication=False,acknowledgments_enabled=False)
if __name__=='__main__':
 result=build();(HERE/'source-ledger.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'functions':len(result['functions']),'files':len(result['original_source_sha256_lf'])}))
