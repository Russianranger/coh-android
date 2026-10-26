"""Summarize 0090 camera/player observations, without deciding rendering success."""
import json
import math
import re

import world_model_report

FLOAT = r'-?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?'
VEC = rf'{FLOAT},{FLOAT},{FLOAT}'
CAMERA = re.compile(rf'frame=([0-9]+) camera=({VEC}) view0=({VEC}) view1=({VEC}) view2=({VEC}) view3=({VEC}) player=([01]) player_svr_idx=(-?[0-9]+) player_pos=({VEC}) player_net_ipos=(-?[0-9]+,-?[0-9]+,-?[0-9]+)')


def summarize(lines):
    lines=list(lines)
    models=world_model_report.summarize(lines)
    failures=[] if models['observations_valid'] else ['matching model/draw observations invalid']
    samples=[];count=0
    for index,line in enumerate(lines,1):
        if not line.endswith('\n'):continue  # model summary rejects all torn records
        try:record=json.loads(line)
        except (ValueError,TypeError):continue
        if not isinstance(record,dict) or record.get('stage')!='world.camera':continue
        count+=1
        if count>8:continue
        text=record.get('text');m=CAMERA.fullmatch(text) if isinstance(text,str) and len(text)<=1024 else None
        if not m or type(record.get('tid')) is not int or record['tid']<0:
            failures.append(f'invalid camera record {index}');continue
        frame=int(m[1]);camera=[float(v) for v in m[2].split(',')]
        view=[[float(v) for v in m[j].split(',')] for j in range(3,7)]
        present=bool(int(m[7]));player_pos=[float(v) for v in m[9].split(',')]
        if (any(not math.isfinite(v) for row in [camera,player_pos,*view] for v in row)
                or samples and frame<=samples[-1]['frame']):
            failures.append(f'inconsistent/nonfinite camera record {index}');continue
        # Mat4 stores basis rows 0..2 and translation row3. Report residuals,
        # without thresholds or a conclusion about culling/terrain pixels.
        camera_view=[sum(camera[k]*view[k][axis] for k in range(3))+view[3][axis] for axis in range(3)]
        if any(not math.isfinite(v) for v in camera_view):
            failures.append(f'nonfinite camera transform {index}');continue
        distance=math.dist(camera,player_pos) if present else None
        if distance is not None and not math.isfinite(distance):
            failures.append(f'nonfinite camera/player distance {index}');continue
        samples.append(dict(frame=frame,tid=record['tid'],camera=camera,view=view,
            player_present=present,player_svr_idx=int(m[8]),player_pos=player_pos,
            player_net_ipos=[int(v) for v in m[10].split(',')],camera_in_view=camera_view,
            camera_player_distance=distance))
    if count>8:failures.append('camera sample bound exceeded')
    if not samples or count!=len(samples) or len(samples)!=len(models['samples']):
        failures.append('missing matching camera/model samples')
    for camera,model in zip(samples,models['samples']):
        if (camera['frame'],camera['tid'])!=(model['frame'],model['tid']):
            failures.append('camera/model frame or thread mismatch')
    return dict(scope='sampled_camera_player_inputs_only',observations_valid=not failures,
        sample_count=count,failure_count=len(failures),failures=failures[:16],samples=samples,
        cause_established=False,rendering_acceptance_changed=False)
