#ifndef COH_TEST_LARGE_SCENE_FIXTURE_H
#define COH_TEST_LARGE_SCENE_FIXTURE_H
/* Qualification-only complete normal GROUPS body emitted by the unchanged
 * original producer/BitStream oracle. No synthetic padding tail is appended.
 * Never linked into production clients or evidence of a real server world. */
#include <zlib.h>
#include "groups-fixtures.h"
#define SCENE_FIXTURE_DECODED_BYTES ((unsigned)sizeof(source_groups_large_world_byte_aligned))
static void scene_fixture_u32(uint8_t *out,uint32_t value) {
    for(unsigned i=0;i<4;i++)out[i]=(uint8_t)(value>>(8*i));
}
static size_t scene_fixture_encode(size_t decoded_bytes,uint32_t command,int streaming,
    uint8_t *out,size_t capacity) {
    CHECK(decoded_bytes==SCENE_FIXTURE_DECODED_BYTES&&decoded_bytes<=COH_NET_DECODED_MAX);
    CHECK(capacity>=16&&capacity<=COH_NET_MESSAGE_MAX);
    uint8_t *body=malloc(decoded_bytes);CHECK(body);
    memcpy(body,source_groups_large_world_byte_aligned,decoded_bytes);
    scene_fixture_u32(body,command);
    scene_fixture_u32(out,command);scene_fixture_u32(out+4,(uint32_t)decoded_bytes-4);
    z_stream stream;memset(&stream,0,sizeof(stream));CHECK(deflateInit(&stream,Z_DEFAULT_COMPRESSION)==Z_OK);
    stream.next_in=body+4;stream.avail_in=(uInt)decoded_bytes-4;
    stream.next_out=out+8;stream.avail_out=(uInt)capacity-8;
    int status=deflate(&stream,streaming?Z_SYNC_FLUSH:Z_FINISH);
    CHECK(status==(streaming?Z_OK:Z_STREAM_END)&&!stream.avail_in&&stream.avail_out);
    size_t bytes=capacity-stream.avail_out;status=deflateEnd(&stream);CHECK(status==Z_OK||(streaming&&status==Z_DATA_ERROR));
    memset(body,0,decoded_bytes);free(body);return bytes;
}
#endif
