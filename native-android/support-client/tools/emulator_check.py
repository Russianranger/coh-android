#!/usr/bin/env python3
"""Exercise the separate offline support APK with Android framework actions.

The coordinator-owned scenario selects observable fields and controls. Results
describe actual emulator execution only: no physical gamepad, Thor, full-game,
live-session or full gate acceptance is inferred.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import time
import xml.etree.ElementTree as ET

PACKAGE='org.coh.nativesupport'
ACTIVITY=PACKAGE+'/org.coh.sessionclient.MainActivity'

def require(ok,message):
    if not ok:raise ValueError(message)

def field(value,path):
    for part in path.split('.'):
        if isinstance(value,list):value=value[int(part)]
        else:value=value[part]
    return value

def matches(value,conditions,baseline=None):
    try:
        for path,expected in conditions.items():
            current=field(value,path)
            if isinstance(expected,dict):
                if not expected or set(expected)-{'gte','gt','lte','eq','increases','changes','same'}:return False
                if 'gte' in expected and not current>=expected['gte']:return False
                if 'gt' in expected and not current>expected['gt']:return False
                if 'lte' in expected and not current<=expected['lte']:return False
                if 'eq' in expected and current!=expected['eq']:return False
                if expected.get('increases') and (baseline is None or not current>field(baseline,path)):return False
                if expected.get('changes') and (baseline is None or current==field(baseline,path)):return False
                if expected.get('same') and (baseline is None or current!=field(baseline,path)):return False
            elif current!=expected:return False
        return True
    except (KeyError,IndexError,TypeError,ValueError):return False

class Check:
    def __init__(self,a,scenario):
        self.a=a;self.scenario=scenario;self.commands=[];self.last=None;self.steps=[]
        self.relay=None
        if a.relay:
            spec=importlib.util.spec_from_file_location('support_emulator_relay',Path(__file__).with_name('emulator_relay.py'))
            self.relay=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.relay)
    def save(self,name,value):
        (self.a.output/name).write_text(json.dumps(value,indent=2)+'\n')
    def adb(self,*args,check=True,timeout=60):
        if self.relay:result=self.relay.request(self.a.relay,list(args),timeout)
        else:
            prefix=[self.a.adb]+(['-s',self.a.serial] if self.a.serial else [])
            result=subprocess.run([*prefix,*args],capture_output=True,timeout=timeout)
        self.commands.append({'args':list(args),'returncode':result.returncode,'stdout_bytes':len(result.stdout),
                              'stdout_sha256':hashlib.sha256(result.stdout).hexdigest(),
                              'stdout_preview':result.stdout[:2048].decode(errors='replace'),
                              'stderr':result.stderr[:4096].decode(errors='replace')})
        self.save('emulator-command-proof.json',self.commands)
        if check:require(result.returncode==0,'ADB command failed: '+' '.join(args)+'\n'+result.stderr.decode(errors='replace'))
        return result
    def report(self):
        result=self.adb('exec-out','run-as',PACKAGE,'cat',self.scenario.get('report','files/support-report.json'),check=False)
        if result.returncode:return None
        require(len(result.stdout)<=4<<20,'Application report exceeds bound')
        try:value=json.loads(result.stdout)
        except (ValueError,UnicodeDecodeError):return None
        self.last=value;self.save('emulator-latest-report.json',value)
        for path in self.scenario.get('fatal_fields',['native.failed']):
            try:fatal=field(value,path)
            except KeyError:continue
            require(not fatal,'Sticky app failure at '+path+': '+str(fatal))
        return value
    def wait(self,conditions,label,baseline=None,timeout=90):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            current=self.report()
            if current is not None and matches(current,conditions,baseline):return current
            time.sleep(.2)
        raise TimeoutError(label+' timed out; last report saved')
    def screenshot(self,name):
        result=self.adb('exec-out','screencap','-p',check=False)
        if result.returncode==0 and result.stdout.startswith(b'\x89PNG\r\n\x1a\n'):
            (self.a.output/name).write_bytes(result.stdout);return True
        return False
    def tap_text(self,text):
        self.adb('shell','uiautomator','dump','/data/local/tmp/coh-support-ui.xml')
        raw=self.adb('exec-out','cat','/data/local/tmp/coh-support-ui.xml').stdout
        tree=ET.fromstring(raw);nodes=[n for n in tree.iter('node') if n.get('text')==text or n.get('content-desc')==text]
        require(len(nodes)==1,'Expected unique Android control: '+text)
        bounds=re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',nodes[0].get('bounds',''))
        require(bounds,'Control has no actionable bounds: '+text)
        x0,y0,x1,y1=map(int,bounds.groups());self.adb('shell','input','tap',str((x0+x1)//2),str((y0+y1)//2))
    def action(self,value):
        kind=value['kind']
        if kind=='tap_text':self.tap_text(value['text'])
        elif kind=='key':
            source=['gamepad'] if value.get('source')=='gamepad' else []
            self.adb('shell','input',*source,'keyevent',value['key'])
        elif kind=='text':
            text=value['text'];require(re.fullmatch(r'[A-Za-z0-9 ._-]{1,256}',text),'Text injection uses a bounded shell-safe alphabet')
            self.adb('shell','input','text',text.replace(' ','%s'))
        elif kind=='hud_tap':
            report=self.report();require(report is not None,'No report for HUD coordinates')
            area=report['input_area'];scale=min(area['width']/1024,area['height']/768)
            x=area['left']+(area['width']-1024*scale)/2+float(value['x'])*scale
            y=area['top']+(area['height']-768*scale)/2+float(value['y'])*scale
            self.adb('shell','input','tap',str(round(x)),str(round(y)))
        elif kind=='tap':self.adb('shell','input','tap',str(value['x']),str(value['y']))
        elif kind=='swipe':self.adb('shell','input','swipe',*[str(value[k]) for k in ('x0','y0','x1','y1','ms')])
        elif kind=='home':self.adb('shell','input','keyevent','KEYCODE_HOME')
        elif kind=='launch':self.adb('shell','am','start','-W','-n',ACTIVITY)
        elif kind=='wait':time.sleep(min(10,float(value.get('seconds',1))))
        else:raise ValueError('Unsupported framework action: '+kind)
    def execute(self):
        require(self.adb('shell','getprop','ro.boot.qemu').stdout.strip()==b'1','Support qualification is restricted to disposable emulator')
        existing=self.adb('shell','pm','path',PACKAGE,check=False).stdout.strip()
        require(not existing or self.a.replace,'Support app already installed; use explicit --replace for owned emulator iteration')
        if existing:self.adb('shell','am','force-stop',PACKAGE)
        installed=self.adb('install',*(['-r'] if self.a.replace else []),str(self.a.apk),timeout=120)
        require(re.search(rb'^Success\s*$',installed.stdout,re.M),'APK install did not report Success')
        launched=self.adb('shell','am','start','-W','-n',ACTIVITY)
        require(re.search(rb'^Status:\s*ok\s*$',launched.stdout,re.M),'Android Activity launch failed')
        ready=self.scenario['ready'];require(ready,'Scenario must declare actual readiness observations')
        first=self.wait(ready,'Native support client ready',timeout=self.a.startup_timeout)
        self.save('emulator-initial-report.json',first);self.screenshot('emulator-initial.png')
        previous=first
        for i,step in enumerate(self.scenario.get('steps',[])):
            require(step.get('assert'),'Every scenario step must declare observable assertions')
            before=self.report() or previous
            for action in step.get('actions',[step.get('action')]):
                if action:self.action(action)
            current=self.wait(step.get('assert',ready),step['label'],before,step.get('timeout',60))
            receipt={'label':step['label'],'passed':True,'actions':step.get('actions',[step.get('action')]),'assertions':step.get('assert',ready)}
            self.steps.append(receipt);self.save('emulator-step-%02d-report.json'%i,current)
            if step.get('screenshot'):self.screenshot('emulator-step-%02d.png'%i)
            print(json.dumps({'step':step['label'],'passed':True}),flush=True);previous=current
        self.save('emulator-final-report.json',previous);self.screenshot('emulator-final.png')
        summary={'schema':1,'passed':True,'package':PACKAGE,'source_commit':self.scenario.get('source_commit'),
                 'installed_apk':{'bytes':self.a.apk.stat().st_size,'sha256':hashlib.sha256(self.a.apk.read_bytes()).hexdigest()},
                 'scope':'actual Android emulator framework input/lifecycle and native report assertions in separate offline support client',
                 'scenario_sha256':hashlib.sha256(self.a.scenario.read_bytes()).hexdigest(),'steps':self.steps,
                 'native_execution_verified':True,'physical_controller_verified':False,'thor_device_execution_verified':False,
                 'full_atlas_loaded':False,'server_interoperability_verified':False,'gates_fully_accepted':False}
        self.save('emulator-support-summary.json',summary);print(json.dumps(summary),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apk',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--scenario',type=Path,required=True);p.add_argument('--adb',default='adb');p.add_argument('--serial')
    p.add_argument('--relay',type=Path);p.add_argument('--replace',action='store_true');p.add_argument('--startup-timeout',type=int,default=180)
    a=p.parse_args();a.apk=a.apk.resolve();a.output.mkdir(parents=True,exist_ok=True);scenario=json.loads(a.scenario.read_text())
    require(scenario.get('schema')==1,'Unsupported emulator scenario schema');c=Check(a,scenario)
    try:c.execute()
    finally:
        try:(a.output/'emulator-logcat.txt').write_bytes(c.adb('logcat','-d',check=False).stdout)
        except Exception as error:c.save('emulator-logcat-error.json',{'error':str(error)})
        try:c.screenshot('emulator-last.png')
        except Exception:pass

if __name__=='__main__':main()
