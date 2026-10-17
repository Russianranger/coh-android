# Standalone raw PowerInfo update staging

`coh_global_power_info` atomically stages the entire original PowerInfo wire
function, including the mandatory range terminator even when has_updates is
false. It retains ordered power definitions, CRCs (including zero), raw PowerRef
words, boost/global-boost metadata, ranges, active/enabled/usage/recharge events,
inspirations and boost inventory updates. It stops before PowerModeUpdate.

The caller owns two disjoint heap/arena PODs. Their combined size is 1,069,200
bytes; admission also charges input, caller-retained bytes and an 8 KiB stack
reservation against an 8 MiB maximum. Pool bounds and finite-float checks are
explicit native admission policies. Refusal preserves reader and output exactly.

The pinned entire original `entity_SendPowerInfoUpdate` and its range, power,
boost and event helpers emit 70 fixtures at aligned and unaligned cursors.
Native release, ASan and UBSan each passed 380,498 checks, including 61,200
truncations, 7,706 mutations and 2,000 random inputs. Original helper consumers
also round-trip power/status records. The whole original PowerInfo consumer is
not executed by this oracle. Evidence: qualification/power-info-20261017/host.json.

This is raw metadata, not a gameplay dictionary or applied server state. Actual
CRC/dictionary semantics, enclosing global-message offset, selected DBID/entity
generation, whole initial-update composition and actor publication remain open.
No READY, RECEIVED_CHARACTER or application ACK is enabled. No Android execution,
live-server acceptance or physical-device qualification is inferred.
