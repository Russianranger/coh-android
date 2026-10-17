# Historical name/source-file correlation

Audit helper commit: see separate `inspect_trick_associations.py` source commit. Exact audit result SHA256 `3116f9d80c8b985649f9f073704ee75ec5fb7d2de3da45cbaa81714b5b2e94f3`.

All 5,994 named Trick observations in exact captured SERVER resources have a case-insensitive name and source filename match in the retained historical CLIENT cache. Of these, 1,959 occur on the exact 3,083-row root-model ledger; 4,035 are other observations. The latter are **not** classified unreachable because the model ledger alone does not cover arbitrary graph/definition membership. Full per-historical-row captured source ordinals are retained in the JSON. No unmatched name or source file was observed in this exact cohort.

The helper bounds reads to exact cache/resource/ledger byte sizes, verifies all three SHA256s, validates every root model ordinal/name/GEO/partition association, checks source hashes before helper execution and after processing, readmits exact inputs, and refuses changed bytes in each input. It reuses the independently qualified complete Trick wire grammar and captured resource format reader. The historical owner follows source reverse-order/default-casefold name registration; no original stash primitive execution is implied.

This is a correlation across historical and captured source inputs. It proves no generation equality, active CLIENT dictionary ownership, animation binding, numeric/flag postprocess parity, LOD resolution, material/asset/capability authority or live world permission. No Android/native execution is claimed by this Python audit. Current generation and source identity joins remain necessary even when all names match.
