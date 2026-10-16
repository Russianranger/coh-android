/* Trusted synthetic runtime objects; original packet/CRC producers above. */
static void pktFree(Packet *p) { assert(p == &oracle_packet); }
static GroupDef snapshot_ext[66];
static GroupFile snapshot_prealloc, snapshot_foreign;
static GroupEnt snapshot_children[70];
static char snapshot_names[66][32];
static unsigned snapshot_ext_count;
static unsigned snapshot_checks;
static int snapshot_lookup;
static int snapshot_wrong_hash;
static GroupDef *groupDefFind(const char *name)
{
    unsigned i; int f, n;
    if (snapshot_wrong_hash) return NULL;
    for (f = 0; f < group_info.file_count; ++f)
        for (n = 0; n < group_info.files[f]->count; ++n)
            if (group_info.files[f]->defs[n] && group_info.files[f]->defs[n]->in_use &&
                !strcmp(group_info.files[f]->defs[n]->name, name)) return group_info.files[f]->defs[n];
    for (i = 0; i < snapshot_ext_count; ++i)
        if (!strcmp(snapshot_ext[i].name, name)) return &snapshot_ext[i];
    return NULL;
}
static int objectLibraryGetBounds(const char *name, GroupDef *out)
{
    (void)name;
    if (!snapshot_lookup) return 0;
    out->min[0] = -2; out->max[0] = 3; out->mid[0] = 0.5f;
    out->vis_dist = 100; out->radius = 4; out->lod_scale = 1;
    out->child_light = 1; return 1;
}
static char *objectLibraryPathFromObj(const char *name)
{
    (void)name;
    /* Distinct observation: path can exist even without raw-name bounds. */
    return "object_library/snapshot/test.geo";
}
#include "../scenecatalog/source_export.inc"
#include "source_snapshot.inc"

typedef struct SnapshotOutput { unsigned char *data; unsigned size, limit, fail_after; } SnapshotOutput;
static int snapshot_write(void *context, const unsigned char *bytes, unsigned size)
{
    SnapshotOutput *s = context;
    if (s->fail_after && s->size + size > s->fail_after) return 0;
    assert(size <= s->limit - s->size); memcpy(s->data + s->size, bytes, size); s->size += size;
    return 1;
}
static unsigned char snapshot_catalog[1u << 20], snapshot_sidecar[1u << 20], snapshot_wire[1u << 20];
static GroupDef snapshot_chain[130];
static GroupDef *snapshot_chain_ptrs[130];
static GroupEnt snapshot_chain_edges[130];
static char snapshot_chain_names[130][32];
static void snapshot_setup(unsigned external, unsigned roots_external)
{
    unsigned bits, footer[4], i; int f, n;
    assert(groups_original(2, 1, 0, snapshot_wire, &bits, footer));
    memset(snapshot_ext, 0, sizeof(snapshot_ext)); memset(&snapshot_prealloc, 0, sizeof(snapshot_prealloc));
    memset(snapshot_children, 0, sizeof(snapshot_children));
    snapshot_wrong_hash = 0; snapshot_lookup = 0; group_ptr = &group_info;
    snapshot_ext_count = external; group_info.pre_alloc = &snapshot_prealloc; snapshot_prealloc.pre_alloc = 1;
    for (f = 0; f < group_info.file_count; ++f)
        for (n = 0; n < group_info.files[f]->count; ++n)
            if (group_info.files[f]->defs[n]) group_info.files[f]->defs[n]->file = group_info.files[f];
    for (i = 0; i < external; ++i)
    {
        snprintf(snapshot_names[i], sizeof(snapshot_names[i]), "snapshot_future_%02u", i);
        oracle_simple(&snapshot_ext[i], 0, snapshot_names[i]);
        snapshot_ext[i].file = &snapshot_prealloc; snapshot_ext[i].pre_alloc = 1;
        snapshot_children[i].def = &snapshot_ext[i]; oracle_identity(snapshot_children[i].mat);
    }
    if (external)
    {
        /* Both id0 futures, plus repeated incidence of the first pointer. */
        snapshot_children[external] = snapshot_children[0];
        oracle_defs[0].entries = snapshot_children; oracle_defs[0].count = (int)external + 1;
        if (roots_external) oracle_refs[0].def = &snapshot_ext[external - 1];
    }
}
static int snapshot_pair(SnapshotOutput *catalog_out, SnapshotOutput *side_out, CohSourceSnapshotReport *report)
{
    CohSourceCatalogExportReport catalog;
    int status = coh_source_catalog_export(snapshot_write, catalog_out, 20261016u, &catalog);
    assert(!status);
    return coh_source_runtime_snapshot_export(snapshot_write, side_out, catalog_out->data, &catalog, report);
}
static void snapshot_save(const char *directory, const char *name, const unsigned char *bytes, unsigned size)
{
    char path[2048]; FILE *out;
    assert(snprintf(path, sizeof(path), "%s/%s", directory, name) > 0);
    out = fopen(path, "wb"); assert(out); assert(fwrite(bytes, 1, size, out) == size); assert(fclose(out) == 0);
}
static void snapshot_chain_setup(unsigned mode)
{
    unsigned i, count = mode == 4 ? 1 : mode == 5 ? 130 : mode == 6 ? 4 : 129;
    snapshot_setup(0,0); memset(snapshot_chain_edges,0,sizeof(snapshot_chain_edges));
    group_info.file_count = 1; group_info.ref_count = 1;
    group_info.files[0]->count = (int)count; group_info.files[0]->defs = snapshot_chain_ptrs;
    for (i=0;i<count;++i)
    {
        snprintf(snapshot_chain_names[i],sizeof(snapshot_chain_names[i]),"snapshot_chain_%03u",i);
        oracle_simple(&snapshot_chain[i],(int)i,snapshot_chain_names[i]);snapshot_chain_ptrs[i]=&snapshot_chain[i];
        snapshot_chain[i].file=group_info.files[0];
        if(i+1<count || mode==4 || mode==6)
        {
            unsigned next=i+1<count?i+1:0;
            if(mode==6 && i==1)continue;
            if(mode==6 && i==3)next=2;
            snapshot_chain[i].count=1;snapshot_chain[i].entries=&snapshot_chain_edges[i];
            snapshot_chain_edges[i].def=&snapshot_chain[next];oracle_identity(snapshot_chain_edges[i].mat);
        }
    }
    group_info.refs[0]->def=&snapshot_chain[0];
}
#define SNAP_CHECK(x) do { if (!(x)) {fprintf(stderr,"snapshot check failed %u: %s\n",__LINE__,#x);abort();} ++snapshot_checks; } while (0)
int main(int argc, char **argv)
{
    unsigned mode, f, n; CohSourceSnapshotReport report;
    SnapshotOutput cat, side;
    SNAP_CHECK(argc == 1 || argc == 2);
    for (mode = 0; mode < 4; ++mode)
    {
        snapshot_setup(mode ? 2 : 0, mode == 2);
        snapshot_lookup = mode == 3;
        if (mode == 3)
        {
            /* Reuse original GROUPS fixture 7's packed rotation/scale forms,
             * retaining this fixture's sparse root slots and object owners. */
            Vec3 angle0={0,0.25f,0},angle1={0,0.5f,0},angle2={0,0,0};
            unsigned indices[3]={0,2,3},i,j;
            for(i=0;i<3;++i)oracle_identity(oracle_refs[indices[i]].mat);
            createMat3YPR(oracle_refs[0].mat,angle0);createMat3YPR(oracle_refs[2].mat,angle1);
            oracle_refs[2].mat[3][0]=0.5f;oracle_refs[2].mat[3][1]=-3.5f;oracle_refs[2].mat[3][2]=1.25f;
            createMat3YPR(oracle_refs[3].mat,angle2);
            for(j=0;j<3;++j)oracle_refs[3].mat[j][0]=0;
            for(i=0;i<3;++i)
            {
                PackMat packed;
                SNAP_CHECK(packMat(oracle_refs[indices[i]].mat,&packed));
                SNAP_CHECK(packed.has_pyr && packed.has_scale==(i==2));
            }
        }
        cat = (SnapshotOutput){snapshot_catalog,0,sizeof(snapshot_catalog),0};
        side = (SnapshotOutput){snapshot_sidecar,0,sizeof(snapshot_sidecar),0};
        SNAP_CHECK(snapshot_pair(&cat, &side, &report) == 0);
        SNAP_CHECK(report.total_bytes == side.size && report.emitted_bytes == side.size);
        SNAP_CHECK(report.external_count == (mode ? 2u : 0u));
        SNAP_CHECK(report.root_slots == 4 && report.active_roots == 3);
        SNAP_CHECK(!memcmp(side.data, "COHRTS01", 8));
        SNAP_CHECK(coh_snapshot_u32(side.data + 24) == cat.size);
        SNAP_CHECK(snapshot_ext[0].id == 0 && snapshot_ext[1].id == 0);
        SNAP_CHECK(snapshot_prealloc.count == 0 && snapshot_prealloc.defs == NULL);
        /* Direct unchanged source producer parity for each captured matrix. */
        {
            unsigned at = 80, r, wirebytes, namebytes, j;
            for (r = 0; r < 4; ++r)
            {
                SNAP_CHECK(coh_snapshot_u32(side.data + at) == r);
                namebytes = coh_snapshot_u32(side.data + at + 20);
                wirebytes = coh_snapshot_u32(side.data + at + 28); at += 32;
                if (group_info.refs[r]->def)
                {
                    Packet *p = pktCreate(); pktSetCompression(p, 1); sendMat4(p, group_info.refs[r]->mat);
                    SNAP_CHECK(p->stream.bitLength == wirebytes * 8);
                    for (j = 0; j < 12; ++j)
                    {
                        unsigned char raw[4]; coh_snapshot_float(raw, &group_info.refs[r]->mat[j/3][j%3]);
                        SNAP_CHECK(!memcmp(raw, side.data + at + namebytes + j*4, 4));
                    }
                    SNAP_CHECK(!memcmp(p->stream.data, side.data + at + namebytes + 48, wirebytes)); pktFree(p);
                    at += namebytes + 48 + wirebytes;
                }
            }
            for (r = 0; r < report.external_count; ++r)
            {
                unsigned pathbytes = coh_snapshot_u32(side.data + at + 32);
                namebytes = coh_snapshot_u32(side.data + at + 16);
                wirebytes = coh_snapshot_u32(side.data + at + 24);
                SNAP_CHECK(coh_snapshot_u32(side.data + at) == r);
                SNAP_CHECK(coh_snapshot_u32(side.data + at + 4) == 0);
                SNAP_CHECK(coh_snapshot_u32(side.data + at + 8) == 15);
                at += 36 + 120 + namebytes + pathbytes;
                { Packet *p = pktCreate(); pktSetCompression(p, 1); sendDef(p, &snapshot_ext[r]);
                  SNAP_CHECK(p->stream.bitLength == wirebytes * 8);
                  SNAP_CHECK(!memcmp(p->stream.data, side.data + at, wirebytes)); pktFree(p); }
                at += wirebytes;
            }
            SNAP_CHECK(at == side.size);
        }
        if (argc == 2)
        {
            char name[64]; snprintf(name,sizeof(name),"snapshot-%u.cohcat",mode); snapshot_save(argv[1],name,cat.data,cat.size);
            snprintf(name,sizeof(name),"snapshot-%u.cohrts",mode); snapshot_save(argv[1],name,side.data,side.size);
        }
    }
    for(mode=4;mode<8;++mode)
    {
        snapshot_chain_setup(mode);
        cat=(SnapshotOutput){snapshot_catalog,0,sizeof(snapshot_catalog),0};
        side=(SnapshotOutput){snapshot_sidecar,0,sizeof(snapshot_sidecar),0};
        SNAP_CHECK(snapshot_pair(&cat,&side,&report)==0);
        if(argc==2)
        {
            char name[64];snprintf(name,sizeof(name),"snapshot-%u.cohcat",mode);snapshot_save(argv[1],name,cat.data,cat.size);
            snprintf(name,sizeof(name),"snapshot-%u.cohrts",mode);snapshot_save(argv[1],name,side.data,side.size);
        }
    }
    for (mode = 0; mode < 15; ++mode)
    {
        CohSourceCatalogExportReport catalog;
        snapshot_setup(mode == 0 ? 65 : 2, 0);
        cat = (SnapshotOutput){snapshot_catalog,0,sizeof(snapshot_catalog),0};
        side = (SnapshotOutput){snapshot_sidecar,0,sizeof(snapshot_sidecar),0};
        SNAP_CHECK(coh_source_catalog_export(snapshot_write,&cat,20261016u,&catalog) == 0);
        if (mode == 1) snapshot_ext[1].name = snapshot_ext[0].name;
        if (mode == 2) snapshot_ext[0].file = &snapshot_foreign;
        if (mode == 3) snapshot_ext[0].pre_alloc = 0;
        if (mode == 4) snapshot_prealloc.pre_alloc = 0;
        if (mode == 5) snapshot_wrong_hash = 1;
        if (mode == 6) group_ptr = NULL;
        if (mode == 7) group_info.refs[0]->def->in_use = 0;
        if (mode == 8) group_info.refs[0] = NULL;
        if (mode == 9) side.fail_after = 80;
        if (mode == 10) catalog.emitted_bytes--;
        if (mode == 11) snapshot_catalog[36] ^= 1;
        if (mode == 12) { unsigned bits=0x7fc00000u;memcpy(&group_info.refs[0]->mat[0][0],&bits,4); }
        if (mode == 13) { unsigned bits=0x7f800000u;memcpy(&snapshot_ext[0].radius,&bits,4); }
        if (mode == 14) { unsigned bits=0x7fc00000u;snapshot_ext[0].count=1;snapshot_ext[0].entries=&snapshot_children[69];snapshot_children[69].def=&snapshot_ext[1];oracle_identity(snapshot_children[69].mat);memcpy(&snapshot_children[69].mat[0][0],&bits,4); }
        SNAP_CHECK(coh_source_runtime_snapshot_export(snapshot_write,&side,snapshot_catalog,&catalog,&report) != 0);
        SNAP_CHECK(mode == 9 || side.size == 0);
    }
    snapshot_setup(2,0);
    for (f=0; f<(unsigned)group_info.file_count; ++f)
        for (n=0; n<(unsigned)group_info.files[f]->count; ++n)
            SNAP_CHECK(!group_info.files[f]->defs[n] || group_info.files[f]->defs[n]->file == group_info.files[f]);
    if(argc==2)
    {
        const char *expect="{\"schema\":1,\"fixtures\":[{\"id\":0,\"expected_status\":0},{\"id\":1,\"expected_status\":0},{\"id\":2,\"expected_status\":0},{\"id\":3,\"expected_status\":0},{\"id\":4,\"expected_status\":1,\"reason\":\"reachable_cycle\"},{\"id\":5,\"expected_status\":4,\"reason\":\"depth129\"},{\"id\":6,\"expected_status\":0,\"reason\":\"unreachable_cycle\"},{\"id\":7,\"expected_status\":0,\"reason\":\"depth128\"}]}\n";
        snapshot_save(argv[1],"fixture-expected.json",(const unsigned char*)expect,(unsigned)strlen(expect));
    }
    printf("{\"passed\":true,\"checks\":%u,\"fixtures\":8,\"source_snapshot_only\":true,\"runtime_executed\":false}\n",snapshot_checks);
    return 0;
}
