# Exact hosted PostgreSQL18.6 package revision

Actual run39078358295 stopped before runtime startup because18.6-3.pgdg24.04+1 was absent from the signed main index. The exact available18.6-1.pgdg24.04+2 packages are pinned for server, matching client and libpq5. This changes packaging revision, not the PostgreSQL18.6 format used by the original ARM dump180006.

Root verified the official PGDG key fingerprint, gpgv InRelease signature, signed compressed+uncompressed index hashes and all three exact stanzas. D independently matched package sizes/hashes and dependency closure. Hosted acquisition still uses APT signature verification and compares each complete .deb to its pinned SHA256 before installation. The exact original fixture, MapServer observer and DbServer donor are unchanged. No original runtime/capture ran in the failed job.

Retained public InRelease, key, exact Packages.gz and pins.json allow offline membership/signature rechecking. This evidence is not an executed database or scene qualification.
