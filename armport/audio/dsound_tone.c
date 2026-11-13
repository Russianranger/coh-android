/* CI probe: play a known tone through the game's audio path under Wine.
 *
 * The CI client data has no sound files (the zone sound packs are device
 * assets), so the game itself only feeds silence to the bridge in CI. This
 * program uses DirectSound exactly as the client does (sound_sys.c: priority
 * cooperative level, a primary buffer set to 44.1 kHz 16-bit stereo and played
 * looping) and plays 1.5 s of a 440 Hz left / 660 Hz right tone in a secondary
 * buffer. Wine mixes it through winealsa.drv, ALSA plug converts it to 48 kHz,
 * and the ArmPort plugin hands it to the CI protocol sink, which must see
 * non-zero samples on both channels.
 */
#include <windows.h>
#include <mmsystem.h>
#include <dsound.h>
#include <math.h>
#include <stdio.h>

#define RATE 44100
#define SECONDS 1.5

static int fail(const char *step, HRESULT hr)
{
    printf("ARMPORT_DSOUND_TONE_V1 result=fail step=%s hr=0x%08lx\n", step, (unsigned long)hr);
    fflush(stdout);
    return 2;
}

int main(void)
{
    LPDIRECTSOUND sound = NULL;
    LPDIRECTSOUNDBUFFER primary = NULL, tone = NULL;
    DSBUFFERDESC desc;
    WAVEFORMATEX format;
    void *first = NULL, *second = NULL;
    DWORD first_bytes = 0, second_bytes = 0, status = 0, frames = (DWORD)(RATE * SECONDS), i;
    HRESULT hr;
    int waited = 0;

    if (FAILED(hr = DirectSoundCreate(NULL, &sound, NULL)))
        return fail("create", hr);
    if (FAILED(hr = IDirectSound_SetCooperativeLevel(sound, GetDesktopWindow(), DSSCL_PRIORITY)))
        return fail("cooperative_level", hr);

    ZeroMemory(&format, sizeof(format));
    format.wFormatTag = WAVE_FORMAT_PCM;
    format.nChannels = 2;
    format.nSamplesPerSec = RATE;
    format.wBitsPerSample = 16;
    format.nBlockAlign = format.wBitsPerSample / 8 * format.nChannels;
    format.nAvgBytesPerSec = format.nSamplesPerSec * format.nBlockAlign;

    ZeroMemory(&desc, sizeof(desc));
    desc.dwSize = sizeof(desc);
    desc.dwFlags = DSBCAPS_PRIMARYBUFFER;
    if (FAILED(hr = IDirectSound_CreateSoundBuffer(sound, &desc, &primary, NULL)))
        return fail("primary_buffer", hr);
    if (FAILED(hr = IDirectSoundBuffer_SetFormat(primary, &format)))
        return fail("primary_format", hr);
    if (FAILED(hr = IDirectSoundBuffer_Play(primary, 0, 0, DSBPLAY_LOOPING)))
        return fail("primary_play", hr);

    ZeroMemory(&desc, sizeof(desc));
    desc.dwSize = sizeof(desc);
    desc.dwFlags = DSBCAPS_GLOBALFOCUS | DSBCAPS_GETCURRENTPOSITION2 | DSBCAPS_CTRLVOLUME;
    desc.dwBufferBytes = frames * format.nBlockAlign;
    desc.lpwfxFormat = &format;
    if (FAILED(hr = IDirectSound_CreateSoundBuffer(sound, &desc, &tone, NULL)))
        return fail("tone_buffer", hr);
    if (FAILED(hr = IDirectSoundBuffer_Lock(tone, 0, desc.dwBufferBytes, &first, &first_bytes,
                                            &second, &second_bytes, 0)))
        return fail("lock", hr);
    for (i = 0; i < first_bytes / format.nBlockAlign; i++) {
        double t = (double)i / RATE;
        short *frame = (short *)first + 2 * i;
        frame[0] = (short)(8000.0 * sin(2.0 * 3.14159265358979 * 440.0 * t));
        frame[1] = (short)(8000.0 * sin(2.0 * 3.14159265358979 * 660.0 * t));
    }
    if (FAILED(hr = IDirectSoundBuffer_Unlock(tone, first, first_bytes, second, second_bytes)))
        return fail("unlock", hr);
    if (FAILED(hr = IDirectSoundBuffer_Play(tone, 0, 0, 0)))
        return fail("tone_play", hr);
    /* Wait for the end of the buffer (bounded), then let the mixer drain. */
    do {
        Sleep(50);
        waited += 50;
        if (FAILED(hr = IDirectSoundBuffer_GetStatus(tone, &status)))
            return fail("status", hr);
    } while ((status & DSBSTATUS_PLAYING) && waited < 6000);
    Sleep(500);
    IDirectSoundBuffer_Stop(primary);
    IDirectSoundBuffer_Release(tone);
    IDirectSoundBuffer_Release(primary);
    IDirectSound_Release(sound);
    printf("ARMPORT_DSOUND_TONE_V1 result=%s frames=%lu waited_ms=%d\n",
           (status & DSBSTATUS_PLAYING) ? "timeout" : "pass", (unsigned long)frames, waited);
    fflush(stdout);
    return (status & DSBSTATUS_PLAYING) ? 3 : 0;
}
