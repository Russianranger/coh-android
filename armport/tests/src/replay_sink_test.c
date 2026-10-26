/* Replay preflight only: original network functions accept a socketless sink.
 * No receive decoder, live socket, gameplay or receiver-equivalence claim. */
#include <stdio.h>
#include <string.h>
#include "utilitieslib/network/netio.h"
#include "utilitieslib/network/net_structdefs.h"
#include "utilitieslib/network/net_packet.h"
#include "utilitieslib/network/net_link.h"
#include "utilitieslib/network/netio_send.h"

int main(void)
{
    NetLink sink;
    Packet *packet;
    U32 sent;
    memset(&sink, 0, sizeof(sink));
    packetStartup(0, 0);
    packet = pktCreate();
    pktSendBitsPack(packet, 1, 123);
    sent = pktSend(&packet, &sink);
    if (sent || packet || sink.socket) return 1;
    /* Exercise both empty and populated transport ACK paths. pktSend must
     * discard packets without a socket; lnkBatchSend must not enter raw I/O. */
    netSendIdle(&sink);
    sink.ack_count = 1;
    netSendIdle(&sink);
    lnkBatchSend(&sink);
    if (sink.socket) return 2;
    puts("socketless replay sink: pktSend discards, netSendIdle/lnkBatchSend return");
    return 0;
}
