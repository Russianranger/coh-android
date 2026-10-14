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
    xml='''<hierarchy>
    <node class="android.widget.Button" package="org.coh.sessionclient" text="RESET ACTOR" enabled="true" clickable="true" bounds="[10,280][292,375]"/>
    <node class="android.widget.Button" package="org.coh.sessionclient" text="RECREATE" enabled="true" clickable="true" bounds="[310,280][532,375]"/>
    <node class="android.widget.Button" package="org.coh.sessionclient" text="EXPORT REPORT" enabled="true" clickable="true" bounds="[550,280][879,375]"/>
    </hierarchy>'''
    nodes=list(ET.fromstring(xml).iter('node'))
    for label,event in [('Reset actor','reset_requested'),('Recreate','recreate_requested'),('Export report','export_requested')]:
        matched=driver.button_nodes(nodes,label)
        check(len(matched)==1,'Material uppercase button: '+label)
        check(driver.bounds(matched[0])[2]>driver.bounds(matched[0])[0],'Positive actual button bounds: '+label)
        original=deepcopy(matched[0]);original.set('text',label)
        check(driver.button_nodes([original],label)==[original],'Original sentence-case button: '+label)
        for key,value in [('package','org.other.app'),('enabled','false'),('clickable','false'),('text',label+' again')]:
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
    observed=None
    if args.observed_ui:
        raw=args.observed_ui.read_bytes();actual=list(ET.fromstring(raw).iter('node'))
        for label in ('Reset actor','Recreate','Export report'):
            check(len(driver.button_nodes(actual,label))==1,'Observed Android UI finds '+label)
        observed={'file':args.observed_ui.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    receipt={'schema':1,'passed':True,'checks':checks,
             'scope':'Actual shipped accessibility-label, exact tap listener and strict unreleased-source Home predicates on independent XML/event fixtures; no device execution',
             'emulator_driver_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
             'observed_android_ui':observed}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__=='__main__':
    main()
