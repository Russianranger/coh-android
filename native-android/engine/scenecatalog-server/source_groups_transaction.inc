/* Private diagnostic hook; include after source_groups_eligibility.inc.
 * Static state is serialized on the original worldSendUpdate owner thread.
 * Disabled unless a nonshipping caller installs all callbacks. No callback may
 * yield, load, alter source/link/packet or retain any borrowed pointer.
 */
#ifndef COH_SOURCE_GROUPS_TRANSACTION_INCLUDED
#define COH_SOURCE_GROUPS_TRANSACTION_INCLUDED
#define COH_GROUPS_TRANSACTION_MAX_BYTES (16u*1024u*1024u)
typedef struct CohGroupsTransactionHooks {
 /* begin supplies a nonzero observation identity; 0 disables this observation.
  * It must first establish owned run/source/quiescence and source-association
  * records. This seam alone cannot prove those properties. */
 unsigned (*begin)(void*,const NetLink*,int);
 CohGroupsEligibilityOutput record;
 /* finish receives exact original pre-pktSend logical packet including command.
  * No framing/compression/normalization is invented here. Partial final-byte
  * unused bits are excluded by bits. Sink must copy before returning. */
 int (*finish)(void*,unsigned,const unsigned char*,unsigned,unsigned,unsigned,
              const CohGroupsEligibilityReport*);
 void (*abort)(void*,unsigned);
 void*context;
} CohGroupsTransactionHooks;
static CohGroupsTransactionHooks coh_groups_transaction_hooks;
static unsigned coh_groups_transaction_active;
static CohGroupsEligibilityReport coh_groups_transaction_report;
static void coh_groups_transaction_begin(const NetLink*link,int full)
{
 CohGroupsTransactionHooks*h=&coh_groups_transaction_hooks;unsigned id;
 /* No reentrant invocation; do not overwrite the outer provisional capture. */
 if(coh_groups_transaction_active||!h->begin||!h->record||!h->finish||!h->abort)return;
 id=h->begin(h->context,link,full);if(!id)return;
 if(!coh_source_groups_eligibility(link,full,id,h->record,h->context,&coh_groups_transaction_report)){h->abort(h->context,id);return;}
 coh_groups_transaction_active=id;
}
static void coh_groups_transaction_finish(const Packet*pak)
{
 CohGroupsTransactionHooks*h=&coh_groups_transaction_hooks;unsigned id=coh_groups_transaction_active,bits,bytes;
 if(!id)return;coh_groups_transaction_active=0;
 bits=pak->stream.bitLength;bytes=bits/8u+(bits%8u!=0);
 if(!bits||bytes>COH_GROUPS_TRANSACTION_MAX_BYTES||!pak->stream.data||pak->stream.errorFlags||!h->finish(h->context,id,pak->stream.data,bits,pak->stream.byteAlignedMode,(unsigned)pak->compress,&coh_groups_transaction_report))h->abort(h->context,id);
}
#endif
