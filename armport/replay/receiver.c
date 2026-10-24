/* Original-receiver replay qualification, never normal gameplay.
 * Called after game_beforeLoop's normal startup. Additional initialization:
 * entReceiveInit resets receive ordering/deletes as resetStuffOnMapMove does;
 * commNewInputPak resets the original outgoing input packet before each record.
 * No entity/costume/game-command decoder is replaced. Transport statistics,
 * packet-loss handling, the UDP envelope and READY generation are not exercised.
 *
 * This first execution stage qualifies dispatch/cursors and captures actual ACKs.
 * State equivalence is deliberately NOT qualified by this stage. Exit 2 after
 * 117 dispatches means the comparison work is still incomplete, not M3 success.
 */
#include <winsock2.h>
#include <windows.h>
#include <wincrypt.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include "clientcomm/armport_replay.h"
#include "clientcomm/clientcomm.h"
#include "entity/entrecv.h"
#include "entity/entVarUpdate.h"
#include <utilitieslib/network/net_packet.h>
#include <utilitieslib/network/netio.h>
#include <utilitieslib/utils/SuperAssert.h>
#include "comm_game.h"

static HANDLE output = INVALID_HANDLE_VALUE;
static int active;
static unsigned int dispatches;

static void emit(const char *format, ...)
{
    char line[2048];
    DWORD written;
    int size;
    va_list args;
    va_start(args, format);
    size = vsnprintf(line, sizeof(line), format, args);
    va_end(args);
    if (size < 0 || size >= sizeof(line) || output == INVALID_HANDLE_VALUE ||
        !WriteFile(output, line, size, &written, NULL) || written != size)
        ExitProcess(3);
    FlushFileBuffers(output);
}

static void fail(const char *reason)
{
    emit("{\"type\":\"failure\",\"dispatches\":%u,\"reason\":\"%s\"}\n", dispatches, reason);
    ExitProcess(3);
}

static void require(int condition, const char *reason)
{
    if (!condition) fail(reason);
}

void armportReplayUnknownCommand(int command)
{
    if (active) {
        emit("{\"type\":\"unknown_game_command\",\"command\":%d}\n", command);
        fail("unknown game command");
    }
}

static unsigned int u32(const unsigned char *p)
{
    return (unsigned int)p[0] | (unsigned int)p[1] << 8 |
           (unsigned int)p[2] << 16 | (unsigned int)p[3] << 24;
}

static unsigned long long u64(const unsigned char *p)
{
    return u32(p) | (unsigned long long)u32(p + 4) << 32;
}

static void sha256(const unsigned char *data, DWORD size, const char *expected)
{
    HCRYPTPROV provider = 0;
    HCRYPTHASH hash = 0;
    unsigned char bytes[32];
    char hex[65];
    DWORD length = sizeof(bytes);
    int i;
    require(CryptAcquireContextA(&provider, NULL, NULL, PROV_RSA_AES, CRYPT_VERIFYCONTEXT), "SHA provider");
    require(CryptCreateHash(provider, CALG_SHA_256, 0, 0, &hash), "SHA create");
    require(CryptHashData(hash, data, size, 0), "SHA data");
    require(CryptGetHashParam(hash, HP_HASHVAL, bytes, &length, 0) && length == 32, "SHA value");
    CryptDestroyHash(hash);
    CryptReleaseContext(provider, 0);
    for (i = 0; i < 32; ++i) sprintf(hex + i * 2, "%02x", bytes[i]);
    require(strcmp(hex, expected) == 0, "input identity differs from reviewed Thor capture");
}

static unsigned char *read_input(const char *directory, const char *name, DWORD size, const char *hash)
{
    char path[1024];
    HANDLE file;
    LARGE_INTEGER actual;
    unsigned char *data;
    DWORD read;
    require(snprintf(path, sizeof(path), "%s/%s", directory, name) < sizeof(path), "input path too long");
    file = CreateFileA(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    require(file != INVALID_HANDLE_VALUE, "input file missing");
    require(GetFileSizeEx(file, &actual) && actual.QuadPart == size, "input file size");
    data = calloc(1, size + 4); /* padding for the original bit-reader's word fetch */
    require(data != NULL, "input allocation");
    require(ReadFile(file, data, size, &read, NULL) && read == size, "input read");
    CloseHandle(file);
    sha256(data, size, hash);
    return data;
}

static void dispatch(NetLink *sink, unsigned char *payload, unsigned int size,
                     unsigned int bits, unsigned int cursor, unsigned int aligned,
                     unsigned int id, unsigned int command, unsigned int ordered,
                     unsigned int ordered_id, int synthetic)
{
    Packet packet = {0};
    unsigned int end, output_bits;
    unsigned int ack = 0;
    require(size && bits && bits <= size * 8 && cursor <= bits, "packet bounds");
    require(aligned <= 1 && (!aligned || cursor % 8 == 0), "packet alignment");
    require(ordered <= 1 && (command == SERVER_ALLENTS || command == SERVER_UPDATE), "packet metadata");
    require(synthetic || id >= 32, "real record ID below 32");
    /* initBitStream zeros the first four bytes even in Read mode. Initialize
     * the documented fields directly so captured payload bytes stay intact. */
    packet.stream.mode = Read;
    packet.stream.data = payload;
    packet.stream.size = packet.stream.maxSize = size;
    packet.stream.bitLength = bits;
    packet.stream.byteAlignedMode = aligned;
    packet.stream.cursor.byte = cursor / 8;
    packet.stream.cursor.bit = cursor % 8;
    packet.stream.userData = &packet;
    packet.id = id;
    packet.ordered = ordered;
    packet.ordered_id = ordered_id;
    commNewInputPak();
    emit("{\"type\":\"dispatch_begin\",\"index\":%u,\"id\":%u,\"command\":%u,"
         "\"logical_bits\":%u,\"cursor\":%u,\"byte_aligned\":%u,\"ordered\":%u,"
         "\"ordered_id\":%u,\"synthetic_transport\":%s}\n",
         dispatches, id, command, bits, cursor, aligned, ordered, ordered_id, synthetic ? "true" : "false");
    require(commArmPortReplayDispatch(&packet, command, sink) == 1, "receive dispatch returned failure");
    end = bsGetCursorBitPosition(&packet.stream);
    require(!packet.stream.errorFlags && !bsIsBad(&packet.stream), "receive stream error");
    require(end == bits, "receive did not consume exact logical bit length");
    output_bits = bsGetBitLength(&client_input_pak->stream);
    if (command == SERVER_ALLENTS) {
        /* Inspect a read-only view of the real output, not a re-created ACK. */
        Packet sent = *client_input_pak;
        sent.stream.mode = Read;
        sent.stream.bitLength = output_bits;
        sent.stream.cursor.byte = sent.stream.cursor.bit = 0;
        require(pktGetBitsPack(&sent, 1) == CLIENTINP_ACK_FULL_UPDATE, "missing full-update ACK");
        ack = pktGetBitsPack(&sent, 1);
        require(!sent.stream.errorFlags, "ACK stream error");
        emit("{\"type\":\"ack\",\"packet_id\":%u,\"ack_id\":%u,\"ack_bits\":%u,\"total_input_bits\":%u}\n",
             id, ack, bsGetCursorBitPosition(&sent.stream), output_bits);
    }
    ++dispatches;
    emit("{\"type\":\"dispatch_end\",\"count\":%u,\"id\":%u,\"cursor\":%u,\"error_flags\":0}\n",
         dispatches, id, end);
}

void armportReplayMaybeRun(void)
{
    char directory[768], path[1024], id_text[16];
    DWORD length = GetEnvironmentVariableA("ARMPORT_REPLAY_DIR", directory, sizeof(directory));
    unsigned char *initial, *post;
    unsigned int initial_id = 1, at = 64, records = 0;
    unsigned long long payload_total = 0, bit_total = 0;
    NetLink *sink;
    if (!length) return;
    if (length >= sizeof(directory)) ExitProcess(3);
    if (snprintf(path, sizeof(path), "%s/receiver.jsonl", directory) >= sizeof(path)) ExitProcess(3);
    output = CreateFileA(path, GENERIC_WRITE, FILE_SHARE_READ, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (output == INVALID_HANDLE_VALUE) ExitProcess(3);
    active = 1;
#ifdef FINAL
    fail("replay requires OptDebug with assertions enabled");
#endif
    setAssertMode(ASSERTMODE_STDERR | ASSERTMODE_EXIT);
    length = GetEnvironmentVariableA("ARMPORT_REPLAY_INITIAL_ID", id_text, sizeof(id_text));
    require(length < sizeof(id_text), "synthetic ID too long");
    if (length) {
        require(strcmp(id_text, "1") == 0 || strcmp(id_text, "31") == 0, "synthetic ID must be 1 or 31");
        initial_id = (unsigned int)atoi(id_text);
    }
    require(!comm_link.socket, "replay requires no server connection");
    emit("{\"type\":\"configuration\",\"scope\":\"receiver_cursors_and_ack_only\","
         "\"initial_id\":%u,\"initial_ordered\":1,\"initial_ordered_id\":1,"
         "\"synthetic_initial_transport\":true,\"transport_stats_exercised\":false,"
         "\"state_comparison_complete\":false}\n", initial_id);
    initial = read_input(directory, "initial-replay.bin", 37994,
        "cc949b01f5db6ff108efcf6afcbfe9567c432b4aa15f3a02c8f193e380cc7b39");
    post = read_input(directory, "post-ready-replay.bin", 74416,
        "f134c3c083e571b679ed6976bec36c672028854f4a48879cc0f2d47423db96a9");
    require(!memcmp(initial, "COHIRP01", 8) && u32(initial + 8) == 88 &&
            u32(initial + 12) == 37994 - 88 && u64(initial + 16) == 303248 &&
            u64(initial + 24) == 32 && u32(initial + 48) == 28 && u32(initial + 52) == SERVER_ALLENTS,
            "INITIAL envelope");
    require(!memcmp(post, "COHPRP01", 8) && u32(post + 8) == 64 && u32(post + 12) == 112,
            "post-READY envelope");
    sink = calloc(1, sizeof(*sink));
    require(sink != NULL, "sink allocation");
    entReceiveInit();
    dispatch(sink, initial + 88, u32(initial + 12), (unsigned int)u64(initial + 16),
             (unsigned int)u64(initial + 24), u32(initial + 40), initial_id, SERVER_ALLENTS, 1, 1, 1);
    while (at + 112 <= 74416 - 96 && !memcmp(post + at, "COHMSG01", 8)) {
        unsigned char *h = post + at;
        unsigned int size = u32(h + 12);
        require(records < 116 && u32(h + 8) == 112 && size <= 74416 - 96 - at - 112, "record bounds");
        require(u64(h + 16) <= size * 8 && u64(h + 24) <= u64(h + 16) &&
                u64(h + 48) >= 32 && u64(h + 48) <= 155, "record bit bounds or ID");
        dispatch(sink, h + 112, size, (unsigned int)u64(h + 16), (unsigned int)u64(h + 24),
                 u32(h + 60), (unsigned int)u64(h + 48), u32(h + 56), u32(h + 64), u32(h + 68), 0);
        payload_total += size;
        bit_total += u64(h + 16);
        at += 112 + size;
        ++records;
    }
    require(records == 116 && dispatches == 117 && at == 74416 - 96 &&
            !memcmp(post + at, "COHPEND1", 8) && u32(post + at + 12) == records &&
            u32(post + at + 16) == records && u32(post + at + 28) == 1 &&
            u64(post + at + 32) == payload_total && u64(post + at + 40) == bit_total,
            "incomplete replay or trailer");
    emit("{\"type\":\"result\",\"dispatches\":117,\"exact_cursors\":true,"
         "\"state_comparison_complete\":false,\"m3_replay_complete\":false}\n");
    CloseHandle(output);
    free(sink);
    free(post);
    free(initial);
    ExitProcess(2); /* Explicitly incomplete until full state comparison exists. */
}
