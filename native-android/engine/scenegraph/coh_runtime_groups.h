#ifndef COH_RUNTIME_GROUPS_H
#define COH_RUNTIME_GROUPS_H
#include "runtime_graph.h"
#include "../scenecatalog/coh_catalog_owner.h"
typedef struct {size_t aggregate_limit,retained_bytes;} CohRuntimeGroupsBudget;
typedef struct {
    CohGroupsInspection groups;
    CohRepScenePrefix prefix;
    uint32_t graph_generation,catalog_generation,files_equal,emitted_definitions_equal,root_wires_equal;
    size_t aggregate_reserved_bytes;
    uint32_t source_generation_admitted,assets_admitted,world_authority;
} CohRuntimeGroupsReport;
/* Synchronous compatibility diagnostic for a complete new-world byte-aligned
 * normal GROUPS body, starting immediately after its normalized command. Uses
 * the original imported catalog for omitted saved definitions; every file0 record must be emitted; every emitted
 * definition must match exact retained source serialization, every file name
 * and bounds checksum must match, and every root slot/name/packed matrix wire
 * must match the audited runtime snapshot. Delta/absent files, sparse root
 * updates, changed definitions and another wire representation are refused.
 *
 * This proves compatibility of observed bytes only. The caller authenticates
 * the real transport/session separately; matching names/CRC/wire never proves
 * matching live asset/source generation or which files the server opened.
 * No certificate, publication, ACK, actor or world authority is produced.
 *
 * Graph, exact borrowed input owners and catalog owner remain alive/immutable
 * throughout; no retain or copy occurs. Owner catalog pointer+extent and actual
 * recorded graph/catalog bindings must agree. All controls/report/known input
 * spans are disjoint. Opaque owner/graph allocations are caller-disjoint from
 * controls and callback scratch. No allocations occur. Charge all other live
 * resources, allocation slack and callback/digest scratch in retained_bytes;
 * graph payload, owner payload, snapshot, wire and64KiB reserve are added here.
 * Counts cover named reservations, not process RSS. On ANY refusal report is
 * unchanged; reader is always unchanged. Run off rendering thread.
 */
CohStatus coh_runtime_graph_compare_groups(const CohRuntimeGraph *,const CohCatalogOwner *,
    const CohRepReader *,const CohRuntimeGroupsBudget *,CohRuntimeGroupsReport *);
#endif
