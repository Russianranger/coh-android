#!/usr/bin/env python3
"""Exercise shipped tap predicates against Android Material accessibility text.

These are source-independent XML/event fixtures representing observed Android
behavior. This is a host selector regression test, not an Android/device pass.
"""
import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--observed-ui',type=Path)
    args=parser.parse_args()
    path=Path(__file__).with_name('emulator_check.py')
    spec=importlib.util.spec_from_file_location('shipped_session_tap_predicates',path)
    driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
    checks=0
    def check(value,label):
        nonlocal checks
        checks+=1
        assert value,label
    xml=f'''<hierarchy>
    <node class="android.widget.Button" package="{driver.PACKAGE}" text="RESET ACTOR" enabled="true" clickable="true" bounds="[10,280][292,375]"/>
    <node class="android.widget.Button" package="{driver.PACKAGE}" text="RECREATE" enabled="true" clickable="true" bounds="[310,280][532,375]"/>
    <node class="android.widget.Button" package="{driver.PACKAGE}" text="EXPORT REPORT" enabled="true" clickable="true" bounds="[550,280][879,375]"/>
    </hierarchy>'''
    nodes=list(ET.fromstring(xml).iter('node'))
    for label,event in [('Reset actor','reset_requested'),('Recreate','recreate_requested'),('Export report','export_requested')]:
        matched=driver.button_nodes(nodes,label)
        check(len(matched)==1,'Material uppercase button: '+label)
        check(driver.bounds(matched[0])[2]>driver.bounds(matched[0])[0],'Positive actual button bounds: '+label)
        original=deepcopy(matched[0]);original.set('text',label)
        check(driver.button_nodes([original],label)==[original],'Original sentence-case button: '+label)
        for key,value in [('package','org.coh.sessionclient'),('enabled','false'),('clickable','false'),('text',label+' again')]:
            wrong=deepcopy(original);wrong.set(key,value)
            check(driver.button_nodes([wrong],label)==[],'Reject unrelated or unavailable target '+key+': '+label)
        receipt={'events':[{'sequence':11,'type':event}]}
        check(driver.button_listener(receipt,10,event)==receipt['events'][0],'Exact action callback: '+label)
        check(driver.button_listener(receipt,11,event) is None,'Stale callback cannot qualify: '+label)
    check(driver.button_nodes(nodes,'Reset')==[],'Partial labels cannot target another button')
    check(driver.button_listener({'events':[{'sequence':12,'type':'render_returned'}]},10,'recreate_requested') is None,
          'Worker completion cannot qualify an action tap')
    for events,label in [([{'sequence':12,'type':'reset_requested'}],'Wrong listener'),
                         ([{'sequence':12,'type':'recreate_requested'},{'sequence':13,'type':'recreate_requested'}],'Duplicate listener'),
                         ([{'sequence':12,'type':'recreate_requested'},{'sequence':13,'type':'export_requested'}],'Multiple action listeners')]:
        try:
            driver.button_listener({'events':events},10,'recreate_requested')
        except AssertionError:
            check(True,label+' rejected')
        else:
            check(False,label+' incorrectly accepted')
    before={'native':{'movement_ticks':20,'frames':50,'actor_position':[1,2,3]},
            'input_adapter':{'external_android':{'key_down':8,'key_up':8}},
            'events':[{'sequence':10,'type':'resume'}]}
    clear={'held_dirs':1,'source_state_bits':1,'movement_ticks':22,'running':True,'frames':52,
           'actor_position':[2,2,3],'foreground':True}
    paused={'resumed':False,'native':{'running':False,'held_dirs':0,'foreground':False,'source_state_bits':0,
                                    'motion_local':[0,0,0],'motion_world':[0,0,0]},
            'input_adapter':{'external_android':{'key_down':9,'key_up':8}},
            'events':[{'sequence':11,'type':'key_down','native':{'held_dirs':1}},
                      {'sequence':13,'type':'input_clear_requested','native':clear},
                      {'sequence':14,'type':'pause','native':{'held_dirs':0}}]}
    check(driver.home_interrupt_witness(before,paused)==[paused['events'][1]],'Unreleased moving source input before real focus clear qualifies')
    for key,value,label in [('held_dirs',0,'Already released native input'),('source_state_bits',0,'No source forward state'),
                            ('movement_ticks',20,'No source movement tick'),('actor_position',[1,2,3],'No actual displacement'),
                            ('foreground',False,'Already background clear'),('running',False,'Inactive pre-clear renderer'),
                            ('frames',50,'No actual rendering before focus interruption')]:
        bad=deepcopy(paused);bad['events'][1]['native'][key]=value
        try:driver.home_interrupt_witness(before,bad)
        except AssertionError:check(True,label+' rejected')
        else:check(False,label+' incorrectly accepted')
    for insert,up,label in [(True,8,'Key up precedes pre-clear witness'),
                            (True,9,'Observed fourth-run early release'),
                            (False,9,'Aggregate key release cannot establish unreleased interruption')]:
        bad=deepcopy(paused);bad['input_adapter']['external_android']['key_up']=up
        if insert:bad['events'].insert(1,{'sequence':12,'type':'key_up','native':{'held_dirs':0}})
        try:driver.home_interrupt_witness(before,bad)
        except AssertionError:check(True,label+' rejected')
        else:check(False,label+' incorrectly accepted')
    axis_before=deepcopy(before);axis_before['input_adapter']['external_android'].update(motion=0,controller_events=0,left_axis_directions=0)
    axis_paused=deepcopy(paused);axis_paused['input_adapter']['external_android'].update(key_down=8,motion=1,controller_events=0,left_axis_directions=4)
    axis_before['input_adapter']['in_app_synthetic']={'motion':0}
    axis_paused['input_adapter']['in_app_synthetic']={'motion':0}
    axis_paused['events']=axis_paused['events'][1:]
    check(driver.home_interrupt_witness(axis_before,axis_paused,source='joystick')==[axis_paused['events'][0]],
          'Observed external framework axis with held moving source state qualifies')
    for field,value,label in [('motion',0,'Missing external motion'),('left_axis_directions',0,'Missing observed forward-axis coverage'),
                              ('key_down',9,'Unrelated keyboard down'),('key_up',9,'Unrelated keyboard release')]:
        bad=deepcopy(axis_paused);bad['input_adapter']['external_android'][field]=value
        try:driver.home_interrupt_witness(axis_before,bad,source='joystick')
        except AssertionError:check(True,label+' rejected')
        else:check(False,label+' incorrectly accepted')
    bad=deepcopy(axis_paused);bad['events'][0]['native']['held_dirs']=0
    try:driver.home_interrupt_witness(axis_before,bad,source='joystick')
    except AssertionError:check(True,'Already-cleared axis cannot qualify pre-clear witness')
    else:check(False,'Already-cleared axis incorrectly accepted')
    bad=deepcopy(axis_paused);bad['input_adapter']['in_app_synthetic']['motion']=1
    try:driver.home_interrupt_witness(axis_before,bad,source='joystick')
    except AssertionError:check(True,'In-app synthetic motion cannot qualify framework joystick receipt')
    else:check(False,'In-app synthetic motion incorrectly accepted')
    for field,value in [('foreground',True),('source_state_bits',1),('motion_local',[0,0,1]),('motion_world',[1,0,0])]:
        bad=deepcopy(axis_paused);bad['native'][field]=value
        try:driver.home_interrupt_witness(axis_before,bad,source='joystick')
        except AssertionError:check(True,'Background source state rejects '+field)
        else:check(False,'Background source state incorrectly accepts '+field)
    # Independent evidence fixtures check that stationary input, adapter bounds
    # or aggregate feature labels cannot pass the shipped collision predicates.
    native={'walk':{'bounded_scene':True,'grounded':True,'ground_y':74,
                    'triangles':96,'blocked_ticks':0,'sliding_ticks':0,
                    'ground_hits':30,'collision_queries':60,'bounded_ticks':0,
                    'obstacle_bounds_min':[579.656,74,-1387.604],
                    'obstacle_bounds_max':[585.344,77.68225,-1385.0634]},
            'actor_position':[582.5,74,-1380],'held_dirs':1,'source_state_bits':1,
            'movement_ticks':30,'frames':100}
    walk_before={'native':deepcopy(native),'input_adapter':{'in_app_synthetic':{'motion':0}}}
    walk_blocked=deepcopy(walk_before)
    walk_blocked['native'].update(actor_position=[582.5,74,-1384.0634],movement_ticks=40,frames=120)
    walk_blocked['native']['walk'].update(blocked_ticks=1,ground_hits=40,collision_queries=100)
    walk_settled=deepcopy(walk_blocked)
    walk_settled['native'].update(movement_ticks=70,frames=180)
    walk_settled['native']['walk'].update(blocked_ticks=25,ground_hits=70,collision_queries=180)
    check(driver.blocked_walk_witness(walk_before,walk_blocked,walk_settled),
          'Held advancing grounded source movement stopped at the authored obstacle qualifies')
    for section,field,value,label in [('native','held_dirs',0,'Released movement cannot qualify blocking'),
                                     ('native','source_state_bits',0,'Absent source controls cannot qualify blocking'),
                                     ('native','movement_ticks',40,'Stopped physics clock cannot qualify blocking'),
                                     ('native','frames',120,'Stopped renderer cannot qualify blocking'),
                                     ('native','actor_position',[582.5,74,-1383],'Moving actor cannot qualify blocking'),
                                     ('walk','blocked_ticks',1,'No additional blocked steps cannot qualify blocking'),
                                     ('walk','collision_queries',100,'No actual collision queries cannot qualify blocking'),
                                     ('walk','bounded_ticks',1,'Adapter clamp cannot qualify authored blocking'),
                                     ('walk','grounded',False,'Airborne actor cannot qualify grounded blocking'),
                                     ('walk','ground_y',73,'Wrong ground height cannot qualify grounding')]:
        bad=deepcopy(walk_settled)
        (bad['native'] if section=='native' else bad['native']['walk'])[field]=value
        try:driver.blocked_walk_witness(walk_before,walk_blocked,bad)
        except AssertionError:check(True,label+' rejected')
        else:check(False,label+' incorrectly accepted')
    bad=deepcopy(walk_settled);bad['native']['actor_position']=[582.5,74,-1340]
    far_block=deepcopy(walk_blocked);far_block['native']['actor_position']=[582.5,74,-1340]
    try:driver.blocked_walk_witness(walk_before,far_block,bad)
    except AssertionError:check(True,'Stable stop far from authored obstacle rejected')
    else:check(False,'Stable stop far from authored obstacle incorrectly accepted')
    walk_sliding=deepcopy(walk_settled)
    walk_sliding['native'].update(actor_position=[581.5,74,-1384.0634],held_dirs=9,
                                 source_state_bits=9,movement_ticks=76,frames=192)
    walk_sliding['native']['walk'].update(blocked_ticks=29,sliding_ticks=4,ground_hits=76,collision_queries=196)
    check(driver.sliding_walk_witness(walk_settled,walk_sliding),
          'Actual grounded diagonal displacement with source block/slide queries qualifies')
    for section,field,value,label in [('native','held_dirs',1,'Non-diagonal input cannot qualify sliding'),
                                     ('native','movement_ticks',70,'No physics progression cannot qualify sliding'),
                                     ('native','frames',180,'No rendering progression cannot qualify sliding'),
                                     ('native','actor_position',walk_settled['native']['actor_position'],'Stationary actor cannot qualify sliding'),
                                     ('walk','sliding_ticks',0,'No source slide steps cannot qualify sliding'),
                                     ('walk','blocked_ticks',25,'No source blocking cannot qualify sliding'),
                                     ('walk','bounded_ticks',1,'Adapter safety clamp cannot qualify sliding')]:
        bad=deepcopy(walk_sliding)
        (bad['native'] if section=='native' else bad['native']['walk'])[field]=value
        try:driver.sliding_walk_witness(walk_settled,bad)
        except AssertionError:check(True,label+' rejected')
        else:check(False,label+' incorrectly accepted')
    run_before={'native':{'movement_ticks':10,'frames':30,'actor_position':[1,2,3],
                          'animation_move_samples':[10,0,0,4,0,0,0,0,0,0,0,0]},
                'input_adapter':{'external_android':{'key_down':8,'key_up':8}},
                'events':[{'sequence':10,'type':'resume'}]}
    run_pre={'held_dirs':0,'animation_state':3,'source_state_bits':1,
             'foreground':True,'running':True,'movement_ticks':14,'frames':35,
             'actor_position':[1,2,2.5],
             'animation_move_samples':[10,0,0,7,0,0,0,0,0,0,0,0]}
    run_released={'input_adapter':{'external_android':{'key_down':9,'key_up':9},
                                    'in_app_synthetic':{'key_down':0,'key_up':0}},
                  'events':[{'sequence':11,'type':'key_down','native':{'held_dirs':1}},
                            {'sequence':12,'type':'key_up','native':run_pre}]}
    check(driver.pre_release_witness(run_before,run_released)==run_released['events'][1],
          'Fresh actual key-up after held input clears while native remains RunPre qualifies interruption')
    for field,value,label in [('animation_state',1,'RunCycle release cannot qualify interrupted Pre'),
                              ('held_dirs',1,'Still-held joystick during keyboard up cannot qualify release'),
                              ('source_state_bits',0,'No source forward state cannot qualify Pre release'),
                              ('foreground',False,'Background release cannot qualify live Pre interruption'),
                              ('running',False,'Stopped rendering cannot qualify live Pre interruption'),
                              ('movement_ticks',10,'Stale source ticks cannot qualify Pre interruption'),
                              ('frames',30,'Stale native frames cannot qualify Pre interruption'),
                              ('actor_position',[1,2,3],'No real source displacement cannot qualify Pre interruption'),
                              ('animation_move_samples',[10,0,0,4,0,0,0,0,0,0,0,0],
                               'Historical Pre samples cannot qualify current interruption')]:
        bad=deepcopy(run_released);bad['events'][1]['native'][field]=value
        try:driver.pre_release_witness(run_before,bad)
        except AssertionError:check(True,label+' rejected')
        else:check(False,label+' incorrectly accepted')
    bad=deepcopy(run_released);bad['events'][0]['sequence']=8;bad['events'][1]['sequence']=9
    try:driver.pre_release_witness(run_before,bad)
    except AssertionError:check(True,'Stale prior-run release receipt rejected')
    else:check(False,'Stale prior-run release receipt incorrectly accepted')
    bad=deepcopy(run_released);bad['input_adapter']['in_app_synthetic']['key_up']=1
    try:driver.pre_release_witness(run_before,bad)
    except AssertionError:check(True,'In-app synthetic release cannot qualify actual framework interruption')
    else:check(False,'In-app synthetic release incorrectly accepted')
    bad=deepcopy(run_released);bad['events'].reverse()
    try:driver.pre_release_witness(run_before,bad)
    except AssertionError:check(True,'Reversed actual press/release trace rejected')
    else:check(False,'Reversed press/release trace incorrectly accepted')
    observed=None
    if args.observed_ui:
        raw=args.observed_ui.read_bytes();actual=list(ET.fromstring(raw).iter('node'))
        for label in ('Reset actor','Recreate','Export report'):
            check(len(driver.button_nodes(actual,label))==1,'Observed Android UI finds '+label)
        observed={'file':args.observed_ui.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    receipt={'schema':1,'passed':True,'checks':checks,
             'scope':'Actual shipped accessibility-label, exact tap listener, strict unreleased-source Home, grounded source obstacle/slide and exact RunPre-at-release evidence predicates on independent XML/event fixtures; no device execution',
             'emulator_driver_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
             'observed_android_ui':observed}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__=='__main__':
    main()
