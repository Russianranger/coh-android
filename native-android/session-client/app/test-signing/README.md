# Public native debug test signer

`session-test.p12` is an intentionally public fixture, with its byte and
certificate identity in `signer.json`. It is used only by the native Session
Client's debug build. It grants no account or production access and must never
sign a production release. The alias and password are public test constants.

The accepted 0.1.0 test package used an ephemeral hosted debug key. Its private
key is unavailable. Version 0.2.0 therefore uses `org.coh.sessionclient.walk`
so it can install alongside the accepted client and retain all existing data.
This is the same Session Client source and native runtime. Future debug updates
of this application ID retain this signer; do not regenerate the fixture.
The Java namespace stays `org.coh.sessionclient` for JNI compatibility.

Package qualification verifies both the fixture bytes and exact APK signer.
Release signing and the conventional launcher are outside this fixture.
