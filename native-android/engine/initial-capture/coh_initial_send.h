#ifndef COH_INITIAL_SEND_H
#define COH_INITIAL_SEND_H
#include "../mapclient/coh_mapclient.h"
/* Original commSendInput envelope for the explicit stationary local client:
 * no control update, current target, selected target DBID, control log or old
 * control commands. The input substream is byte-aligned by pktSendBitsArray.
 * ACK retains the actual full-update ID. RECEIVED_CHARACTER is optional and
 * requires the caller's original waiting-for-full-update condition. Neither
 * this serializer nor successful transport queueing proves a received entity. */
CohStatus coh_initial_input_serialize(CohMapProfile,uint32_t full_update_id,
 unsigned received_character,CohMapPacket *);
#endif
