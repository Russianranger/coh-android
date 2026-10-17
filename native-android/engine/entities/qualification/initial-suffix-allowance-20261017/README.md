Suffix scratch acquisition follow-up
====================================

Source commit 2591062922d5e823306fe6d3a23292163a8a8bf8. F review requested explicit pre-allocation allowance and partial-error ownership cleanup. The new acquire ABI supplies minimum bytes and maximum charged bytes, respecting each child limit before allocation. Non-OK acquisition with any populated loan field triggers exactly one release. Header explicitly forbids hidden unreported ownership and requires providers to refuse before exceeding allowance.

All tested inputs equal committed blobs. Release/ASan/UBSan each pass9991checks,55sourcefragment compositions,95cuts,125mutations,2390matched acquisitions/releases; peak charged loan5993424bytes. Tests include error-after-allocation and a provider that refuses the oversized badge scratch before allocation. C++/native frame checks pass. Earlier receipts are preserved and describe their earlier source/API faithfully. All no-actor/no-ACK/dependency-closure limits remain.
