#include "coh_initial_send.h"
#include <string.h>
static CohStatus scalar(CohProtocolBits *b,CohMapProfile p,unsigned width,uint32_t value){return coh_protocol_write(b,p.byte_aligned?(width+7u)&~7u:width,value)?COH_LIMIT:COH_OK;}
static CohStatus pack(CohProtocolBits *b,CohMapProfile p,unsigned width,uint32_t value){return(p.byte_aligned?coh_protocol_write(b,32,value):coh_protocol_write_pack(b,width,value))?COH_LIMIT:COH_OK;}
CohStatus coh_initial_input_serialize(CohMapProfile profile,uint32_t id,unsigned received,CohMapPacket *out){
 CohMapPacket packet={0},commands={0};CohProtocolBits p,c;CohStatus status=COH_LIMIT;
 if(!out||profile.legacy_commands>1||profile.byte_aligned>1||received>1)return COH_INVALID;
 if(coh_protocol_bits_init(&p,packet.data,sizeof(packet.data),0,1)||coh_protocol_bits_init(&c,commands.data,sizeof(commands.data),0,1))return COH_INVALID;
 if(pack(&p,profile,1,COH_MAP_INPUT+(profile.legacy_commands?5u:0u))||scalar(&p,profile,1,0)||scalar(&p,profile,1,0)||pack(&p,profile,14,0)||scalar(&p,profile,1,0)||pack(&p,profile,1,0))goto done;
 /* clientcomm.c ALLENTS branch appends ACK before entReceiveUpdate can append
  * RECEIVED_CHARACTER. These are CLIENTINP values, never top-level commands. */
 if(pack(&c,profile,1,4)||pack(&c,profile,1,id)||(received&&pack(&c,profile,1,3)))goto done;
 while(p.cursor&7u)if(coh_protocol_write(&p,1,0))goto done;
 for(size_t bit=0;bit<c.bit_length;bit++)if(coh_protocol_write(&p,1,(commands.data[bit/8]>>(bit%8))&1u))goto done;
 packet.bits=(uint32_t)p.bit_length;*out=packet;status=COH_OK;
 done:coh_map_packet_wipe(&packet);coh_map_packet_wipe(&commands);return status;
}
