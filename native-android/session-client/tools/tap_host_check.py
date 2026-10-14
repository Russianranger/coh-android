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
    observed=None
    if args.observed_ui:
        raw=args.observed_ui.read_bytes();actual=list(ET.fromstring(raw).iter('node'))
        for label in ('Reset actor','Recreate','Export report'):
            check(len(driver.button_nodes(actual,label))==1,'Observed Android UI finds '+label)
        observed={'file':args.observed_ui.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    receipt={'schema':1,'passed':True,'checks':checks,
             'scope':'Actual shipped case-insensitive accessibility-label selector and exact post-tap listener predicates on literal XML/event fixtures; no device execution',
             'emulator_driver_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
             'observed_android_ui':observed}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__=='__main__':
    main()
