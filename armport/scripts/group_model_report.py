"""Summarize bounded original lookup outcomes; never decide world acceptance."""
import json
import re

RESULT=re.compile(r'outcome=([0-2]) sample=([0-9]+) name="([!-~]{0,96})" geo="([!-~]{0,260})" model=([01]) loadstate=([0-9]+) verts=(-?[0-9]+) tris=(-?[0-9]+)')
NAMES=['library_entry_missing','model_lookup_missing','model_found']


def summarize(lines):
    failures=[];samples=[];seen=[set(),set(),set()];count=0
    for index,line in enumerate(lines,1):
        if not line.endswith('\n'):
            failures.append(f'torn record {index}');continue
        try:record=json.loads(line)
        except (ValueError,TypeError):
            failures.append(f'malformed record {index}');continue
        if not isinstance(record,dict):
            failures.append(f'non-object record {index}');continue
        if record.get('stage')!='group.model':continue
        count+=1
        if count>48:continue
        text=record.get('text');match=RESULT.fullmatch(text) if isinstance(text,str) and len(text)<512 else None
        if not match or type(record.get('tid')) is not int or record['tid']<0:
            failures.append(f'invalid lookup record {index}');continue
        kind,ordinal=int(match[1]),int(match[2]);name,path=match[3],match[4]
        found,loaded,verts,tris=map(int,match.group(5,6,7,8))
        if (not 1<=ordinal<=16 or ordinal in seen[kind]
                or any(c in name+path for c in ['"','\\'])
                or found!=(kind==2) or bool(path)!=(kind!=0)
                or kind!=2 and (loaded or verts or tris)
                or not 0<=loaded<=0xffffffff
                or not -(1<<31)<=verts<(1<<31) or not -(1<<31)<=tris<(1<<31)):
            failures.append(f'inconsistent lookup record {index}');continue
        seen[kind].add(ordinal)
        samples.append(dict(outcome=NAMES[kind],sample=ordinal,name=name,geo=path,model_present=bool(found),loadstate=loaded,verts=verts,tris=tris,tid=record['tid']))
    if count>48:failures.append('lookup sample bound exceeded')
    if not samples or count!=len(samples):failures.append('missing or invalid lookup samples')
    for kind,ordinals in enumerate(seen):
        if ordinals and ordinals!=set(range(1,max(ordinals)+1)):
            failures.append(f'missing ordinal for {NAMES[kind]}')
    return dict(scope='bounded_original_model_lookup_results_only',observations_valid=not failures,
        sample_count=count,sampled_outcome_counts={name:len(seen[i]) for i,name in enumerate(NAMES)},
        saturated_outcomes=[name for i,name in enumerate(NAMES) if len(seen[i])==16],
        samples=samples,failure_count=len(failures),failures=failures[:16],
        complete_model_census=False,cause_established=False,rendering_acceptance_changed=False)
