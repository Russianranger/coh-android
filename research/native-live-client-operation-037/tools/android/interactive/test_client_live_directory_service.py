"""Real JVM/TCP controls for the dormant operation-owned metadata service.

The Backend is a typed mock. These tests do not execute JNI, Wine, PRoot, FEX,
Android, Game, player SQL or a filesystem metadata provider.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
SOURCE = JAVA / 'ClientLiveDirectoryService.java'

HARNESS = r'''
package io.github.russianranger.cohclientinteractive;
import java.io.*;
import java.net.*;
import java.nio.*;
import java.nio.charset.StandardCharsets;
import java.lang.reflect.Field;
import java.util.*;

public final class LiveDirectoryServiceHost {
 static final byte[] OP=new byte[16], TOKEN=new byte[16];
 static final String PATH="/state/work/data/fx";
 static final long DEV=41, INODE=55; static final int UID=42;
 static { Arrays.fill(OP,(byte)0x21);Arrays.fill(TOKEN,(byte)0x31); }
 static void need(boolean value,String note){if(!value)throw new AssertionError(note);}
 static final class State {
  final byte[] op,token; int sequence,rows;
  State(byte[] a,byte[] b){op=a.clone();token=b.clone();}
 }
 static final class Mock implements ClientLiveDirectoryService.Backend {
  final Map<Long,State> states=new HashMap<Long,State>();
  volatile int opened,closedCursor,closed,preparedRows; long nextHandle=1;
  String identity="good", mutation="", fault=""; boolean failNext;
  int[] counts={1}; boolean finalFrame=true;
  public synchronized long open(String path,byte[] op,byte[] token)throws IOException {
   need(PATH.equals(path),"mock receives exact admitted path");
   need(Arrays.equals(op,OP)&&token.length==16,"mock receives current operation/token");
   if(fault.equals("open"))throw new IOException("injected open failure");
   opened++; if(fault.equals("zero_handle"))return 0;
   long result=nextHandle++;states.put(result,new State(op,token));return result;
  }
  public synchronized long[] identity(long cursor)throws IOException {
   if(fault.equals("identity"))throw new IOException("injected identity failure");
   if(identity.equals("null"))return null;
   if(identity.equals("short"))return new long[]{DEV,INODE};
   return new long[]{identity.equals("device")?DEV+1:DEV,INODE,identity.equals("uid")?UID+1:UID};
  }
  public synchronized byte[] next(long handle)throws IOException {
   if(fault.equals("next_runtime"))throw new IllegalStateException("injected current batch runtime failure");
   if(failNext||fault.equals("next"))throw new IOException("injected current batch failure");
   State s=states.get(handle);need(s!=null,"mock cursor still owned");
   int count=counts[Math.min(s.sequence,counts.length-1)];
   byte[] result=frame(s.op,s.token,s.sequence,s.rows,count,finalFrame);
   s.sequence++;s.rows+=count;
   preparedRows=s.rows;
   if(fault.equals("next_oome"))throw new OutOfMemoryError("typed mock error after native-style cursor advancement");
   if(mutation.equals("null"))return null;
   if(mutation.equals("short"))return new byte[63];
   if(mutation.equals("oversized"))return new byte[27945];
   ByteBuffer b=ByteBuffer.wrap(result).order(ByteOrder.LITTLE_ENDIAN);
   if(mutation.equals("magic"))result[0]^=1;
   if(mutation.equals("operation"))result[8]^=1;
   if(mutation.equals("token"))result[24]^=1;
   if(mutation.equals("sequence"))b.putInt(40,17);
   if(mutation.equals("start"))b.putInt(44,17);
   if(mutation.equals("count"))b.putInt(48,86);
   if(mutation.equals("final"))b.putInt(52,2);
   if(mutation.equals("reserved"))b.putInt(56,1);
   if(mutation.equals("size"))b.putInt(60,result.length+1);
   if(count>0){
    if(mutation.equals("ordinal"))b.putInt(64,17);
    if(mutation.equals("row_reserved"))b.putInt(68,1);
    if(mutation.equals("invalid_name"))result[64+8+44]=':';
    if(mutation.equals("unterminated"))Arrays.fill(result,64+8+44,64+8+304,(byte)'A');
    if(mutation.equals("name_padding"))result[64+8+46]=1;
    if(mutation.equals("wfd_reserved"))result[64+8+36]=1;
    if(mutation.equals("short_name"))result[64+8+304]=1;
    if(mutation.equals("nt_boundary"))for(int j=0;j<count;j++)Arrays.fill(result,64+j*328+8+44,64+j*328+8+44+259,(byte)'a');
   }
   return result;
  }
  public synchronized void closeCursor(long cursor)throws IOException {
   closedCursor++;
   if(fault.equals("close_cursor_runtime"))throw new IllegalStateException("injected cursor runtime cleanup failure");
   if(fault.equals("close_cursor"))throw new IOException("injected cursor cleanup failure");
   states.remove(cursor);
  }
  public synchronized void close()throws IOException {
   closed++;states.clear();
   if(fault.equals("close_runtime"))throw new IllegalStateException("injected namespace runtime cleanup failure");
   if(fault.equals("close"))throw new IOException("injected namespace cleanup failure");
  }
 }
 static byte[] frame(byte[] operation,byte[] token,int sequence,int start,int count,boolean done){
  byte[] result=new byte[64+count*328];ByteBuffer b=ByteBuffer.wrap(result).order(ByteOrder.LITTLE_ENDIAN);
  b.put("COHLIVE1".getBytes(StandardCharsets.US_ASCII)).put(operation).put(token)
   .putInt(sequence).putInt(start).putInt(count).putInt(done?1:0).putInt(0).putInt(result.length);
  for(int i=0;i<count;i++){
   int row=64+i*328;b.putInt(row,start+i);b.putInt(row+8,32);b.putLong(row+8+20,133444736000000000L);
   result[row+8+44]='a';
  }
  return result;
 }
 static final class Scope implements AutoCloseable {
  final Mock mock=new Mock();final List<String> log=Collections.synchronizedList(new ArrayList<String>());
  final ClientLiveDirectoryService service; Socket socket; DataInputStream in;DataOutputStream out;
  volatile boolean failJournal,failJournalError; boolean expectedFailure;
  Scope()throws Exception {service=new ClientLiveDirectoryService(OP,DEV,UID,mock,path->PATH.equals(path),
   (phase,token,rows,result)->{if(failJournalError)throw new AssertionError("typed mock journal Error");
    if(failJournal)throw new IllegalStateException("injected journal failure");
    log.add(phase+":"+rows+":"+result);});}
  void connect()throws Exception {socket=new Socket("127.0.0.1",service.port());socket.setSoTimeout(4000);socket.setTcpNoDelay(true);
   in=new DataInputStream(socket.getInputStream());out=new DataOutputStream(socket.getOutputStream());}
  public void close()throws Exception {
   IOException error=null;try{service.close();}catch(IOException problem){error=problem;}finally{if(socket!=null)socket.close();}
   need(mock.closed==1,"every test releases namespace exactly once");
   if(!expectedFailure&&error!=null)throw error;
  }
 }
 static byte[] request(Scope f,int command,int sequence,byte[] token,byte[] path){
  byte[] result=new byte[96+path.length];ByteBuffer b=ByteBuffer.wrap(result).order(ByteOrder.LITTLE_ENDIAN);
  b.put("COHLDIR1".getBytes(StandardCharsets.US_ASCII)).putInt(1).putInt(command).put(OP)
   .put(f.service.authenticationNonce()).putInt(sequence).put(token).putInt(path.length).putInt(result.length).putInt(0);
  System.arraycopy(path,0,result,96,path.length);return result;
 }
 static byte[] request(Scope f,int command,int sequence){return request(f,command,sequence,TOKEN,
  command==1?PATH.getBytes(StandardCharsets.US_ASCII):new byte[0]);}
 static final class Reply {final int status,sequence;final byte[] body;
  Reply(int a,int b,byte[] c){status=a;sequence=b;body=c;}}
 static Reply read(Scope f)throws Exception {
  byte[] raw=new byte[32];f.in.readFully(raw);ByteBuffer b=ByteBuffer.wrap(raw).order(ByteOrder.LITTLE_ENDIAN);
  need(Arrays.equals(Arrays.copyOfRange(raw,0,8),new byte[]{'C','O','H','R','S','P','1',0}),"exact response magic");
  need(b.getInt(8)==1&&b.getInt(24)==0&&b.getInt(28)==0,"exact response version/reserved");
  int size=b.getInt(20);need(size>=0&&size<=27944,"bounded response body");byte[] body=new byte[size];f.in.readFully(body);
  return new Reply(b.getInt(12),b.getInt(16),body);
 }
 static Reply send(Scope f,int command,int seq)throws Exception {f.out.write(request(f,command,seq));f.out.flush();return read(f);}
 static void ack(Reply reply,int seq){need(reply.status==0&&reply.sequence==seq&&reply.body.length==32,"OPEN successful exact32byte ACK");
  ByteBuffer b=ByteBuffer.wrap(reply.body).order(ByteOrder.LITTLE_ENDIAN);
  need(b.getLong()==DEV&&b.getLong()==INODE&&b.getInt()==1&&b.getInt()==1&&b.getLong()==0,"OPEN actual mock identity/recipe flags");}
 static void open(Scope f)throws Exception {f.connect();ack(send(f,1,1),1);}
 static Thread worker(Scope f)throws Exception {Field field=ClientLiveDirectoryService.class.getDeclaredField("worker");field.setAccessible(true);return(Thread)field.get(f.service);}
 static void waitFinished(Scope f)throws Exception {Thread t=worker(f);t.join(4000);need(!t.isAlive(),"bounded owned worker termination");}
 static void closedServer(Scope f)throws Exception {boolean refused=false;try(Socket ignored=new Socket("127.0.0.1",f.service.port())){}catch(IOException expected){refused=true;}
  need(refused,"service listening socket closed after cleanup");}
 static void protocolFailure(Scope f,byte[] bytes)throws Exception {f.out.write(bytes);f.out.flush();f.socket.shutdownOutput();
  need(f.in.read()==-1,"malformed request closes owned connection");waitFinished(f);
  need(f.service.failure()!=null,"protocol failure retained");f.expectedFailure=true;
  need(f.mock.closed==1,"namespace cleanup attempted exactly once");closedServer(f);}
 static void run(String mode)throws Exception {
  if(mode.equals("construction")){
   boolean failed=false;try{new ClientLiveDirectoryService(new byte[15],DEV,UID,new Mock(),path->true,(a,b,c,d)->{});}catch(IOException expected){failed=true;}
   need(failed,"invalid operation refused before thread/server");return;
  }
  try(Scope f=new Scope()){
   if(mode.equals("close_before_peer")){f.service.close();need(f.mock.closed==1,"unconnected namespace cleanup");closedServer(f);return;}
   if(mode.equals("rejected_limit")){
    for(int i=0;i<8;i++){f.connect();byte[] wrong=request(f,1,1);wrong[32]^=1;f.out.write(wrong);f.out.flush();
     need(f.in.read()==-1,"bounded unauthenticated peer rejected");f.socket.close();}
    waitFinished(f);need(f.service.failure()!=null&&f.mock.opened==0&&f.mock.closed==1,"rejected peer limit closes service without backend cursor");f.expectedFailure=true;
    closedServer(f);return;
   }
   if(mode.equals("nonce_copy")){byte[] n=f.service.authenticationNonce();n[0]^=1;need(!Arrays.equals(n,f.service.authenticationNonce()),"nonce clones protect authority");}
   if(mode.equals("unauthenticated")){
    f.connect();byte[] wrong=request(f,1,1);wrong[32]^=1;f.out.write(wrong);f.out.flush();need(f.in.read()==-1,"wrong nonce closes unauth peer");
    f.socket.close();need(f.mock.opened==0,"unauth cannot call native Backend");f.connect();ack(send(f,1,1),1);
   }else if(mode.equals("admission_decline")){
    f.connect();f.out.write(request(f,1,1,TOKEN,"/state/other".getBytes(StandardCharsets.US_ASCII)));f.out.flush();Reply r=read(f);
    need(r.status==1&&r.body.length==0&&f.mock.opened==0,"path denied before backend");return;
   }else if(mode.equals("invalid_path")){
    f.connect();f.out.write(request(f,1,1,TOKEN,"/state/../fx".getBytes(StandardCharsets.US_ASCII)));f.out.flush();Reply r=read(f);
    need(r.status==1&&f.mock.opened==0,"alias path denied before backend");return;
   }else if(mode.startsWith("identity_")){
    f.mock.identity=mode.substring(9);f.connect();Reply r=send(f,1,1);need(r.status==1&&r.body.length==0,"identity mismatch declines");
    need(f.mock.closedCursor==1,"failed identity releases exact opened cursor");return;
   }else if(mode.equals("backend_open")||mode.equals("backend_identity")||mode.equals("zero_handle")){
    f.mock.fault=mode.equals("backend_open")?"open":mode.equals("backend_identity")?"identity":"zero_handle";
    f.connect();Reply r=send(f,1,1);need(r.status==1&&r.body.length==0,"backend initial error declines");
    need(f.mock.closedCursor==(mode.equals("backend_identity")?1:0),"only actual nonzero cursor released");return;
   }else if(mode.equals("fragmented")){
    f.connect();byte[] r=request(f,1,1);for(int i=0;i<r.length;i+=7){f.out.write(r,i,Math.min(7,r.length-i));f.out.flush();}ack(read(f),1);
   }else if(mode.equals("coalesced")){
    f.connect();ByteArrayOutputStream r=new ByteArrayOutputStream();r.write(request(f,1,1));r.write(request(f,2,2));f.out.write(r.toByteArray());f.out.flush();
    ack(read(f),1);Reply second=read(f);need(second.status==0&&second.sequence==2&&second.body.length==392,"two coalesced requests framed exactly");
    need(send(f,3,3).status==0,"explicit close after pipelined batches");return;
   }else open(f);
   if(mode.equals("no_idle_expiry")){Thread.sleep(2300);need(send(f,2,2).status==0,"authenticated idle beyond admission limit remains live");return;}
   if(mode.equals("tcp_no_delay")){Field active=ClientLiveDirectoryService.class.getDeclaredField("active");active.setAccessible(true);
    need(((Socket)active.get(f.service)).getTcpNoDelay(),"real accepted TCP socket disables Nagle");return;}
   if(mode.equals("close_blocked_read")){f.service.close();need(f.mock.closedCursor==1&&f.mock.closed==1,"blocked peer unblocked and owned cleanup complete");return;}
   if(mode.equals("idempotent_close")){f.service.close();f.service.close();
    need(f.mock.closedCursor==1&&f.mock.closed==1,"repeat close cannot duplicate cursor or namespace release");return;}
   if(mode.equals("journal_runtime")){f.failJournal=true;protocolFailure(f,request(f,2,2));
    need(f.mock.closedCursor==1,"journal failure releases actual cursor");return;}
   if(mode.equals("backend_next_runtime")){f.mock.finalFrame=false;need(send(f,2,2).status==0,"first current frame emitted");
    f.mock.fault="next_runtime";protocolFailure(f,request(f,2,3));need(f.mock.closedCursor==1,"late runtime error cannot leave cursor or silently fallback");return;}
   if(mode.equals("backend_next_oome_after_advance")){f.mock.finalFrame=false;need(send(f,2,2).status==0,"first current frame emitted");
    f.mock.fault="next_oome";protocolFailure(f,request(f,2,3));
    need(f.mock.preparedRows==2&&f.mock.closedCursor==1,"Error after cursor advancement is terminal and cannot retry advanced state");
    need(f.service.failure().getCause() instanceof OutOfMemoryError,"actual typed mock Error retained as cause");return;
   }
   if(mode.equals("journal_error_after_rows")){f.mock.finalFrame=false;need(send(f,2,2).status==0,"first current frame emitted");
    f.failJournalError=true;protocolFailure(f,request(f,2,3));
    need(f.mock.preparedRows==2&&f.mock.closedCursor==1,"journal Error after metadata acquisition cleans current cursor");
    need(f.service.failure().getCause() instanceof AssertionError,"journal Error cause retained");return;
   }
   if(mode.equals("request_nonce")){byte[] r=request(f,2,2);r[32]^=1;protocolFailure(f,r);return;}
   if(mode.equals("request_sequence")){protocolFailure(f,request(f,2,1));return;}
   if(mode.equals("request_operation")){byte[] r=request(f,2,2);r[16]^=1;protocolFailure(f,r);return;}
   if(mode.equals("request_version")){byte[] r=request(f,2,2);ByteBuffer.wrap(r).order(ByteOrder.LITTLE_ENDIAN).putInt(8,2);protocolFailure(f,r);return;}
   if(mode.equals("request_reserved")){byte[] r=request(f,2,2);ByteBuffer.wrap(r).order(ByteOrder.LITTLE_ENDIAN).putInt(92,1);protocolFailure(f,r);return;}
   if(mode.equals("request_oversize")){byte[] r=request(f,1,2);ByteBuffer.wrap(r).order(ByteOrder.LITTLE_ENDIAN).putInt(84,1025);protocolFailure(f,r);return;}
   if(mode.equals("request_size")){byte[] r=request(f,2,2);ByteBuffer.wrap(r).order(ByteOrder.LITTLE_ENDIAN).putInt(88,97);protocolFailure(f,r);return;}
   if(mode.equals("request_opcode")){byte[] r=request(f,2,2);ByteBuffer.wrap(r).order(ByteOrder.LITTLE_ENDIAN).putInt(12,9);protocolFailure(f,r);return;}
   if(mode.equals("duplicate_open")){protocolFailure(f,request(f,1,2));return;}
   if(mode.equals("cursor_limit")){
    for(int i=1;i<16;i++){byte[] token=TOKEN.clone();token[0]=(byte)i;
     f.out.write(request(f,1,i+1,token,PATH.getBytes(StandardCharsets.US_ASCII)));f.out.flush();ack(read(f),i+1);}
    byte[] seventeenth=TOKEN.clone();seventeenth[0]=100;
    protocolFailure(f,request(f,1,17,seventeenth,PATH.getBytes(StandardCharsets.US_ASCII)));
    need(f.mock.closedCursor==16,"cursor cap releases every actual owned cursor");return;
   }
   if(mode.equals("cursor_reuse")){need(send(f,3,2).status==0,"first exact cursor released");
    byte[] other=TOKEN.clone();other[0]=100;f.out.write(request(f,1,3,other,PATH.getBytes(StandardCharsets.US_ASCII)));f.out.flush();ack(read(f),3);
    f.out.write(request(f,2,4,other,new byte[0]));f.out.flush();Reply current=read(f);
    need(current.status==0&&Arrays.equals(Arrays.copyOfRange(current.body,24,40),other),"reusedslot owns current token/session");return;
   }
   if(mode.equals("unknown_cursor")){byte[] r=request(f,2,2);r[68]^=1;protocolFailure(f,r);return;}
   if(mode.equals("truncated_header")){byte[] r=request(f,2,2);f.out.write(r,0,37);f.out.flush();f.socket.shutdownOutput();waitFinished(f);
    need(f.service.failure()!=null,"partial authenticated request header must remain failure evidence");f.expectedFailure=true;return;}
   if(mode.equals("truncated_body")){byte[] token=TOKEN.clone();token[0]^=1;byte[] r=request(f,1,2,token,PATH.getBytes(StandardCharsets.US_ASCII));
    f.out.write(r,0,99);f.out.flush();f.socket.shutdownOutput();waitFinished(f);need(f.service.failure()!=null,"partial request body must remain failure");f.expectedFailure=true;return;}
   if(mode.equals("eof_live_cursor")){f.socket.shutdownOutput();waitFinished(f);need(f.mock.closedCursor==1&&f.mock.closed==1,"EOF releases held cursor/backend");
    need(f.service.failure()!=null,"unexpected peerEOF with owned live cursor preserves interrupted-session failure");f.expectedFailure=true;return;}
   if(mode.equals("graceful_eof")){need(send(f,3,2).status==0,"explicit cursor close");f.socket.shutdownOutput();waitFinished(f);
    need(f.service.failure()==null&&f.mock.closed==1,"EOF after all cursors closed is graceful");return;}
   if(mode.equals("initial_batch_failure")){f.mock.failNext=true;Reply r=send(f,2,2);need(r.status==1&&f.mock.closedCursor==1,"failure before rows declines and cleans cursor");return;}
   if(mode.equals("terminal_after_rows")){f.mock.finalFrame=false;need(send(f,2,2).status==0,"first current frame");f.mock.failNext=true;
    Reply r=send(f,2,3);need(r.status==2&&f.mock.closedCursor==1,"failure after rows terminal/no restart");
    need(f.log.toString().contains("terminal_no_restart"),"terminal evidence attributed to rows");return;}
   if(mode.equals("next_after_final")){need(send(f,2,2).status==0,"final frame passed");need(send(f,2,3).status==2,"next after emitted final frame terminal");return;}
   if(mode.equals("final_empty")){f.mock.counts=new int[]{0};Reply r=send(f,2,2);need(r.status==0&&r.body.length==64,"explicit empty final frame");return;}
   if(mode.equals("zero_nonfinal")){f.mock.counts=new int[]{0};f.mock.finalFrame=false;need(send(f,2,2).status==1,"empty nonfinal frame refused");return;}
   if(mode.startsWith("frame_")){f.mock.mutation=mode.substring(6);Reply r=send(f,2,2);need(r.status==1&&f.mock.closedCursor==1,"malformed initial native frame refused and cursor released");return;}
   if(mode.equals("nt_boundary")){f.mock.counts=new int[]{85};f.mock.mutation="";
    // Make every name 259 bytes: the wire cap alone cannot authorize NT acquisition geometry.
    f.mock.counts=new int[]{85};f.mock.mutation="nt_boundary";need(send(f,2,2).status==1,"terminated large names rejected by actual NT geometry");return;}
   if(mode.equals("row_limit")){f.mock.finalFrame=false;f.mock.counts=new int[98];Arrays.fill(f.mock.counts,85);f.mock.counts[96]=32;f.mock.counts[97]=1;
    for(int i=0;i<97;i++)need(send(f,2,i+2).status==0,"bounded rows through8192");
    need(send(f,2,99).status==2,"row8193 terminally exceeds cursor cap");return;}
   if(mode.startsWith("cleanup_")){f.mock.fault=mode.substring(8);f.socket.shutdownOutput();waitFinished(f);
    need(f.mock.closed==1,"namespace cleanup attempted despite cursor cleanup error");closedServer(f);
    need(f.service.failure()!=null,"cleanup failure remains durable service evidence");f.expectedFailure=true;return;}
   if(mode.equals("success")||mode.equals("fragmented")||mode.equals("unauthenticated")||mode.equals("nonce_copy")){
    Reply r=send(f,2,2);need(r.status==0&&r.body.length==392,"actual socket carries typed current batch");
    need(send(f,3,3).status==0&&f.mock.closedCursor==1,"one owned cursor closed");return;
   }
   throw new AssertionError("Unknown control "+mode);
  }
 }
 public static void main(String[] args)throws Exception {run(args[0]);System.out.println("{\"case\":\""+args[0]+"\",\"status\":\"passed\",\"actual_JVM_TCP\":true,\"JNI_native_backend\":false}");}
}
'''


class ClientLiveDirectoryServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-live-service-JVM-')
        cls.directory = Path(cls.temporary.name)
        cls.source_bytes = SOURCE.read_bytes()
        cls.source_sha256 = hashlib.sha256(cls.source_bytes).hexdigest()
        snapshot = cls.directory / SOURCE.name
        snapshot.write_bytes(cls.source_bytes)
        fixture = cls.directory / 'LiveDirectoryServiceHost.java'
        fixture.write_text(HARNESS)
        result = subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
            '-d', str(cls.directory), str(snapshot), str(fixture)], capture_output=True, text=True, timeout=30)
        if result.returncode:
            cls.temporary.cleanup()
            raise AssertionError('Actual Service/JVM fixture compilation failed:\n'+result.stdout+result.stderr)

    @classmethod
    def tearDownClass(cls):
        try:
            if SOURCE.read_bytes() != cls.source_bytes:
                raise AssertionError('Service source changed during focused replay; recapture before final freeze')
        finally:
            cls.temporary.cleanup()

    def control(self, mode):
        result = subprocess.run(['java', '-cp', str(self.directory),
            'io.github.russianranger.cohclientinteractive.LiveDirectoryServiceHost', mode],
            capture_output=True, text=True, timeout=12)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value, {'case': mode, 'status': 'passed', 'actual_JVM_TCP': True, 'JNI_native_backend': False})


MODES = [
    'construction', 'success', 'nonce_copy', 'unauthenticated', 'admission_decline', 'invalid_path',
    'identity_null', 'identity_short', 'identity_device', 'identity_uid', 'backend_open', 'backend_identity',
    'zero_handle', 'fragmented', 'coalesced', 'no_idle_expiry', 'tcp_no_delay', 'close_before_peer',
    'close_blocked_read', 'idempotent_close', 'rejected_limit', 'journal_runtime', 'backend_next_runtime',
    'backend_next_oome_after_advance', 'journal_error_after_rows',
    'request_nonce', 'request_sequence', 'request_operation', 'request_version',
    'request_reserved', 'request_oversize', 'request_size', 'request_opcode', 'duplicate_open',
    'unknown_cursor', 'cursor_limit', 'cursor_reuse', 'truncated_header', 'truncated_body', 'eof_live_cursor', 'graceful_eof',
    'initial_batch_failure', 'terminal_after_rows', 'next_after_final', 'final_empty', 'zero_nonfinal',
    'frame_null', 'frame_short', 'frame_oversized', 'frame_magic', 'frame_operation', 'frame_token',
    'frame_sequence', 'frame_start', 'frame_count', 'frame_final', 'frame_reserved', 'frame_size',
    'frame_ordinal', 'frame_row_reserved', 'frame_invalid_name', 'frame_unterminated',
    'frame_name_padding', 'frame_wfd_reserved', 'frame_short_name', 'nt_boundary', 'row_limit',
    'cleanup_close_cursor', 'cleanup_close', 'cleanup_close_cursor_runtime', 'cleanup_close_runtime',
]


def case(mode):
    def test(self):
        self.control(mode)
    return test


for mode in MODES:
    setattr(ClientLiveDirectoryServiceTests, 'test_'+mode, case(mode))


if __name__ == '__main__':
    unittest.main()
