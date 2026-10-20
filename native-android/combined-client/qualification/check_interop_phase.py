#!/usr/bin/env python3
"""Execute production scalar state and exact Activity methods with host doubles.

The small JSON/Android/JNI collaborators below are test doubles. This does not
claim Android execution, protocol admission or genuine server-world entry.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'app/src/main/java/org/coh/nativecombined'
METHODS = ['sameNetworkPolicy', 'disconnectNetwork', 'suspendNetwork', 'networkTick',
           'checkedHandoffReport', 'storeNetworkReport', 'publishNetwork', 'updateNetworkUi']


def method(text, name):
    match = re.search(r'    private (?:void|boolean|String) ' + name + r'\(', text)
    assert match, name
    start = text.index('{', match.end())
    depth = 0
    quote = None
    escaped = False
    for i in range(start, len(text)):
        char = text[i]
        if quote:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == quote:
                quote = None
        elif char in '\"\'':
            quote = char
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[match.start():i+1]
    raise AssertionError('Unclosed method ' + name)


HEADER = r'''
package org.coh.nativecombined;
import java.nio.charset.StandardCharsets;
import java.util.*;
final class InteropPhaseTest {
 private enum NetworkMode { LOCAL, WORLD_HANDOFF }
 private NetworkMode networkMode=NetworkMode.WORLD_HANDOFF;
 private String networkReport="{}",interopReport="{}",localNetworkReport="{}";
 private final HandoffState handoffState=new HandoffState();
 private boolean captureTelemetryPublished,destroying,networkForeground=true,networkRequested=true;
 private boolean networkConnecting,returningToLauncher,charactersPublished;
 private long networkHandle=1,networkAttempt,networkOwnerAttempt,policyCheckedAt=1000;
 private long observedEntityAttempt=-1;private int observedEntityIndex=-1;
 // JNI/render callout is an explicit collaborator; the eight production phase methods remain exact.
 private void publishObservedSelf(long sourceHandle,long attempt){}
 private JSONObject networkPolicy;
 private boolean policyFailure;
 private int policyCalls,pickerCalls;
 private final Handler main=new Handler();
 private final Ui connectButton=new Ui(),handoffButton=new Ui(),characterButtons=new Ui(),charactersScroll=new Ui(),networkStatus=new Ui();
 private JSONObject localPolicy(){policyCalls++;if(policyFailure)throw new IllegalStateException("private fixture failure");return networkPolicy;}
 private void showCharacters(JSONArray values,long attempt){pickerCalls++;}
'''

TESTS = r'''
 static int checks;
 static void need(boolean condition,String why){checks++;if(!condition)throw new AssertionError(why+" ["+checks+"]");}
 static void reset(){InteropNative.bits=1;InteropNative.services=InteropNative.reports=InteropNative.suspends=InteropNative.characters=0;InteropNative.text="{}";MemoryTelemetry.calls=0;SystemClock.now=1000;}
 static InteropPhaseTest active(){reset();InteropPhaseTest t=new InteropPhaseTest();t.handoffState.begin();t.handoffState.control(1);return t;}
 static String first(long failure){return new JSONObject().put("phase","FAILED").put("first_failure",new JSONObject().put("valid",true).put("local_phase",8).put("db_phase",3).put("map_phase",5).put("status",4).put("failure",failure)).toString();}
 static String initial(InteropPhaseTest t){return (String)PhaseMemoryDiagnostics.states(t.handoffState.initialObserved(),false).get("initial_packet");}
 public static void main(String[]args)throws Exception {
  HandoffState s=new HandoffState();need(s.initialObserved()==null,"fresh observation unknown");
  need(!s.blocksNewAttempt()&&!s.shouldService(),"fresh state has no owner");s.begin();
  need(s.blocksNewAttempt()&&!s.shouldService(),"unknown control blocks replacement and service");
  s.control(1);need(s.shouldService()&&Boolean.FALSE.equals(s.initialObserved()),"actual present control supplies negative observation");
  s.control(0);need(s.blocksNewAttempt()&&!s.shouldService(),"missing scalar observation never means idle");
  need(s.initialObserved()==null,"known negative becomes unknown when current scalar is unavailable/busy");
  s.control(9);need(s.charactersReady()&&s.blocksNewAttempt(),"characters ready still owned");
  s.control(7);need(!s.shouldService()&&!s.blocksNewAttempt()&&Boolean.TRUE.equals(s.initialObserved()),"captured terminal");
  s.control(1);need(!s.shouldService()&&Boolean.TRUE.equals(s.initialObserved()),"terminal/captured state sticky");
  s.control(0);s.retired();need(Boolean.TRUE.equals(s.initialObserved()),"capture survives cleanup");
  s.begin();need(s.initialObserved()==null&&s.firstFailure()==null,"new explicit begin resets attempt evidence");
  s.firstFailure(1,2,3,4,5);s.firstFailure(6,7,8,9,10);long[] saved=s.firstFailure();need(saved[4]==5,"first failure sticky");
  saved[4]=99;need(s.firstFailure()[4]==5,"failure snapshot detached");
  s.phase("WAIT_ALLENTS");s.phase("REPORT_LIMIT");need(s.lastPhase().equals("WAIT_ALLENTS"),"report limit retains previous phase observation");
  s.phase("INITIAL_OBSERVED");need(!s.shouldService()&&Boolean.TRUE.equals(s.initialObserved()),"legacy captured report stops service");
  InteropPhaseTest t=new InteropPhaseTest();t.storeNetworkReport("{\"phase\":\"REPORT_LIMIT\"}");
  need(initial(t).equals("UNKNOWN"),"legacy report without independent observation is unknown");
  need(new JSONObject(t.interopReport).getBoolean("report_serialization_unknown"),"explicit unknown serialization");
  t.storeNetworkReport("{\"phase\":");need(initial(t).equals("UNKNOWN"),"malformed serialization cannot fabricate negative");
  need(new JSONObject(t.interopReport).optString("phase").equals("REPORT_UNAVAILABLE"),"malformed report normalized");
  t=active();InteropNative.text="{\"phase\":\"REPORT_LIMIT\"}";t.publishNetwork();t.main.drain();
  need(!t.handoffButton.enabled&&t.connectButton.enabled,"active REPORT_LIMIT keeps handoff disabled");
  t.networkTick();need(InteropNative.services==1,"active REPORT_LIMIT continues real owner service");
  need(initial(t).equals("NOT_OBSERVED"),"actual scalar negative remains distinct from unknown");
  InteropNative.bits=0;t.publishNetwork();t.main.drain();need(!t.handoffButton.enabled,"missing owner scalar does not enable handoff");
  need(initial(t).equals("UNKNOWN"),"unavailable scalar clears stale negative observation");
  InteropNative.text="{\"phase\":\"OWNER_BUSY\",\"initial_observation_known\":false,\"raw_allents_observed\":false}";
  t.publishNetwork();need(initial(t).equals("UNKNOWN"),"busy report false placeholder remains unknown");
  InteropNative.text="{\"raw_allents_observed\":false}";t.publishNetwork();
  need(initial(t).equals("UNKNOWN"),"partial report negative without observation-known cannot establish a negative");
  int services=InteropNative.services;t.networkTick();need(InteropNative.services==services,"unknown owner scalar does not service");
  InteropNative.bits=9;InteropNative.text="{\"phase\":\"REPORT_LIMIT\"}";t.networkTick();t.main.drain();
  need(t.pickerCalls==1&&!t.handoffButton.enabled,"picker publication uses scalar characters-ready despite fallback");
  t.characterButtons.removals=0;t.updateNetworkUi();need(t.characterButtons.removals==0,"partial report does not hide active picker");
  InteropNative.bits=7;InteropNative.text="{\"phase\":\"REPORT_LIMIT\"}";t.publishNetwork();t.main.drain();
  need(t.handoffButton.enabled&&initial(t).equals("INITIAL_PACKET_OBSERVED"),"completed fallback permits explicit new attempt only");
  services=InteropNative.services;t.policyFailure=true;SystemClock.now=9999;
  for(int i=0;i<100;i++)t.networkTick();
  need(InteropNative.services==services&&InteropNative.suspends==0&&t.policyCalls==0,"completed capture neither serviced nor revalidated/suspended");
  t.publishNetwork();need(MemoryTelemetry.calls==1,"capture memory event published once");
  t.suspendNetwork();InteropNative.bits=3;t.publishNetwork();need(initial(t).equals("INITIAL_PACKET_OBSERVED"),"initial survives cleanup control without capture bit");
  t=active();t.storeNetworkReport(first(10));
  String[] partial={"{\"phase\":\"REPORT_LIMIT\"}","{\"phase\":\"CLOSED\",\"first_failure\":{\"valid\":false}}","{\"phase\":",first(11)};
  for(String raw:partial){t.storeNetworkReport(raw);JSONObject f=new JSONObject(t.interopReport).optJSONObject("first_failure");need(f!=null&&f.optLong("failure")==10&&f.optLong("status")==4,"first native failure survives partial/cleanup/later failure");}
  t=active();t.storeNetworkReport("{\"phase\":\"WAIT_ALLENTS\",\"raw_allents_observed\":\"false\"}");
  need(initial(t).equals("NOT_OBSERVED"),"string cannot change actual scalar observation");
  t.handoffState.begin();t.storeNetworkReport("{\"raw_allents_observed\":\"false\"}");need(initial(t).equals("UNKNOWN"),"string boolean cannot establish observation");
  t=active();InteropNative.text="{\"phase\":";t.publishNetwork();t.main.drain();need(!t.handoffButton.enabled,"malformed report cannot mark owner idle");
  t.networkForeground=false;services=InteropNative.services;t.networkTick();need(InteropNative.services==services,"background no service/reconnect");
  t.networkForeground=true;t.networkRequested=false;t.networkTick();need(InteropNative.services==services,"stopped request no service/reconnect");
  need(Boolean.FALSE.equals(PhaseMemoryDiagnostics.states((Boolean)null,false).get("world_authority")),"unknown never authority");
  need(Boolean.FALSE.equals(PhaseMemoryDiagnostics.states((Boolean)null,false).get("application_ack_permitted")),"unknown never ACK");
  long[] boundary={2,41,3,1,2424,3416,262144};
  s.begin();s.catalogBoundary(boundary,false);need(s.catalogBoundary()==null,"boundary without positive observation refused");
  for(int i=0;i<7;i++){long[] bad=boundary.clone();bad[i]=-1;s.catalogBoundary(bad,true);need(s.catalogBoundary()==null,"negative scalar refused");}
  for(long[] bad:new long[][]{null,new long[6],new long[8],{3,41,3,1,2424,3416,262144},{2,40,3,1,2424,3416,262144},{2,41,257,1,2424,3416,262144},{2,41,3,257,2424,3416,262144},{2,41,3,1,33554433L,3416,262144},{2,41,3,1,33554432L,1,262144},{2,41,3,1,2424,3271,262144},{2,41,3,1,2424,3416,Long.MAX_VALUE},{2,41,3,1,2424,3416,2359296},{2,41,3,1,2424,3416,67371008},{2,43,3,1,2424,3416,4L<<26},{2,43,3,1,2424,3416,(2L<<26)|(14L<<21)},{2,41,3,1,2424,3416,262199},{2,41,3,1,2424,3416,786432}}){s.catalogBoundary(bad,true);need(s.catalogBoundary()==null,"malformed framing refused");}
  s.catalogBoundary(boundary,true);need(s.catalogDetail().contains("stage 41")&&s.catalogDetail().contains("current MapServer"),"precise default refusal");
  boundary[1]=43;long[] copy=s.catalogBoundary();copy[1]=40;need(s.catalogBoundary()[1]==41,"input and output detached");
  s.retired();need(s.catalogBoundary()[1]==41,"boundary survives cleanup");s.begin();need(s.catalogBoundary()==null&&s.catalogDetail()==null,"new attempt clears boundary");
  s.catalogBoundary(new long[]{2,43,3,1,2424,3448, (5L<<26)|(28L<<21)|(1L<<18)},true);need(s.catalogDetail().contains("explicit part count"),"explicit framing separate");
  t=active();InteropNative.bits=7;
  InteropNative.text="{\"schema\":\"coh-native-initial-interop-numeric-v1\",\"phase\":\"INITIAL_OBSERVED\",\"raw_allents_observed\":true,\"catalog_boundary\":[2,41,3,1,2424,3416,262144]}";
  t.publishNetwork();t.main.drain();need(t.networkStatus.text.contains("stage 41")&&t.networkStatus.text.contains("default part count"),"actual Activity UI projects boundary");
  need(new JSONObject(t.interopReport).optJSONArray("catalog_boundary").length()==7,"numeric retained report");
  InteropNative.text="{\"phase\":\"REPORT_LIMIT\"}";t.publishNetwork();t.main.drain();need(t.networkStatus.text.contains("stage 41"),"partial report preserves boundary UI");
  need(new JSONObject(t.interopReport).optJSONArray("catalog_boundary").length()==7,"partial report preserves boundary numeric evidence");
  t.disconnectNetwork();t.updateNetworkUi();need(t.networkStatus.text.contains("stage 41"),"closed same attempt preserves boundary");
  t.handoffState.begin();need(t.handoffState.catalogBoundary()==null,"fresh attempt does not leak previous boundary");
  t=active();InteropNative.bits=7;InteropNative.text="{\"schema\":\"coh-native-initial-interop-numeric-v1\",\"phase\":\"INITIAL_OBSERVED\",\"initial_observation_known\":true,\"raw_allents_observed\":true,\"catalog_boundary\":[2,41,3,1,2424,3416,262144]}";t.publishNetwork();t.main.drain();
  need(t.networkStatus.text.contains("default part count"),"unresolved actual stage41 remains visible");
  InteropNative.text="{\"schema\":\"coh-native-initial-interop-numeric-v1\",\"phase\":\"INITIAL_OBSERVED\",\"initial_observation_known\":true,\"raw_allents_observed\":true,\"bodyparts_default\":[0,28],\"costume_continuation\":[2,3,0,28,0,2,0,1,1,0,5146,5146],\"catalog_boundary\":null}";t.publishNetwork();t.main.drain();
  need(t.networkStatus.text.contains("BodyPart count verified")&&t.networkStatus.text.contains("geometry")&&t.networkStatus.text.contains("costume strings"),"actual continuation replaces stale41 UI");
  need(!t.networkStatus.text.contains("default part count"),"verified count is not described as unresolved");
  t.observedEntityAttempt=t.networkAttempt;t.observedEntityIndex=123;t.updateNetworkUi();need(t.networkStatus.text.contains("observed server entity #123"),"observed entity marker independent of later dictionary");

  for(String invalid:new String[]{"{\"phase\":\"INITIAL_OBSERVED\",\"raw_allents_observed\":true,\"catalog_boundary\":[2,41,3,1,2424,3416,262144]}","{\"schema\":\"wrong\",\"raw_allents_observed\":true,\"catalog_boundary\":[2,41,3,1,2424,3416,262144]}","{\"schema\":\"coh-native-initial-interop-numeric-v1\",\"raw_allents_observed\":false,\"catalog_boundary\":[2,41,3,1,2424,3416,262144]}","{\"schema\":\"coh-native-initial-interop-numeric-v1\",\"raw_allents_observed\":true,\"catalog_boundary\":[2,\"41\",3,1,2424,3416,262144]}","{\"schema\":\"coh-native-initial-interop-numeric-v1\",\"raw_allents_observed\":true,\"catalog_boundary\":[2,true,3,1,2424,3416,262144]}"}){t=active();t.storeNetworkReport(invalid);need(t.handoffState.catalogBoundary()==null,"untrusted schema/numeric input refused");}
  System.out.println("{\"status\":\"passed\",\"checks\":"+checks+",\"exact_activity_methods\":8,\"native_json_android_collaborators_are_doubles\":true,\"android_execution\":false,\"world_authority\":false}");
 }
}
final class Handler {final ArrayDeque<Runnable> q=new ArrayDeque<>();void post(Runnable r){q.add(r);}void drain(){while(!q.isEmpty())q.remove().run();}}
final class Ui {boolean enabled;int removals;String text;void setEnabled(boolean value){enabled=value;}void setText(String text){this.text=text;}void removeAllViews(){removals++;}void setVisibility(int value){}}
final class SystemClock {static long now;static long elapsedRealtime(){return now;}}
final class JSONArray {
 final List<Object> values=new ArrayList<>();JSONArray(){}JSONArray(String raw){}
 JSONArray put(Object value){values.add(value);return this;}int length(){return values.size();}Object opt(int i){return i>=0&&i<values.size()?values.get(i):null;}
 int optInt(int i,int fallback){Object value=opt(i);return value instanceof Number?((Number)value).intValue():fallback;}
 public String toString(){return values.toString();}
}
final class InteropNative {
 static int bits,services,reports,suspends,characters;static String text;
 static int controlState(long handle){return bits;}static String report(long handle){reports++;return text;}
 static int service(long handle,long now){services++;return 0;}static byte[] characters(long handle){characters++;return "[]".getBytes(StandardCharsets.UTF_8);}
 static void suspend(long handle){suspends++;bits=3;}static void disconnect(long handle){bits=3;}
}
final class LocalNative {
 static int service(long handle,long now){throw new AssertionError("wrong producer");}static String report(long handle){throw new AssertionError("wrong producer");}
 static byte[] characters(long handle){throw new AssertionError("wrong producer");}static void suspend(long handle){throw new AssertionError("wrong producer");}static void disconnect(long handle){throw new AssertionError("wrong producer");}
}
final class MemoryTelemetry {static int calls;static void request(Object activity,PhaseMemoryDiagnostics.Phase phase){calls++;}}
// A deliberately small test collaborator: real object JSON fixtures are parsed
// and serialized, but Android's org.json is qualified separately in Android13.
final class JSONObject {
 static final Object NULL=new Object();final Map<String,Object> values=new LinkedHashMap<>();
 JSONObject(){}JSONObject(String raw){Parser p=new Parser(raw);JSONObject parsed=p.object();p.space();if(p.at!=raw.length())throw new IllegalArgumentException();values.putAll(parsed.values);}
 JSONObject put(String key,Object value){values.put(key,value);return this;}Object opt(String key){return values.get(key);}
 JSONArray optJSONArray(String key){Object value=opt(key);return value instanceof JSONArray?(JSONArray)value:null;}
 JSONObject optJSONObject(String key){Object value=opt(key);return value instanceof JSONObject?(JSONObject)value:null;}
 String optString(String key){return optString(key,"");}String optString(String key,String fallback){Object value=opt(key);return value==null||value==NULL?fallback:String.valueOf(value);}
 String getString(String key){return (String)opt(key);}int getInt(String key){return ((Number)opt(key)).intValue();}
 boolean getBoolean(String key){return (Boolean)opt(key);}long optLong(String key){Object value=opt(key);return value instanceof Number?((Number)value).longValue():0;}
 int optInt(String key){return (int)optLong(key);}
 public String toString(){StringBuilder out=new StringBuilder("{");for(Map.Entry<String,Object> entry:values.entrySet()){if(out.length()>1)out.append(',');out.append(quote(entry.getKey())).append(':');Object value=entry.getValue();out.append(value==null||value==NULL?"null":value instanceof String?quote((String)value):value.toString());}return out.append('}').toString();}
 static String quote(String value){return "\""+value.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n")+"\"";}
 static final class Parser {
  final String raw;int at;Parser(String value){if(value==null)throw new IllegalArgumentException();raw=value;}
  void space(){while(at<raw.length()&&Character.isWhitespace(raw.charAt(at)))at++;}
  char take(){if(at>=raw.length())throw new IllegalArgumentException();return raw.charAt(at++);}
  void need(char value){space();if(take()!=value)throw new IllegalArgumentException();}
  String string(){need('"');StringBuilder out=new StringBuilder();while(true){char c=take();if(c=='"')return out.toString();if(c=='\\'){c=take();if(c=='n')c='\n';}out.append(c);}}
  JSONObject object(){need('{');JSONObject out=new JSONObject();space();if(at<raw.length()&&raw.charAt(at)=='}'){at++;return out;}while(true){String key=string();need(':');out.put(key,value());space();char c=take();if(c=='}')return out;if(c!=',')throw new IllegalArgumentException();}}
  Object value(){space();if(at>=raw.length())throw new IllegalArgumentException();char c=raw.charAt(at);if(c=='{')return object();if(c=='['){at++;JSONArray result=new JSONArray();space();if(raw.charAt(at)==']'){at++;return result;}while(true){result.put(value());space();char sep=take();if(sep==']')return result;if(sep!=',')throw new IllegalArgumentException();}}if(c=='"')return string();for(String word:new String[]{"true","false","null"})if(raw.startsWith(word,at)){at+=word.length();return word.equals("null")?NULL:Boolean.valueOf(word);}int start=at;if(c=='-')at++;while(at<raw.length()&&Character.isDigit(raw.charAt(at)))at++;if(start==at)throw new IllegalArgumentException();return Long.valueOf(raw.substring(start,at));}
 }
}
'''


def main():
    activity = (SOURCE / 'NativeClientActivity.java').read_text()
    service = (SOURCE / 'ServerService.java').read_text()
    assert 'PhaseMemoryDiagnostics.states((Boolean)null,(String)serverMemory.snapshot().get("reason"))' in service
    extracted = '\n'.join(method(activity, name) for name in METHODS)
    with tempfile.TemporaryDirectory(prefix='coh-interop-phase-') as tmp:
        out = Path(tmp)
        harness = out / 'InteropPhaseTest.java'
        harness.write_text(HEADER + extracted + TESTS)
        view = out / 'android/view/View.java'
        view.parent.mkdir(parents=True)
        view.write_text('package android.view; public final class View {public static final int GONE=8;}')
        command = ['java', 'com.sun.tools.javac.Main', '--release', '8', '-d', str(out),
                   str(SOURCE / 'HandoffState.java'), str(SOURCE / 'ServerMemoryPolicy.java'),
                   str(SOURCE / 'PhaseMemoryDiagnostics.java'), str(view), str(harness)]
        compile_result = subprocess.run(command, capture_output=True, text=True)
        if compile_result.returncode:
            raise RuntimeError(compile_result.stderr)
        result = subprocess.run(['java', '-cp', str(out), 'org.coh.nativecombined.InteropPhaseTest'],
                                capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        receipt = json.loads(result.stdout)
        receipt['activity_sha256'] = hashlib.sha256(activity.encode()).hexdigest()
        receipt['state_sha256'] = hashlib.sha256((SOURCE / 'HandoffState.java').read_bytes()).hexdigest()
        receipt['server_only_initial_observation_unknown'] = True
        print(json.dumps(receipt))


if __name__ == '__main__':
    main()
