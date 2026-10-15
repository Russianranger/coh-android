/* API-shaped HOST TEST SHIM ONLY. Android builds use the real NDK header. */
#ifndef COH_HOST_AAUDIO_H
#define COH_HOST_AAUDIO_H
#include <stdint.h>
typedef int32_t aaudio_result_t;
typedef int32_t aaudio_stream_state_t;
typedef int32_t aaudio_data_callback_result_t;
typedef struct AAudioStream AAudioStream;
typedef struct AAudioStreamBuilder AAudioStreamBuilder;
typedef aaudio_data_callback_result_t (*AAudioDataCallback)(AAudioStream*,void*,void*,int32_t);
typedef void (*AAudioErrorCallback)(AAudioStream*,void*,aaudio_result_t);
enum { AAUDIO_OK=0, AAUDIO_ERROR_TIMEOUT=-1, AAUDIO_DIRECTION_OUTPUT=0,
       AAUDIO_FORMAT_PCM_FLOAT=2, AAUDIO_SHARING_MODE_SHARED=1, AAUDIO_PERFORMANCE_MODE_LOW_LATENCY=12,
       AAUDIO_CALLBACK_RESULT_CONTINUE=0, AAUDIO_CALLBACK_RESULT_STOP=1,
       AAUDIO_STREAM_STATE_STARTED=4, AAUDIO_STREAM_STATE_STARTING=3,
       AAUDIO_STREAM_STATE_STOPPED=10, AAUDIO_STREAM_STATE_DISCONNECTED=13,
       AAUDIO_STREAM_STATE_CLOSED=12 };
aaudio_result_t AAudio_createStreamBuilder(AAudioStreamBuilder **);
aaudio_result_t AAudioStreamBuilder_delete(AAudioStreamBuilder *);
void AAudioStreamBuilder_setDirection(AAudioStreamBuilder *,int32_t);
void AAudioStreamBuilder_setFormat(AAudioStreamBuilder *,int32_t);
void AAudioStreamBuilder_setSampleRate(AAudioStreamBuilder *,int32_t);
void AAudioStreamBuilder_setChannelCount(AAudioStreamBuilder *,int32_t);
void AAudioStreamBuilder_setSharingMode(AAudioStreamBuilder *,int32_t);
void AAudioStreamBuilder_setPerformanceMode(AAudioStreamBuilder *,int32_t);
void AAudioStreamBuilder_setDataCallback(AAudioStreamBuilder *,AAudioDataCallback,void *);
void AAudioStreamBuilder_setErrorCallback(AAudioStreamBuilder *,AAudioErrorCallback,void *);
aaudio_result_t AAudioStreamBuilder_openStream(AAudioStreamBuilder *,AAudioStream **);
int32_t AAudioStream_getSampleRate(AAudioStream *);
int32_t AAudioStream_getChannelCount(AAudioStream *);
int32_t AAudioStream_getFormat(AAudioStream *);
int32_t AAudioStream_getFramesPerBurst(AAudioStream *);
int32_t AAudioStream_getBufferSizeInFrames(AAudioStream *);
aaudio_stream_state_t AAudioStream_getState(AAudioStream *);
aaudio_result_t AAudioStream_waitForStateChange(AAudioStream *,aaudio_stream_state_t,aaudio_stream_state_t *,int64_t);
aaudio_result_t AAudioStream_requestStart(AAudioStream *);
aaudio_result_t AAudioStream_requestStop(AAudioStream *);
aaudio_result_t AAudioStream_close(AAudioStream *);
int32_t AAudioStream_getXRunCount(AAudioStream *);
int64_t AAudioStream_getFramesRead(AAudioStream *);
int64_t AAudioStream_getFramesWritten(AAudioStream *);
aaudio_result_t AAudioStream_getTimestamp(AAudioStream *,int32_t,int64_t *,int64_t *);
#endif
