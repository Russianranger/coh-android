#ifndef COH_TEST_LARGE_SCENE_FIXTURE_H
#define COH_TEST_LARGE_SCENE_FIXTURE_H
/* Qualification-only source-layout fixture. scene1 is emitted by the pinned
 * original BitStream writer; every appended tail byte is synthetic/unparsed.
 * Never linked into production clients or evidence of a real server world. */
#include <zlib.h>
#define SCENE_FIXTURE_DECODED_BYTES (128u*1024u)
static void scene_fixture_u32(uint8_t *out,uint32_t value) {
    for(unsigned i=0;i<4;i++)out[i]=(uint8_t)(value>>(8*i));
}
static size_t scene_fixture_encode(size_t decoded_bytes,uint32_t command,int streaming,
    uint8_t *out,size_t capacity) {
    CHECK(decoded_bytes>=sizeof(scene1)&&decoded_bytes<=COH_NET_DECODED_MAX);
    CHECK(capacity>=16&&capacity<=COH_NET_MESSAGE_MAX);
    uint8_t *body=malloc(decoded_bytes);CHECK(body);
    memset(body,0x5a,decoded_bytes);memcpy(body,scene1,sizeof(scene1));
    /* A deterministic incompressible section also exercises sibling merge;
     * the remainder keeps the complete wire body within the legacy budget. */
    uint32_t rng=UINT32_C(0x26c0ffee);
    for(size_t i=sizeof(scene1);i<decoded_bytes&&i<sizeof(scene1)+8192;i++){
        rng=rng*UINT32_C(1664525)+UINT32_C(1013904223);body[i]=(uint8_t)(rng>>24);
    }
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
