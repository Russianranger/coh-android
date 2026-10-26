static int run(int padded, int want) {
    Model m={0},*model=&m;
    // Root, two leaves, eight 32-bit child offsets, then three U16 indices.
    U8 disk[80]={0}; U32 kids[8]={12,0,0,24,0,0,0,0};
    U32 root[3]={36,68,1}, leaf1[3]={0,70,1}, leaf2[3]={0,72,1};
    U16 indices[3]={0,1,2};
    memcpy(disk,root,12); memcpy(disk+12,leaf1,12); memcpy(disk+24,leaf2,12);
    memcpy(disk+36,kids,32); memcpy(disk+68,indices,6);
    model->pack.grid.unpacksize=padded?80:74; model->tri_count=3;
    U32 uiGridAllocSize,uiCTrisAllocSize,uiTotalAllocSize;
    /* ALLOCATION_SIZES */
    void *pTotalAlloc=calloc(1,uiTotalAllocSize); assert(pTotalAlloc);
    size_t reserve=GEO_POLYCELL_NATIVE_RESERVE(model->pack.grid.unpacksize);
    U8 *raw=(U8*)pTotalAlloc+reserve;
    memcpy(raw,disk,model->pack.grid.unpacksize);
    PolyCell *cell=polyCellUnpackFile(model,raw,model->pack.grid.unpacksize,pTotalAlloc,reserve);
    assert(cell->children[3]->tri_idxs[0]==2);
    U8 *before=malloc(uiGridAllocSize); assert(before); memcpy(before,pTotalAlloc,uiGridAllocSize);
    /* TRIANGLE_START */
    memset(model->ctris,0x53,uiCTrisAllocSize);
    int intact=memcmp(before,pTotalAlloc,uiGridAllocSize)==0;
    int after=(U8*)model->ctris==(U8*)pTotalAlloc+uiGridAllocSize;
    if(intact) assert(cell->children[0]->tri_idxs[0]==1 && cell->children[3]->tri_idxs[0]==2);
    printf("PolyCell allocation: raw=%u grid=%u triangle_offset=%zu preserved=%d expected=%d\n",
        model->pack.grid.unpacksize,uiGridAllocSize,(size_t)((U8*)model->ctris-(U8*)pTotalAlloc),intact,want);
    free(before);free(pTotalAlloc);return intact==want && after==want;
}
int main(int argc,char **argv) { int want=atoi(argv[1]); return run(0,want)&&run(1,want)?0:1; }
