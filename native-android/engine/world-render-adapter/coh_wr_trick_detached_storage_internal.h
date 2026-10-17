/* Private detached metadata; all offsets address the owned exact suffix. */
struct CohWrTrickDetached{CohWrTrickReport report;CohWrTrickDetachedReport detached;CohBytes bytes;Row rows[COUNT];uint32_t index[COUNT];};
