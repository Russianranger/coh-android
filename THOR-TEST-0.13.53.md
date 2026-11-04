# Thor test: COH Atlas Gameplay 0.13.53 (ARM64 client): game audio

0.13.53 is 0.13.52 plus game audio. If you have not tested 0.13.52 yet, this
sheet covers both. Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.53".

## What changed since 0.13.52

| Change | Default | Expected effect |
|---|---|---|
| Game audio | on (`Game audio (sound and music through Android)`) | Login music, zone ambience, footsteps and power sounds through the Thor's speakers or headphones, at the media volume. Untick it to start without audio, as before |

How it works: the game's DirectSound goes through Wine's ALSA driver to a small
playback plugin in the guest, which hands the sound to an Android AudioTrack
in the app. It is the same bridge as your TRASC/LSB apps. In CI the sound only
reaches a test receiver; hearing it is the device check.

## Steps

1. Install 0.13.53 over 0.13.52 (or 0.13.51), then tap **Set up / update runtime** once.
2. Media volume up. `Game audio` is ticked.
3. **Session 1:** reopen the hero. Listen at the login screen and in Atlas:
   music, ambience, your footsteps, a power or two, the monorail. Take the
   monorail to King's Row (watch the NPCs and cars) and back. Note crackling,
   stutter, delay against the picture, or sound that stops after zoning.
   Save/logout, Finish, **export**.
4. **Session 2 (only if session 1 had a problem):** untick `Game audio`,
   reopen and check that the problem is gone. Save/logout, Finish, **export**.

The 0.13.52 sessions (saved file list on the second start, test server) still
apply; see [THOR-TEST-0.13.52.md](THOR-TEST-0.13.52.md).

## Report

What you heard (or did not), FPS or loading changes you noticed with audio on,
and the exports. Fields I will read: `client_audio_bridge` in the Android
report (streams, frames, non-zero samples, underruns, events), `client_audio`
in the guest report, the client log's `ARMPORT_NET_CLOCK_V1` lines, and each
server process's memory (`rss_kib` in `server-metrics.jsonl`), which decides
how many zones can stay loaded on the Thor.
