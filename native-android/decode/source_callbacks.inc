/* Function bodies retained byte-for-byte from pinned Game/src/sound/ogg_decode.c. */
static size_t readbytes(void *dst, size_t struct_size, size_t num_structs, void* mfData)
{
    MemFile * mf = (MemFile *)mfData;
    size_t available, amt;

    if (!mf || !dst || !mf->mem || !struct_size ||
        mf->curr < 0 || mf->length < mf->curr)
        return 0;

    // Bound the item count before multiplying, as required by fread semantics.
    available = (size_t)(mf->length - mf->curr) / struct_size;
    if (num_structs > available)
        num_structs = available;
    amt = num_structs * struct_size;
    memcpy(dst,mf->mem + mf->curr,amt);

    mf->curr += (int)amt;
    return num_structs;
}
static int seekbytes(void *v_mf,ogg_int64_t amt,int whence)
{
    MemFile *mf = v_mf;
    ogg_int64_t base;

    if (!mf || mf->curr < 0 || mf->length < mf->curr)
        return -1;
    switch (whence) {
    case SEEK_SET: base = 0; break;
    case SEEK_CUR: base = mf->curr; break;
    case SEEK_END: base = mf->length; break;
    default: return -1;
    }
    // Check the offset before adding so even signed 64-bit extremes are safe.
    if (amt < -base || amt > (ogg_int64_t)mf->length - base)
        return -1;
    mf->curr = (int)(base + amt);
    return 0;
}
static int closebytes(void/*MemFile*/ *mf)
{
    return 0;
}
static long tellbytes(void *v_mf)
{
    MemFile *mf = v_mf;
    return mf->curr;
}
