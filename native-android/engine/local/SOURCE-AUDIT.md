# Existing Android development mode source audit

Baseline: `132a813df53d94c38b441932f85ec42741123abf`.
`source-pins.json` records LF-normalized hashes; the checker refuses changed
source/launcher policy until it is reviewed and repinned.

- `Game/src/clientcomm/authclient.c:482–506`: `authLogin` clears `auth_info`,
  bypasses AuthServer when using the explicit DB address, and builds one shard.
- `Game/src/clientcomm/dbclient.c`: `dbConnect` sends the zero UID/cookie
  original LOGIN fields; `handleSendPlayers:248` adopts the genuine returned
  UID. `dbChoosePlayer:750` sends the selected slot/name and local-map override.
- `DBServer/src/clientcomm.c:875–955`: protocol mismatch is rejected before
  fake-auth; explicit fake-auth honors the caller's development stamp override;
  UID zero is assigned by `genFakeAuthId` and stored only after successful
  server login processing. The native module never reproduces that hash.
- `DBServer/src/clientcomm.c:479`: `getEnts_sendPlayers` sends the actual
  account UID as the first field.
- `DBServer/src/clientcomm.c:2041–2059`: nonzero local-map IP overrides saved
  destination selection. The native owner sends zero and follows MAP_CONNECT.
- `Common/comm_backend.h`: DB protocol 20110614, client UDP port 7000.
- `Common/ClientLogin/clientcommLogin.c:68–74`: listener encryption follows
  `packetCanUseEncryption()`, independently of fake account authentication.
- `libs/UtilitiesLib/src/network/net_version.c`: default NetLink version 5,
  outbound compression disabled by default, separate control-command encoding.
- `android/native/client-launcher.c:131–147`: current launcher adds
  `-noversioncheck 1` only to its explicit local-login/character profiles.
- `android/guest/client_login_diagnostic.py`: records this as
  `explicit_dev_stamp_comparison_skipped`, private-loopback fake-auth only.
- `android/guest/game_diagnostic.py`: generates advertised loopback, fake-auth
  enabled and queue-server disabled for the existing development profile.

The existing strict AuthServer receipt and map authorization paths remain
separate. Local development provenance never asserts Gate 26 authentication.
