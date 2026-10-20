# Observed server entity diagnostic box

The initial packet already carries a complete absolute position/quaternion before
the unresolved costume. `coh_initial_pose_probe_with_sample` retains that decoded
position for a local visual observation while preserving the original numeric
probe/report. It clears the sample on syntax/profile refusal. No default spawn,
costume, complete actor or application ACK is supplied. The existing create
parser and real selected-self/raw-DBID comparison must supply the marker index;
the root Combined bridge owns that join and must clear on a fresh attempt,
disconnect and return. Raw coordinates stay outside the old protocol JSON.

`SessionNative.observedEntity(handle,index,x,y,z)` updates one 16-byte visual
observation under the existing mutex. `clearObservedEntity` retires it. While
active, the camera and Atlas radius query follow the decoded coordinate, the
offline character is hidden, and offline WALK/skinning updates pause. User
camera controls still work. The observed box never moves from local controller
movement. Clear restores the existing offline preview. The session snapshot
records active/index/source coordinate, update count and successful box draws;
it explicitly records complete_actor=false and application_ack=false.

The existing renderer draws a fixed orange 2x6x2 box. Its 8 static vertices and
36 indices occupy 592 bytes; it makes no geometry allocation and uses the
existing GLES buffers/queue in a separate one-draw pass. A 4-byte RGBA white
diagnostic texture is created once per Surface and retired on Surface loss.
Its bytes are included in the existing GPU payload estimate; driver/object
memory remains outside that payload estimate. No budget is increased. Session
state adds 32 bytes (index, position and two counters). The parser sample is
20 bytes. These are component payload counts, not process/device RSS/PSS.

Original offline startup pixel/transform checks run at their original private
benchmark camera. Visible observed frames subsequently use the actual server
coordinate. If the retained Atlas subset has no geometry within that radius,
the observed path permits an empty environment and still draws the actual
marker; the strict offline selection behavior remains unchanged. This does not
claim whole-Atlas rendering or invented environment geometry.

Focused checks:

```sh
python3 native-android/engine/renderer/check_debug_entity.py \
  --source-root . --work /tmp/observed-entity-host \
  --output /tmp/observed-entity-host.json
python3 native-android/session-client/tools/check_observed_entity.py \
  --fixtures /tmp/observed-entity-host/fixtures.bin \
  --work /tmp/observed-entity-session \
  --output /tmp/observed-entity-session.json
```

Release/ASan/UBSan each pass 15,282 source-pose/renderer controls over 91
source-produced fixtures, 62 complete pose draws and 8,712 truncated extents.
The original numeric report is identical. The exact production setter/camera/
scene-draw bodies pass 135 additional controls and 33 observed-box draws in each
mode with the real source camera and explicit GL/JNI/storage call observers.
These are host tests using labeled synthetic source-producer fixtures, not a
physical server transaction or actual Android/GLES execution. The existing
stream-GPU checker now compiles the new renderer dependency. Coordinator CI must
compile the complete Session DSO and exercise the real Surface path.

Next physical check: launch the same server, select the existing character and
capture its initial update. An orange box should replace the offline character
at the decoded selected-self coordinate, with observed_server_entity.active=true
and box_draws increasing. Orbit the camera, Home/resume and return; verify GL
cleanup and that a new attempt clears the old marker. A costume refusal can
remain visible alongside the box. This observation does not close the missing
full costume/character transaction or enable an application full-update ACK.
