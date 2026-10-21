#!/usr/bin/env python3
"""Exercise shipped progress text against explicit numeric JSON controls.

No Android, transport, live server, decoded game input or authority is simulated.
"""
import importlib.util,json,subprocess,tempfile,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
JAVA=r'''
import org.json.*;
public class InitialContinuationTextTest {
/*METHOD*/
static int checks;static void check(boolean x){checks++;if(!x)throw new AssertionError();}
public static void main(String[]args){
 JSONObject old=new JSONObject();check(initialContinuationDetail(old,"old scope").equals("old scope"));
 JSONObject value=new JSONObject().put("initial_packet_complete",false).put("initial_next","original unknown field");
 String text=initialContinuationDetail(value,"");check(text.contains("remains incomplete")&&text.contains("original unknown field")&&!text.contains("ACK sent"));
 value.put("initial_next","raw\\nvalue");check(!initialContinuationDetail(value,"").contains("raw"));
 value.put("initial_packet_complete",true).put("initial_command_tail",new JSONArray(0,298736,301656,3,0,1,0)).put("power_unresolved",new JSONArray(343,343,1,2,100));
 value.put("initial_continuation",new JSONArray(1,0,0,0,0,1,0,0,0,0));text=initialContinuationDetail(value,"");check(text.contains("exact EOF at bit 301656")&&text.contains("343 unmapped")&&text.contains("ACK not queued; client READY not queued"));
 value.put("initial_continuation",new JSONArray(1,1,1,0,0,1,0,0,0,0));text=initialContinuationDetail(value,"");check(text.contains("ACK queued; client READY queued")&&!text.contains("ACK sent")&&!text.contains("Later messages"));
 value.put("initial_continuation",new JSONArray(1,1,1,1,0,1,0,0,0,0));check(initialContinuationDetail(value,"").contains("ACK sent; client READY queued"));
 value.put("initial_continuation",new JSONArray(1,1,1,1,1,1,0,4,0,0)).put("post_position",new JSONArray(2,2,1,1,0,1,0));text=initialContinuationDetail(value,"");check(text.contains("ACK sent; client READY sent")&&text.contains("Later messages 4")&&text.contains("Position changes 1, stationary 1, unsupported 1")&&text.contains("Observing bounded updates"));
 value.put("initial_continuation",new JSONArray(1,1,1,1,1,1,0,4,1,0));check(initialContinuationDetail(value,"").contains("Bounded observation ended"));
 value.put("initial_packet_complete",false).put("initial_partial_tail",new JSONArray(1,1,0,1,222,100,101,110,20,1));text=initialContinuationDetail(value,"");check(text.contains("partial-tail skipped command 222")&&text.contains("20 bits discarded")&&text.contains("Whole packet remains incomplete")&&!text.contains("exact EOF"));
 System.out.println("{\"passed\":true,\"checks\":"+checks+",\"android_executed\":false}");}
}'''
JSON=r'''package org.json;import java.util.*;public class JSONObject {Map<String,Object>v=new HashMap<>();public JSONObject put(String k,Object o){v.put(k,o);return this;}public boolean has(String k){return v.containsKey(k);}public Object opt(String k){return v.get(k);}public JSONArray optJSONArray(String k){Object o=v.get(k);return o instanceof JSONArray?(JSONArray)o:null;}public String optString(String k,String d){Object o=v.get(k);return o instanceof String?(String)o:d;}}'''
ARRAY=r'''package org.json;public class JSONArray {long[]v;public JSONArray(long...x){v=x;}public int length(){return v.length;}public long optLong(int i){return optLong(i,0);}public long optLong(int i,long d){return i>=0&&i<v.length?v[i]:d;}public int optInt(int i,int d){return(int)optLong(i,d);}}'''
def renderer_controls(extract,work):
 source=(ROOT/'native-android/session-client/app/src/main/cpp/session_renderer.c').read_text()
 begin=source.index('        uint64_t box_draws=s->observed_entity_draws;')
 end=source.index('        const CohSessionWorldStats *t=',begin)
 helper=extract(source,'static void jappend(Json *j,const char *format,...) {')
 harness=r"""
#include <stdio.h>
#include <stdint.h>
#include <stddef.h>
#include <stdarg.h>
#include <string.h>
#include <inttypes.h>
#define JSON_CAP 2048
typedef struct {char*p;size_t n;int ok;}Json;
typedef struct {uint32_t observed_entity_index;float observed_entity_position[3];uint64_t observed_entity_updates,observed_entity_draws,received_frames;}Session;
/*HELPER*/
int main(void){Session data={7,{1,2,3},4,12,5};Session*s=&data;char output[JSON_CAP]="{\"scope\":0";Json j={output,strlen(output),1};
/*BODY*/
jappend(&j,"}");if(!j.ok)return 1;puts(output);return 0;}
""".replace('/*HELPER*/',helper).replace('/*BODY*/',source[begin:end])
 path=work/'renderer-scope.c';path.write_text(harness);controls=0
 for mode,flags in [('release',['-O2']),('asan',['-O1','-fsanitize=address','-no-pie']),('ubsan',['-O1','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  for profile,actor in ((0,0),(1,0),(1,1)):
   binary=work/('renderer-'+mode+str(profile)+str(actor));subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-DCOH_FULLSCREEN_DIAGNOSTIC='+str(profile),'-DCOH_LIVE_COSTUME_DIAGNOSTIC='+str(actor),*flags,str(path),'-o',str(binary)],check=True,timeout=60)
   result=subprocess.run([str(binary)],check=True,capture_output=True,text=True,timeout=30,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'))
   observed=json.loads(result.stdout)['observed_server_entity'];assert observed['complete_actor']is False and observed['box_draws']==(7 if actor else 12)
   if profile:assert 'application_ack'not in observed and observed['renderer_sends_application_ack']is False and observed['transport_send_facts']=='server_protocol.initial_continuation'
   else:assert observed['application_ack']is False and 'renderer_sends_application_ack'not in observed and 'transport_send_facts'not in observed
   controls+=1
 return controls

def main():
 spec=importlib.util.spec_from_file_location('initial_text_extract',ROOT/'native-android/session-client/tools/lifecycle_host_check.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 source=(ROOT/'native-android/combined-client/app/src/main/java/org/coh/nativecombined/NativeClientActivity.java').read_text();method=m.method(source,'private static String initialContinuationDetail(')
 assert 'if(BuildConfig.FULLSCREEN_DIAGNOSTIC)detail=initialContinuationDetail(report,detail);' in source
 with tempfile.TemporaryDirectory(prefix='coh-initial-text-')as tmp:
  w=Path(tmp);(w/'org/json').mkdir(parents=True)
  files=[]
  for name,text in [('org/json/JSONObject.java',JSON),('org/json/JSONArray.java',ARRAY),('InitialContinuationTextTest.java',JAVA.replace('/*METHOD*/',method))]:
   p=w/name;p.write_text(text);files.append(str(p))
  subprocess.run(['java','-Xmx128m','com.sun.tools.javac.Main','--release','8','-d',str(w),*files],check=True,timeout=60)
  r=subprocess.run(['java','-Xmx64m','-cp',str(w),'InitialContinuationTextTest'],check=True,capture_output=True,text=True,timeout=30);value=json.loads(r.stdout);value['renderer_schema_controls']=renderer_controls(m.method,w);print(json.dumps(value))
if __name__=='__main__':main()
