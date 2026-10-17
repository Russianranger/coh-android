#include "coh_runtime_bounds.h"
#include <string.h>
#define TRY(x) do{CohStatus s_=(x);if(s_!=COH_OK)return s_;}while(0)
static CohStatus tick(CohCancel c){return c.poll&&c.poll(c.context)?COH_CANCELLED:COH_OK;}
static int disjoint(const void *a,size_t an,const void *b,size_t bn){
    if(!an||!bn)return 1;
    uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
    if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 0;
    return x+an<=y||y+bn<=x;
}
static int add(size_t *n,size_t count,size_t width,size_t limit){
    if(!width)return 1;
    if(count>limit/width||*n>limit-count*width)return 0;
    *n+=count*width;return 1;
}
CohStatus coh_runtime_bounds_diagnose(const CohRuntimeGraph *g,CohRuntimeBoundsDefinition provider,
    void *context,const CohRuntimeBoundsBudget *budget,CohCancel cancel,CohRuntimeBoundsRow *rows,
    size_t row_cap,CohGroupBoundsChild *children,size_t child_cap,CohRuntimeBoundsFrame *stack,
    size_t stack_cap,CohRuntimeBoundsReport *out){
    CohRuntimeGraphReport graph;CohRuntimeBoundsReport report={0};size_t bytes=0,total;
    if(!g||!provider||!budget||!rows||!children||!stack||!out)return COH_INVALID;
    TRY(coh_runtime_graph_report(g,&graph));TRY(coh_runtime_graph_binding(g,&report.graph));
    if(row_cap<graph.nodes||row_cap>COH_SG_DEFS_MAX+COH_RUNTIME_SNAPSHOT_EXTERNAL_MAX||child_cap>COH_SG_CHILDREN_MAX||
       stack_cap<COH_SG_DEPTH_MAX+1u||stack_cap>COH_SG_DEPTH_MAX+1u)return COH_LIMIT;
    CohBytes catalog,snapshot;TRY(coh_runtime_graph_sources(g,&catalog,&snapshot));
    const void *starts[]={rows,children,stack,budget,out,catalog.data,snapshot.data};
    size_t extents[]={row_cap*sizeof(*rows),child_cap*sizeof(*children),stack_cap*sizeof(*stack),sizeof(*budget),sizeof(*out),catalog.size,snapshot.size};
    for(unsigned n=0;n<7;n++)for(unsigned k=n+1;k<7;k++)
        if(!disjoint(starts[n],extents[n],starts[k],extents[k]))return COH_INVALID;
    if(!budget->aggregate_limit||budget->aggregate_limit>COH_SG_TRANSACTION_MAX)return COH_LIMIT;
    if(!add(&bytes,row_cap,sizeof(*rows),budget->aggregate_limit)||
       !add(&bytes,child_cap,sizeof(*children),budget->aggregate_limit)||
       !add(&bytes,stack_cap,sizeof(*stack),budget->aggregate_limit)||
       !add(&bytes,1,sizeof(report)+sizeof(graph)+sizeof(CohRuntimeGraphNode)*2u+
            sizeof(CohRuntimeGraphRoot)+sizeof(CohRuntimeGraphChild)+sizeof(CohGroupBoundsInput)+4096u,
            budget->aggregate_limit))return COH_LIMIT;
    total=budget->retained_bytes;
    /* Caller charges input owners separately; graph payload charged here. */
    if(!add(&total,1,graph.owned_bytes,budget->aggregate_limit)||
       !add(&total,1,bytes,budget->aggregate_limit))return COH_LIMIT;
    report.workspace_bytes=bytes;report.aggregate_reserved_bytes=total;
    memset(rows,0,row_cap*sizeof(*rows));
    for(uint32_t root_slot=0;root_slot<graph.source.root_slots;root_slot++){
        CohRuntimeGraphRoot root;size_t depth=0;TRY(tick(cancel));TRY(coh_runtime_graph_root(g,root_slot,&root));
        if(!root.active)continue;
        if(root.node>=graph.nodes)return COH_STATE;
        report.active_roots++;
        if(rows[root.node].color!=2){stack[0]=(CohRuntimeBoundsFrame){root.node,0};depth=1;}
        while(depth){
            CohRuntimeBoundsFrame *f=&stack[depth-1];CohRuntimeGraphNode node;CohRuntimeBoundsRow *row=&rows[f->node];
            TRY(tick(cancel));TRY(coh_runtime_graph_node(g,f->node,&node));
            if(!node.in_use||!node.reachable||node.child_first>graph.edges||node.child_count>graph.edges-node.child_first)return COH_STATE;
            if(node.child_count>child_cap)return COH_LIMIT;
            if(!row->color){row->color=1;if(depth-1>report.maximum_first_visit_depth)report.maximum_first_visit_depth=(uint32_t)(depth-1);}
            if(f->next<node.child_count){
                CohRuntimeGraphChild child;TRY(coh_runtime_graph_child(g,node.child_first+f->next,&child));f->next++;
                if(child.target>=graph.nodes)return COH_STATE;
                if(rows[child.target].color==1)return COH_INVALID;
                if(rows[child.target].color==2)continue;
                if(depth==stack_cap)return COH_LIMIT;
                stack[depth++]=(CohRuntimeBoundsFrame){child.target,0};continue;
            }
            row->result=COH_RB_COMPUTED;
            for(uint32_t n=0;n<node.child_count;n++){
                CohRuntimeGraphChild child;TRY(tick(cancel));TRY(coh_runtime_graph_child(g,node.child_first+n,&child));
                if(child.target>=graph.nodes)return COH_STATE;
                if(rows[child.target].color!=2)return COH_STATE;
                if(rows[child.target].result!=COH_RB_COMPUTED&&rows[child.target].result!=COH_RB_CAPTURED_FUTURE)row->result=COH_RB_CHILD_BLOCKED;
                children[n].bounds=&rows[child.target].bounds;memcpy(children[n].matrix,child.matrix,sizeof(children[n].matrix));
            }
            if(node.external){
                CohRuntimeExternalBounds observed;CohStatus status=coh_runtime_graph_external_bounds(g,f->node,&observed);
                if(status==COH_NOT_FOUND||status==COH_UNSUPPORTED)row->result=COH_RB_FUTURE_BOUNDS_MISSING;
                else if(status!=COH_OK)return status;
                else {
                    for(unsigned n=0;n<3;n++)if(observed.live.min[n]>observed.live.max[n])return COH_INVALID;
                    if(observed.live.radius<0)return COH_INVALID;
                    memcpy(row->bounds.min,observed.live.min,sizeof(row->bounds.min));memcpy(row->bounds.max,observed.live.max,sizeof(row->bounds.max));memcpy(row->bounds.mid,observed.live.mid,sizeof(row->bounds.mid));row->bounds.radius=observed.live.radius;
                    row->result=COH_RB_CAPTURED_FUTURE;
                }
            }
            if(row->result==COH_RB_COMPUTED){
                CohGroupBoundsInput input={0};CohStatus status=provider(context,f->node,&node,&input);
                if(status==COH_NOT_FOUND||status==COH_UNSUPPORTED)row->result=COH_RB_DEFINITION_MISSING;
                else if(status!=COH_OK)return status;
                else {
                    if(input.model_present!=node.source_model_present)return COH_STATE;
                    if(input.pre_alloc)return COH_UNSUPPORTED;
                    input.children=children;input.child_count=node.child_count;
                    input.cancelled=cancel.poll;input.context=cancel.context;
                    CohGroupBoundsStatus s=coh_group_bounds_compute(&input,&row->bounds);
                    if(s==COH_GROUP_BOUNDS_CANCELLED)return COH_CANCELLED;
                    if(s==COH_GROUP_BOUNDS_LIMIT)return COH_LIMIT;
                    if(s!=COH_GROUP_BOUNDS_OK)return COH_INVALID;
                }
            }
            row->color=2;report.visited++;
            if(row->result==COH_RB_COMPUTED)report.computed++;
            else if(row->result==COH_RB_CAPTURED_FUTURE)report.captured_future++;
            else if(row->result==COH_RB_FUTURE_BOUNDS_MISSING)report.future_missing++;
            else if(row->result==COH_RB_DEFINITION_MISSING)report.definition_missing++;
            else report.child_blocked++;
            depth--;
        }
        if(rows[root.node].result==COH_RB_COMPUTED||rows[root.node].result==COH_RB_CAPTURED_FUTURE)report.computed_roots++;else report.blocked_roots++;
    }
    TRY(tick(cancel));*out=report;return COH_OK;
}
