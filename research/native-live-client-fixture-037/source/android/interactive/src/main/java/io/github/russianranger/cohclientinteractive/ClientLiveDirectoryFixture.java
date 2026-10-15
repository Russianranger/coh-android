package io.github.russianranger.cohclientinteractive;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.FileInputStream;
import java.io.FileDescriptor;
import java.nio.channels.FileChannel;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/** Small, dormant packaged-runtime fixture for constructor metadata.
 *
 * This class neither loads JNI nor starts Game, DbServer or MapServer. Its owner
 * supplies exclusive tiny fixture directories, the exact current native API and
 * a held child Process. Raw NT bytes, an exit code or exported JSON never grant
 * production admission. Alias, NT sharing and concurrent-retarget controls are
 * additional reviewed gates; this comparator deliberately cannot satisfy them.
 * No fixture receipt is read from disk or accepted from JSON.
 */
final class ClientLiveDirectoryFixture {
    static final String SCHEMA="COH_CLIENT_LIVE_DIRECTORY_FIXTURE_V1";
    static final String RECIPE="wine-b073-constructor-v1";
    static final int MAX_BYTES=512*1024, MAX_ROWS=256, MAX_BATCHES=32;
    static final int NT_BUFFER_BYTES=8192, BRIDGE_BYTES=27944, MAX_CONSOLE_BYTES=32*1024;
    static final long MAX_FIXTURE_IO_MILLIS=30000;
    private static final long NATIVE_EOF=0x80000006L;
    private ClientLiveDirectoryFixture() {}

    static final class Row {
        final String name;
        final long sizeLow,writeFiletime;
        final int attributes;
        Row(String n,long size,long write,int attr) {
            name=n;sizeLow=size;writeFiletime=write;attributes=attr&0x17;
        }
        boolean same(Row other) {
            return name.equals(other.name)&&sizeLow==other.sizeLow
                    &&writeFiletime==other.writeFiletime&&attributes==other.attributes;
        }
    }
    static final class NtBatch {
        final int number,rawBytes;
        final List<Row> rows;
        final List<Integer> offsets;
        NtBatch(int n,int length,List<Row> r,List<Integer> o) {
            number=n;rawBytes=length;rows=immutable(r);offsets=immutable(o);
        }
    }
    static final class NtObservation {
        final long pid,thread,inode,openStatus,infoStatus,lastQueryStatus;
        final int mode;
        final boolean complete,cleanupFailed;
        final String originalDosPath,finalDosPath,rawSha256;
        final int rawBytes;
        final List<NtBatch> batches;
        final List<Row> rows;
        private NtObservation(long p,long t,long ino,long opened,long info,long query,int selected,
                boolean done,boolean failed,String original,String resolved,byte[] raw,
                List<NtBatch> b,List<Row> r)throws IOException {
            pid=p;thread=t;inode=ino;openStatus=opened;infoStatus=info;lastQueryStatus=query;mode=selected;
            complete=done;cleanupFailed=failed;originalDosPath=original;finalDosPath=resolved;
            rawSha256=sha256(raw);rawBytes=raw.length;batches=immutable(b);rows=immutable(r);
        }
    }
    static final class BridgeBatch {
        final long sequence,first;
        final boolean finished;
        final List<Row> rows;
        final String rawSha256;
        final int rawBytes;private final byte[] rawFrame;
        byte[] rawFrame(){return rawFrame.clone();}
        private BridgeBatch(long seq,long start,boolean finalBatch,List<Row> found,byte[] raw)throws IOException {
            sequence=seq;first=start;finished=finalBatch;rows=immutable(found);
            rawSha256=sha256(raw);rawBytes=raw.length;rawFrame=raw.clone();
        }
    }

    /** Parse exact v1 COHNTB1 + raw FileBothDirectoryInformation3 + NTEND1.
     * Unused native NT fields remain observations, not canonical WFD authority. */
    static NtObservation parseNt(byte[] supplied)throws IOException {
        require(supplied!=null&&supplied.length>=136&&supplied.length<=MAX_BYTES,"NT packet bound differs");
        byte[] raw=supplied.clone();ByteBuffer b=le(raw);
        magic(raw,0,"COHNTB1\0");
        require(u32(b,8)==1&&(u32(b,12)==1||u32(b,12)==2),"NT packet version/mode differs");
        long pid=u32(b,16),thread=u32(b,20);
        require(pid>0&&thread>0,"Native PID/thread missing");zero(raw,24,32);zero(raw,72,96);
        long inode=b.getLong(32),opened=u32(b,40),info=u32(b,44);
        int path=count(u32(b,48),1023),resolved=count(u32(b,52),1032);
        require(u32(b,56)==8192&&u32(b,60)==256&&u32(b,64)==32&&u32(b,68)==MAX_BYTES,
                "NT observer caps differ");
        require(96L+path+resolved+40<=raw.length,"NT path spans differ");
        String original=ascii(raw,96,path),finalPath=ascii(raw,96+path,resolved);
        int at=96+path+resolved;List<NtBatch> batches=new ArrayList<>();List<Row> all=new ArrayList<>();
        while(hasMagic(raw,at,"NTBATCH1")) {
            require(at+24L<=raw.length,"NT envelope truncated");
            int number=count(u32(b,at+8),MAX_BATCHES-1),length=count(u32(b,at+16),NT_BUFFER_BYTES);
            int cardinality=count(u32(b,at+20),MAX_ROWS);
            require(number==batches.size()&&u32(b,at+12)==0&&batches.size()<MAX_BATCHES,
                    "NT batch sequence/status differs");
            require(length>0&&at+24L+length<=raw.length,"NT payload truncated");
            int begin=at+24,pos=0;List<Row> current=new ArrayList<>();List<Integer> offsets=new ArrayList<>();
            for(;;) {
                require(pos+94L<=length,"FileBoth prefix truncated");
                int next=count(u32(b,begin+pos),NT_BUFFER_BYTES);
                int nameBytes=count(u32(b,begin+pos+60),518);
                require(nameBytes>0&&(nameBytes&1)==0&&pos+94L+nameBytes<=length,"NT name span differs");
                String name=ntName(raw,begin+pos+94,nameBytes);
                current.add(new Row(name,u32(b,begin+pos+40),b.getLong(begin+pos+24),(int)u32(b,begin+pos+56)));
                offsets.add(pos);require(current.size()<=MAX_ROWS,"NT row cap exceeded");
                if(next==0)break;
                require((next&7)==0&&next>=94+nameBytes&&pos+(long)next<length,"NT next-entry span differs");
                pos+=next;
            }
            require(current.size()==cardinality&&all.size()+current.size()<=MAX_ROWS,"NT cardinality differs");
            batches.add(new NtBatch(number,length,current,offsets));all.addAll(current);at+=24+length;
        }
        require(at+40L==raw.length,"NT footer missing/trailing bytes");magic(raw,at,"NTEND1\0\0");
        long done=u32(b,at+12),failed=u32(b,at+28),last=u32(b,at+24);
        require(u32(b,at+8)==1&&(done==0||done==1)&&(failed==0||failed==1)&&u32(b,at+36)==0,
                "NT footer schema differs");
        require(u32(b,at+16)==batches.size()&&u32(b,at+20)==all.size()&&u32(b,at+32)==raw.length,
                "NT footer counts differ");
        int mode=(int)u32(b,12);
        if(done==1) {
            require(opened==0&&info==0&&inode!=0&&!finalPath.isEmpty()&&failed==0,"Native handle witness incomplete");
            if(mode==1)require(last==NATIVE_EOF,"Exact native EOF missing");
            else require(batches.isEmpty()&&all.isEmpty(),"Sharing observer unexpectedly enumerated");
        }
        return new NtObservation(pid,thread,inode,opened,info,last,mode,done==1,failed==1,
                original,finalPath,raw,batches,all);
    }

    /** Decode bounded JNI constructor projection, including exact NT geometry.
     * Creation/access/short names are deliberately canonical zero, not proofs. */
    static BridgeBatch parseBridge(byte[] supplied,byte[] operation,byte[] token,
            long expectedSequence,long expectedFirst)throws IOException {
        require(supplied!=null&&supplied.length>=64&&supplied.length<=BRIDGE_BYTES,"Bridge bound differs");
        require(operation!=null&&operation.length==16&&token!=null&&token.length==16,"Wire identities missing");
        byte[] raw=supplied.clone();ByteBuffer b=le(raw);magic(raw,0,"COHLIVE1");
        require(Arrays.equals(operation,Arrays.copyOfRange(raw,8,24))
                &&Arrays.equals(token,Arrays.copyOfRange(raw,24,40)),"Bridge operation/cursor attribution differs");
        long sequence=u32(b,40),first=u32(b,44),cardinality=u32(b,48),done=u32(b,52);
        require(sequence==expectedSequence&&first==expectedFirst&&cardinality<=85&&(done==0||done==1)
                &&u32(b,56)==0&&u32(b,60)==raw.length&&64+cardinality*328==raw.length,
                "Bridge sequence/cardinality/schema differs");
        require(cardinality>0||done==1,"Non-final empty bridge frame refused");
        require(first+cardinality<=MAX_ROWS,"Fixture bridge row cap exceeded");
        List<Row> rows=new ArrayList<>();int used=0;
        for(int i=0;i<(int)cardinality;i++) {
            int at=64+i*328,wfd=at+8;
            require(u32(b,at)==first+i&&u32(b,at+4)==0,"Bridge row ordinal differs");
            zero(raw,wfd+4,wfd+20);zero(raw,wfd+36,wfd+44);
            int length=0;while(length<260&&raw[wfd+44+length]!=0)length++;
            require(length>0&&length<=259,"Bridge basename bound differs");
            String name=ascii(raw,wfd+44,length);basename(name);
            zero(raw,wfd+44+length,wfd+320);
            used=((used+7)&~7)+94+length*2;
            require(used<=8192,"Bridge exceeds native 8KiB geometry");
            rows.add(new Row(name,u32(b,wfd+32),b.getLong(wfd+20),(int)u32(b,wfd)));
        }
        return new BridgeBatch(sequence,first,done==1,rows,raw);
    }

    /** Immutable operation + compiled component attribution. This is supplied by
     * the reviewed owner, not discovered from booleans in an archive. */
    static final class Pins {
        final String operationId,sessionId,processInstance,namespaceSha256,fixtureNamespaceSha256;
        final String runtimeSha256,gameSha256,helperSha256,probeSha256,probeSourceSha256;
        final String recipeSourceSha256,buildFingerprintSha256,apkSha256,wineSha256,fexSha256,prootSha256;
        final int realUid;final long gameBytes,probeBytes,helperBytes,currentDevice;
        Pins(ClientGuestNamespace descriptor,String fixtureNamespace,String probe,long probeSize,
                String probeSource,String recipeSource,String buildFingerprint,long helperSize,
                String apk,String wine,String fex,String proot,long device)throws IOException {
            require(descriptor!=null,"Current finalized namespace required");
            ClientGuestNamespace.Provenance p=descriptor.provenance();
            for(String pin:new String[]{fixtureNamespace,probe,probeSource,recipeSource,buildFingerprint,apk,wine,fex,proot})digest(pin);
            require(probeSize>0&&probeSize<=1024*1024&&helperSize>0&&helperSize<=1024*1024,
                    "Tiny compiled fixture component bounds differ");
            operationId=p.operationId;sessionId=p.sessionId;processInstance=p.processInstance;
            namespaceSha256=descriptor.sha256();fixtureNamespaceSha256=fixtureNamespace;
            runtimeSha256=p.runtimeManifestSha256;gameSha256=p.nativeConsumerSha256;gameBytes=p.nativeConsumerBytes;
            helperSha256=p.helperIdentitySha256;helperBytes=helperSize;probeSha256=probe;probeBytes=probeSize;
            probeSourceSha256=probeSource;recipeSourceSha256=recipeSource;buildFingerprintSha256=buildFingerprint;realUid=p.realUid;
            apkSha256=apk;wineSha256=wine;fexSha256=fex;prootSha256=proot;currentDevice=device;
        }
        String canonical() {
            return SCHEMA+"\n"+operationId+"\n"+sessionId+"\n"+processInstance+"\n"+realUid+"\n"
                    +Long.toUnsignedString(currentDevice)+"\n"+namespaceSha256+"\n"+fixtureNamespaceSha256+"\n"+runtimeSha256+"\n"+gameSha256+"\n"+gameBytes+"\n"
                    +helperSha256+"\n"+helperBytes+"\n"+probeSha256+"\n"+probeBytes+"\n"+probeSourceSha256+"\n"
                    +recipeSourceSha256+"\n"+buildFingerprintSha256+"\n"+apkSha256+"\n"+wineSha256+"\n"+fexSha256+"\n"+prootSha256+"\n"+RECIPE+"\nfalse\nfalse\n";
        }
        boolean same(Pins other) {return other!=null&&canonical().equals(other.canonical());}
    }
    /** Exact current nofollow custody observation; path strings alone are not a
     * proof. The Android implementation must hold/recheck its exclusively owned
     * fixture roots and output parents, never the player's import/profile. */
    static final class DirectoryWitness {
        final String requestedGuest,resolvedGuest;final long device,inode;final int uid;
        DirectoryWitness(String request,String resolved,long dev,long ino,int owner)throws IOException {
            guest(request);guest(resolved);require(ino!=0&&owner>=0,"Current directory custody missing");
            requestedGuest=request;resolvedGuest=resolved;device=dev;inode=ino;uid=owner;
        }
        boolean same(DirectoryWitness other) {
            return other!=null&&requestedGuest.equals(other.requestedGuest)&&resolvedGuest.equals(other.resolvedGuest)
                    &&device==other.device&&inode==other.inode&&uid==other.uid;
        }
    }
    static final class DirectoryCase {
        final String label;final DirectoryWitness identity;private final byte[] token;
        DirectoryCase(String name,DirectoryWitness witness,byte[] cursorToken)throws IOException {
            require(name!=null&&name.matches("(?:state|import)_(?:fx|loc)")&&witness!=null,
                    "Exact tiny fixture case required");
            require(cursorToken!=null&&cursorToken.length==16,"Owned fixture cursor token required");
            label=name;identity=witness;token=cursorToken.clone();
            String root=name.startsWith("state_")?"/state/diagnostic/client-work-[0-9a-f]{24}/data/":"/game-import/data/";
            String branch=name.endsWith("_fx")?"fx":"scripts\\.loc";
            require(witness.requestedGuest.matches(root+branch+"/coh-live-fixture-[0-9a-f]{32}"),
                    "Fixture is not an isolated exact owned constructor subdirectory");
            require(witness.resolvedGuest.matches(root+branch+"/coh-live-fixture-[0-9a-f]{32}"),
                    "Tiny fixture aliases require a separate reviewed control");
            require(witness.requestedGuest.equals(witness.resolvedGuest),"Basic fixture cannot silently qualify an alias");
        }
        byte[] token(){return token.clone();}
    }
    interface OwnedFixture extends AutoCloseable {
        /** A fresh, exclusively owned namespace of tiny synthetic bindings.
         * Never pass the user's actual imported asset directory for mutation. */
        long namespace();
        List<DirectoryCase> cases();
        DirectoryWitness current(DirectoryCase directory)throws IOException;
        /** Recheck actual root binding paths, ancestor dev/inode/UID and output
         * parent custody before/after each native observation. */
        void revalidate()throws IOException;
        void close()throws IOException;
    }
    interface FixtureFactory {OwnedFixture prepare(Pins current)throws IOException;}
    interface ProbeStarter {
        /** Start only the authenticated tiny probe in the exact copied current
         * packaged PRoot/Wine/FEX recipe, with a fresh CREATE_NEW output outside
         * enumeration. No user assets/Game/SQL or arbitrary executable. */
        OwnedProbe start(Pins current,DirectoryCase directory)throws IOException;
    }
    /** Actual Android adapter must obtain these values from Os.fstat on the
     * held FileDescriptor and recheck its nofollow output-parent custody. A
     * typed host mock is not an Android or filesystem authority. */
    interface PacketMetadata {PacketIdentity current(FileDescriptor descriptor)throws IOException;}
    static final class PacketIdentity {
        final long device,inode,bytes;final int uid,mode;
        PacketIdentity(long dev,long ino,int owner,int type,long size){device=dev;inode=ino;uid=owner;mode=type;bytes=size;}
        boolean same(PacketIdentity other){return other!=null&&device==other.device&&inode==other.inode
                &&uid==other.uid&&mode==other.mode&&bytes==other.bytes;}
    }
    /** Held, independently fstat-verified ordinary output file. Arbitrary
     * InputStreams, pipes and socket packets are not accepted for NT evidence.
     * Reads run on an interruptible FileChannel with the whole-fixture deadline;
     * failure retains bounded bytes already read and closes only this descriptor. */
    static final class PacketFile implements AutoCloseable {
        private final FileInputStream stream;private final FileChannel channel;
        private final PacketMetadata metadata;private final PacketIdentity identity;
        private final ByteArrayOutputStream retained=new ByteArrayOutputStream();
        private Thread reader;private Throwable failure;private boolean used;
        PacketFile(FileInputStream owned,PacketMetadata current,int uid,long device)throws IOException {
            require(owned!=null&&current!=null,"Owned regular NT output descriptor required");
            stream=owned;channel=owned.getChannel();metadata=current;
            PacketIdentity observed;
            try{
                observed=current.current(owned.getFD());
                require(observed!=null&&(observed.mode&0170000)==0100000&&observed.uid==uid
                        &&observed.device==device&&observed.inode!=0&&observed.bytes>=0&&observed.bytes<=MAX_BYTES,
                        "Current NT packet regular type/device/UID/size differs");
                require(channel.isOpen()&&channel.size()==observed.bytes,"Held NT output size differs");
            }catch(Throwable problem){try{owned.close();}catch(Throwable cleanup){problem.addSuppressed(cleanup);}
                if(problem instanceof IOException)throw(IOException)problem;throw new IOException("Current NT output custody failed",problem);}
            identity=observed;
        }
        byte[] read(long deadline)throws IOException,InterruptedException {
            require(!used,"Owned NT packet descriptor cannot be replayed");used=true;
            reader=new Thread(()->{
                try{
                    channel.position(0);ByteBuffer buffer=ByteBuffer.allocate(4096);int zeroReads=0;
                    for(;;){if(deadline!=0)remainingMillis(deadline);buffer.clear();int got=channel.read(buffer);
                        if(got<0)break;if(got==0){require(++zeroReads<=16,"Non-advancing regular NT packet refused");continue;}
                        zeroReads=0;synchronized(retained){require(got<=MAX_BYTES-retained.size(),"NT packet byte cap exceeded");retained.write(buffer.array(),0,got);}}
                    require(identity.same(metadata.current(stream.getFD()))&&channel.size()==identity.bytes,
                            "Current NT packet retargeted/changed while read");
                }catch(Throwable problem){failure=problem;}
            },"coh-tiny-NT-packet");reader.setDaemon(true);reader.start();
            reader.join(deadline==0?1000:remainingMillis(deadline));
            require(!reader.isAlive(),"Whole tiny fixture packet IO bound exceeded");
            if(failure!=null)throw new IOException("Current owned NT packet read failed",failure);
            return snapshot();
        }
        byte[] snapshot(){synchronized(retained){return retained.toByteArray();}}
        public void close()throws IOException {
            IOException failed=null;try{channel.close();}catch(Throwable problem){failed=cleanupFailure(failed,problem);}
            try{stream.close();}catch(Throwable problem){failed=cleanupFailure(failed,problem);}
            if(reader!=null)try{reader.join(1000);if(reader.isAlive())throw new IOException("Owned NT packet reader cleanup incomplete");}
            catch(Throwable problem){if(problem instanceof InterruptedException)Thread.currentThread().interrupt();failed=cleanupFailure(failed,problem);}
            if(failed!=null)throw failed;
        }
    }
    interface OwnedProbe extends AutoCloseable {
        Process process();
        /** Read the exact owned output through current nofollow custody; never
         * accept an unrelated earlier packet. */
        PacketFile packet()throws IOException;
        /** Bind packet PID/thread to this held native child, current real UID,
         * current runtime/probe bytes, finalized recipe, start identity and
         * process-instance. Actual packaged implementation is still pending. */
        void verifyCurrent(Pins pins,NtObservation packet,Process process)throws IOException;
        /** Reap and close streams for this exact child. Must remain idempotent
         * and preserve current failure evidence when called after interruption. */
        void close()throws IOException;
    }
    private static final class CaseProgress {
        final DirectoryCase selected;byte[] raw,out,err;NtObservation nt;
        final List<BridgeBatch> bridge=new ArrayList<>();
        boolean compared,clean=true,waitCompleted,currentOwnerVerified;Integer exitCode;String failure,phase="OPEN_CURRENT_DIRECTORY",failurePhase;
        CaseProgress(DirectoryCase directory){selected=directory;}
    }
    static final class CaseResult {
        final String label,packetSha256,stdoutSha256,stderrSha256,failureType,failurePhase;
        final DirectoryWitness identity;
        final long nativePid,nativeThread;
        final int rows,ntBatches,bridgeBatches,packetBytes;
        final List<String> bridgeSha256;
        final boolean comparisonCompleted,cleanupCompleted,processWaitCompleted,currentOwnerVerifierCompleted;
        final Integer processExitCode;
        private final byte[] packetRaw,stdoutRaw,stderrRaw;
        private final List<byte[]> bridgeRaw;
        private CaseResult(CaseProgress progress)throws IOException {
            label=progress.selected.label;identity=progress.selected.identity;
            packetRaw=progress.raw==null?null:progress.raw.clone();
            stdoutRaw=progress.out==null?null:progress.out.clone();stderrRaw=progress.err==null?null:progress.err.clone();
            packetSha256=packetRaw==null?null:sha256(packetRaw);packetBytes=packetRaw==null?0:packetRaw.length;
            stdoutSha256=progress.out==null?null:sha256(progress.out);stderrSha256=progress.err==null?null:sha256(progress.err);
            nativePid=progress.nt==null?0:progress.nt.pid;nativeThread=progress.nt==null?0:progress.nt.thread;
            rows=progress.nt==null?0:progress.nt.rows.size();ntBatches=progress.nt==null?0:progress.nt.batches.size();
            bridgeBatches=progress.bridge.size();comparisonCompleted=progress.compared;
            cleanupCompleted=progress.clean;failureType=progress.failure;failurePhase=progress.failurePhase;
            processWaitCompleted=progress.waitCompleted;processExitCode=progress.exitCode;currentOwnerVerifierCompleted=progress.currentOwnerVerified;
            List<String> pins=new ArrayList<>();List<byte[]> raw=new ArrayList<>();
            for(BridgeBatch batch:progress.bridge){pins.add(batch.rawSha256);raw.add(batch.rawFrame());}
            bridgeSha256=immutable(pins);bridgeRaw=immutable(raw);
        }
        byte[] rawPacket(){return packetRaw==null?null:packetRaw.clone();}
        byte[] rawStdout(){return stdoutRaw==null?null:stdoutRaw.clone();}
        byte[] rawStderr(){return stderrRaw==null?null:stderrRaw.clone();}
        List<byte[]> rawBridge(){List<byte[]> copied=new ArrayList<>();for(byte[] row:bridgeRaw)copied.add(row.clone());return Collections.unmodifiableList(copied);}
    }
    enum Status {COMPARISON_PASSED,FAILED,INTERRUPTED}
    /** Private, immutable current result. Exported fields are diagnostics only;
     * there is intentionally no JSON receipt importer or enabled boolean. */
    static final class Receipt {
        final Pins pins;final Status status;final long startedUnixMillis,elapsedNanos;
        final List<CaseResult> cases;final String failureType;
        final boolean cleanupCompleted;
        private Receipt(Pins identity,Status state,long started,long elapsed,List<CaseResult> results,
                String reason,boolean clean) {
            pins=identity;status=state;startedUnixMillis=started;elapsedNanos=elapsed;
            cases=immutable(results);failureType=reason;cleanupCompleted=clean;
        }
        boolean matchesCurrent(Pins current) {return pins.same(current);}
        boolean comparisonPassed() {
            if(status!=Status.COMPARISON_PASSED||!cleanupCompleted||cases.size()!=4)return false;
            for(CaseResult result:cases)if(!result.comparisonCompleted||!result.cleanupCompleted)return false;
            return true;
        }
        /** Additional actual packaged alias/sharing/retarget, reviewed native
         * consumer and compiled-component admission gates remain mandatory. */
        boolean productionAdmissionAllowed() {return false;}
        Map<String,Object> diagnostic() {
            Map<String,Object> out=new LinkedHashMap<>();
            out.put("schema",SCHEMA);out.put("status",status.name());out.put("operation_id",pins.operationId);
            out.put("session_id",pins.sessionId);out.put("process_instance",pins.processInstance);
            out.put("real_uid",pins.realUid);out.put("current_device",Long.toUnsignedString(pins.currentDevice));out.put("namespace_sha256",pins.namespaceSha256);
            out.put("fixture_namespace_sha256",pins.fixtureNamespaceSha256);out.put("runtime_sha256",pins.runtimeSha256);
            out.put("game_sha256",pins.gameSha256);out.put("game_bytes",pins.gameBytes);
            out.put("helper_sha256",pins.helperSha256);out.put("helper_bytes",pins.helperBytes);
            out.put("probe_sha256",pins.probeSha256);out.put("probe_bytes",pins.probeBytes);
            out.put("probe_source_sha256",pins.probeSourceSha256);out.put("recipe_source_sha256",pins.recipeSourceSha256);
            out.put("build_fingerprint_sha256",pins.buildFingerprintSha256);out.put("recipe",RECIPE);
            out.put("apk_sha256",pins.apkSha256);out.put("wine_sha256",pins.wineSha256);
            out.put("fex_sha256",pins.fexSha256);out.put("proot_sha256",pins.prootSha256);
            out.put("show_dot_files",false);out.put("case_sensitive",false);
            out.put("scope","current_constructor_name_sizeLow_writeFILETIME_DIR_READONLY_HIDDEN_SYSTEM");
            out.put("started_unix_millis",startedUnixMillis);out.put("elapsed_nanos",elapsedNanos);
            out.put("cleanup_completed",cleanupCompleted);out.put("failure_type",failureType);
            out.put("production_admission_allowed",false);out.put("exported_json_is_authority",false);
            out.put("packaged_alias_sharing_retarget_controls","PENDING_SEPARATE_CURRENT_RUNTIME_GATES");
            out.put("device_performance_measured",false);
            List<Map<String,Object>> values=new ArrayList<>();
            for(CaseResult c:cases) {
                Map<String,Object> item=new LinkedHashMap<>();item.put("case",c.label);
                item.put("original_guest_request",c.identity.requestedGuest);item.put("resolved_guest_target",c.identity.resolvedGuest);
                item.put("device",Long.toUnsignedString(c.identity.device));item.put("inode",Long.toUnsignedString(c.identity.inode));
                item.put("uid",c.identity.uid);item.put("native_pid",c.nativePid);item.put("native_thread",c.nativeThread);
                item.put("packet_sha256",c.packetSha256);item.put("packet_bytes",c.packetBytes);
                item.put("stdout_sha256",c.stdoutSha256);item.put("stderr_sha256",c.stderrSha256);
                item.put("rows",c.rows);item.put("nt_batches",c.ntBatches);item.put("bridge_batches",c.bridgeBatches);
                item.put("bridge_sha256",c.bridgeSha256);item.put("comparison_completed",c.comparisonCompleted);
                item.put("cleanup_completed",c.cleanupCompleted);item.put("failure_type",c.failureType);item.put("failure_phase",c.failurePhase);
                item.put("process_wait_completed",c.processWaitCompleted);item.put("native_probe_exit_code",c.processExitCode);
                item.put("current_owner_verifier_completed",c.currentOwnerVerifierCompleted);
                item.put("outer_native_process_custody_proof_required",true);
                List<String> omitted=new ArrayList<>();if(c.packetSha256==null)omitted.add("current_native_packet_unavailable");
                if(c.stdoutSha256==null)omitted.add("current_native_stdout_unavailable");if(c.stderrSha256==null)omitted.add("current_native_stderr_unavailable");
                item.put("evidence_omissions",Collections.unmodifiableList(omitted));values.add(Collections.unmodifiableMap(item));
            }
            out.put("cases",Collections.unmodifiableList(values));return Collections.unmodifiableMap(out);
        }
    }

    /** Concrete bounded execution, ready for a reviewed Android owner adapter.
     * IO bounds apply only to this tiny fixture, never login/world/playtime.
     * Host Process/NativeApi mocks exercise ownership, not Android authority. */
    static Receipt run(Pins pins,byte[] operation,FixtureFactory factory,ProbeStarter starter,
            ClientLiveDirectoryOperation.NativeApi nativeApi,long ioMillis) {
        if(pins==null)throw new IllegalArgumentException("Current compiled-component pins required");
        long started=System.currentTimeMillis(),begin=System.nanoTime();List<CaseResult> results=new ArrayList<>();
        OwnedFixture fixture=null;Throwable failure=null;boolean clean=true;Status status=Status.FAILED;
        try {
            require(pins!=null&&operation!=null&&operation.length==16&&factory!=null&&starter!=null&&nativeApi!=null,
                    "Complete current tiny fixture dependencies required");
            require(ioMillis>0&&ioMillis<=MAX_FIXTURE_IO_MILLIS,"Finite tiny fixture IO bound differs");
            byte[] frozenOperation=operation.clone();require(Arrays.equals(frozenOperation,wire(pins.sessionId)),
                    "Fixture operation bytes differ from current session");
            long deadline=begin+TimeUnit.MILLISECONDS.toNanos(ioMillis);remainingMillis(deadline);
            fixture=factory.prepare(pins);require(fixture!=null&&fixture.namespace()!=0,"Owned tiny fixture namespace missing");
            List<DirectoryCase> dirs=new ArrayList<>(fixture.cases());require(dirs.size()==4,"Four exact constructor fixture cases required");
            String[] labels={"state_fx","state_loc","import_fx","import_loc"};
            for(int i=0;i<4;i++) {
                DirectoryCase directory=dirs.get(i);require(directory!=null&&labels[i].equals(directory.label),"Fixture case scope/order differs");
                require(directory.identity.uid==pins.realUid&&directory.identity.device==pins.currentDevice,"Fixture device/owner differs from current app");
                for(int prior=0;prior<i;prior++) {
                    require(directory.identity.device!=dirs.get(prior).identity.device
                            ||directory.identity.inode!=dirs.get(prior).identity.inode,"Aliased fixture directories refused");
                    require(!Arrays.equals(directory.token(),dirs.get(prior).token()),"Duplicate fixture directory token refused");
                }
            }
            for(DirectoryCase directory:dirs)runCase(pins,frozenOperation,fixture,directory,starter,nativeApi,deadline,results);
            remainingMillis(deadline);
            status=Status.COMPARISON_PASSED;
        } catch(Throwable problem) {
            failure=problem;status=problem instanceof InterruptedException?Status.INTERRUPTED:Status.FAILED;
            if(problem instanceof InterruptedException)Thread.currentThread().interrupt();
        } finally {
            if(fixture!=null)try{fixture.close();}catch(Throwable problem){clean=false;if(failure==null)failure=problem;else failure.addSuppressed(problem);}
        }
        for(CaseResult result:results)if(!result.cleanupCompleted)clean=false;
        if(!clean)status=Status.FAILED;
        return new Receipt(pins,status,started,System.nanoTime()-begin,results,safeFailure(failure),clean);
    }
    private static void runCase(Pins pins,byte[] operation,OwnedFixture fixture,DirectoryCase selected,
            ProbeStarter starter,ClientLiveDirectoryOperation.NativeApi api,long deadline,List<CaseResult> results)throws Exception {
        CaseProgress progress=new CaseProgress(selected);
        OwnedProbe owned=null;Process process=null;long cursor=0;Throwable failed=null;StreamCapture stdout=null,stderr=null;
        try {
            remainingMillis(deadline);fixture.revalidate();require(selected.identity.same(fixture.current(selected)),"Original request/current root identity changed");
            cursor=api.open(fixture.namespace(),selected.identity.requestedGuest,operation.clone(),selected.token());
            require(cursor!=0,"Native fixture cursor missing");verifyCursor(api,cursor,selected.identity);
            progress.phase="START_CURRENT_PROBE";remainingMillis(deadline);owned=starter.start(pins,selected);require(owned!=null&&(process=owned.process())!=null,"Exact owned probe Process missing");
            stdout=new StreamCapture(process.getInputStream());stderr=new StreamCapture(process.getErrorStream());
            stdout.start();stderr.start();
            progress.phase="WAIT_CURRENT_PROBE";if(!process.waitFor(remainingMillis(deadline),TimeUnit.MILLISECONDS))throw new IOException("Tiny owned probe IO bound exceeded");
            progress.waitCompleted=true;progress.exitCode=process.exitValue();
            stdout.finish(remainingMillis(deadline));stderr.finish(remainingMillis(deadline));
            byte[] raw;
            progress.phase="CAPTURE_CURRENT_PACKET";
            raw=capturePacket(progress,owned,deadline);
            progress.raw=raw;progress.out=stdout.bytes();progress.err=stderr.bytes();
            NtObservation nt=parseNt(raw);progress.nt=nt;progress.phase="VERIFY_CURRENT_NATIVE_EXECUTION";
            require(process.exitValue()==0,"Current tiny native probe exited unsuccessfully");owned.verifyCurrent(pins,nt,process);progress.currentOwnerVerified=true;
            require(nt.mode==1&&nt.complete&&!nt.cleanupFailed,"Current stock NT observation incomplete");
            require(nt.inode==selected.identity.inode,"NT held FileInternal inode differs from JNI/current path");
            require(dosGuest(nt.originalDosPath,false).equals(selected.identity.requestedGuest)
                    &&dosGuest(nt.finalDosPath,true).equals(selected.identity.resolvedGuest),"NT original/resolved directory differs");
            console(nt,stdout.bytes(),stderr.bytes());
            progress.phase="COMPARE_CURRENT_BRIDGE";List<BridgeBatch> bridge=progress.bridge;long first=0;boolean finalBatch=false;
            for(int number=0;number<MAX_BATCHES&&!finalBatch;number++) {
                remainingMillis(deadline);fixture.revalidate();require(selected.identity.same(fixture.current(selected)),"Fixture path retargeted during observation");
                verifyCursor(api,cursor,selected.identity);
                BridgeBatch batch=parseBridge(api.next(cursor),operation,selected.token(),number,first);
                bridge.add(batch);first+=batch.rows.size();finalBatch=batch.finished;
                verifyCursor(api,cursor,selected.identity);
            }
            require(finalBatch,"Bridge final frame missing");compare(nt,bridge,selected.identity);
            fixture.revalidate();require(selected.identity.same(fixture.current(selected)),"Fixture changed after comparison");
            remainingMillis(deadline);progress.compared=true;
        } catch(Throwable problem) {failed=problem;progress.failure=safeFailure(problem);progress.failurePhase=progress.phase;throw problem;}
        finally {
            Throwable cleanup=null;
            if(cursor!=0)try{api.closeCursor(cursor);}catch(Throwable problem){cleanup=problem;}
            if(owned!=null)try{owned.close();}catch(Throwable problem){if(cleanup==null)cleanup=problem;else cleanup.addSuppressed(problem);}
            else if(process!=null)try{process.destroy();}catch(Throwable problem){if(cleanup==null)cleanup=problem;else cleanup.addSuppressed(problem);}
            // A failed or interrupted probe can still leave a useful current
            // partial packet. The owned adapter retains only its CREATE_NEW
            // output through nofollow custody after stopping/reaping this child.
            if(owned!=null&&progress.raw==null)try {
                progress.raw=capturePacket(progress,owned,System.nanoTime()+TimeUnit.SECONDS.toNanos(1));
                try{progress.nt=parseNt(progress.raw);}catch(IOException incomplete){/* raw remains exportable */}
            }catch(Throwable omitted){/* explicit omission; cleanup flag retained by capturePacket */}
            if(stdout!=null)try{stdout.close();}catch(Throwable problem){if(cleanup==null)cleanup=problem;else cleanup.addSuppressed(problem);}
            if(stderr!=null)try{stderr.close();}catch(Throwable problem){if(cleanup==null)cleanup=problem;else cleanup.addSuppressed(problem);}
            // Capture after every independent close/join attempt: late EOF bytes
            // must remain exportable even when stream cleanup also failed.
            if(stdout!=null&&progress.out==null)try{progress.out=stdout.snapshot();}catch(Throwable omitted){}
            if(stderr!=null&&progress.err==null)try{progress.err=stderr.snapshot();}catch(Throwable omitted){}
            if(cleanup!=null){progress.clean=false;if(progress.failure==null){progress.failure=safeFailure(cleanup);progress.failurePhase="OWNED_CLEANUP";}}
            results.add(new CaseResult(progress));
            if(cleanup!=null){if(failed!=null)failed.addSuppressed(cleanup);else throw new IOException("Owned fixture child/cursor cleanup failed",cleanup);}
        }
    }
    private static byte[] capturePacket(CaseProgress progress,OwnedProbe owned,long deadline)throws Exception {
        PacketFile packet=null;Throwable failed=null;
        try{
            packet=owned.packet();require(packet!=null,"Current owned regular NT packet missing");return packet.read(deadline);
        }catch(Throwable problem){failed=problem;throw problem;}
        finally{
            if(packet!=null){
                progress.raw=packet.snapshot();
                try{packet.close();}catch(Throwable problem){progress.clean=false;
                    if(failed!=null)failed.addSuppressed(problem);else throw new IOException("Owned NT packet cleanup failed",problem);}
            }
        }
    }
    static void compare(NtObservation nt,List<BridgeBatch> bridge,DirectoryWitness witness)throws IOException {
        require(nt!=null&&witness!=null&&bridge!=null&&nt.complete&&nt.mode==1&&!nt.cleanupFailed&&nt.inode==witness.inode,
                "Current independent stock/JNI directory witness differs");
        require(dosGuest(nt.originalDosPath,false).equals(witness.requestedGuest)
                &&dosGuest(nt.finalDosPath,true).equals(witness.resolvedGuest),"Current original/resolved NT path differs");
        int ntAt=0,first=0;boolean finished=false;
        for(int i=0;i<bridge.size();i++) {
            BridgeBatch current=bridge.get(i);
            require(current!=null&&!finished&&current.sequence==i&&current.first==first,"Bridge transcript gap/duplicate/post-final");
            if(current.rows.isEmpty())require(nt.batches.isEmpty()&&i==0&&bridge.size()==1&&current.finished,"Unexpected empty final bridge frame");
            else {
                require(ntAt<nt.batches.size(),"Extra JNI observation batch");NtBatch stock=nt.batches.get(ntAt++);
                require(stock.rows.size()==current.rows.size(),"Native 8KiB batch cardinality differs");int offset=0;
                for(int row=0;row<current.rows.size();row++) {
                    Row actual=current.rows.get(row);
                    require(actual.same(stock.rows.get(row)),"Current constructor field/order parity differs");
                    offset=(offset+7)&~7;require(stock.offsets.get(row)==offset,"Current NT aligned record geometry differs");
                    offset+=94+actual.name.length()*2;
                }
                require(offset<=stock.rawBytes&&offset<=8192,"NT geometry exceeds returned buffer");
            }
            first+=current.rows.size();finished=current.finished;
        }
        require(finished&&ntAt==nt.batches.size()&&first==nt.rows.size(),"Incomplete NT/JNI transcript parity");
    }
    private static void verifyCursor(ClientLiveDirectoryOperation.NativeApi api,long cursor,DirectoryWitness expected)throws IOException {
        long[] held=api.identity(cursor);
        require(held!=null&&held.length==3&&held[0]==expected.device&&held[1]==expected.inode&&held[2]==expected.uid,
                "JNI held directory dev/inode/UID differs");
        require(expected.resolvedGuest.equals(api.canonicalGuestPath(cursor)),"JNI original request resolved to a different target");
    }
    private static void console(NtObservation nt,byte[] out,byte[] err)throws IOException {
        String text=ascii(out,0,out.length);ascii(err,0,err.length);
        String expected="COH_NT_PROBE_RESULT pid="+nt.pid+" mode=1 complete=1 rows="+nt.rows.size()
                +" batches="+nt.batches.size()+" input_cleanup_failed=0 bytes="+nt.rawBytes;
        int found=0;for(String line:text.split("\\r?\\n",-1))if(line.startsWith("COH_NT_PROBE_RESULT")){require(line.equals(expected),"Native completion console differs");found++;}
        require(found==1,"Exactly one current native completion console required");
    }
    private static final class StreamCapture extends Thread implements AutoCloseable {
        final InputStream stream;private final ByteArrayOutputStream retained=new ByteArrayOutputStream();
        private volatile Throwable failure;
        StreamCapture(InputStream input)throws IOException {require(input!=null,"Owned probe stream missing");stream=input;setDaemon(true);setName("coh-tiny-NT-fixture-console");}
        public void run(){try{
            byte[] buffer=new byte[4096];int zero=0;
            for(;;){int got=stream.read(buffer);if(got<0)break;if(got==0){require(++zero<=16,"Non-advancing console refused");continue;}zero=0;
                synchronized(retained){int room=MAX_CONSOLE_BYTES-retained.size();if(room>0)retained.write(buffer,0,Math.min(room,got));require(got<=room,"Current console byte cap exceeded");}}
        }catch(Throwable problem){failure=problem;}}
        void finish(long millis)throws IOException,InterruptedException {join(millis);require(!isAlive(),"Owned probe console did not close");if(failure!=null)throw new IOException("Bounded current probe console failed",failure);}
        byte[] snapshot(){synchronized(retained){return retained.toByteArray();}}
        byte[] bytes()throws IOException {require(!isAlive()&&failure==null,"Current probe console unavailable");return snapshot();}
        public void close()throws IOException {
            IOException failed=null;try{stream.close();}catch(Throwable problem){failed=cleanupFailure(failed,problem);}
            try{join(1000);require(!isAlive(),"Owned console thread cleanup incomplete");}
            catch(Throwable problem){if(problem instanceof InterruptedException)Thread.currentThread().interrupt();failed=cleanupFailure(failed,problem);}
            if(failed!=null)throw failed;
        }
    }
    static byte[] readBounded(InputStream stream,int bound)throws IOException {return readBounded(stream,bound,0);}
    private static byte[] readBounded(InputStream stream,int bound,long deadline)throws IOException {
        require(stream!=null&&bound>0&&bound<=MAX_BYTES,"Bounded current packet stream required");
        ByteArrayOutputStream data=new ByteArrayOutputStream(Math.min(bound,4096));byte[] buffer=new byte[4096];
        int zeroReads=0;
        for(;;){if(deadline!=0)remainingMillis(deadline);int count=stream.read(buffer);if(deadline!=0)remainingMillis(deadline);if(count<0)break;if(count==0){require(++zeroReads<=16,"Non-advancing fixture stream refused");continue;}
            zeroReads=0;require(count<=bound-data.size(),"Current fixture evidence byte cap exceeded");data.write(buffer,0,count);}
        return data.toByteArray();
    }
    private static IOException cleanupFailure(IOException earlier,Throwable problem) {
        IOException wrapped=problem instanceof IOException?(IOException)problem:new IOException("Owned fixture resource cleanup failed",problem);
        if(earlier==null)return wrapped;earlier.addSuppressed(wrapped);return earlier;
    }
    private static byte[] wire(String session)throws IOException {
        require(session!=null&&session.matches("[0-9a-f]{32}"),"Exact current wire session required");byte[] out=new byte[16];
        for(int i=0;i<16;i++)out[i]=(byte)Integer.parseInt(session.substring(i*2,i*2+2),16);return out;
    }
    private static long remainingMillis(long deadline)throws IOException {
        long remaining=deadline-System.nanoTime();require(remaining>0,"Whole tiny fixture IO bound exceeded");
        return Math.max(1,TimeUnit.NANOSECONDS.toMillis(remaining));
    }
    static String dosGuest(String value,boolean finalPath)throws IOException {
        require(value!=null,"NT path missing");String path=value;
        if(finalPath){require(path.startsWith("\\\\?\\"),"Normalized NT final-object prefix missing");path=path.substring(4);}
        require(path.length()>=4&&(path.startsWith("Z:\\")||path.startsWith("Z:/")),"Only current Wine Z guest mapping admitted");
        path=path.substring(2).replace('\\','/');guest(path);return path;
    }
    private static void guest(String path)throws IOException {
        require(path!=null&&path.startsWith("/")&&path.length()<1024&&!path.endsWith("/")&&!path.contains("//"),"Canonical guest path required");
        for(String part:path.substring(1).split("/",-1)){basename(part);require(!part.equals(".")&&!part.equals("..")&&!part.endsWith(".")&&!part.endsWith(" ")&&!part.contains(".l2s."),"Guest alias/dot/legacy path refused");}
    }
    private static String ntName(byte[] raw,int start,int bytes)throws IOException {
        StringBuilder name=new StringBuilder();for(int at=start;at<start+bytes;at+=2){int c=(raw[at]&255)|((raw[at+1]&255)<<8);require(c>=32&&c<127,"Unsupported NT basename");name.append((char)c);}
        String text=name.toString();basename(text);return text;
    }
    private static void basename(String name)throws IOException {
        require(name!=null&&!name.isEmpty()&&name.length()<=259,"ASCII basename bound differs");
        for(int i=0;i<name.length();i++){char c=name.charAt(i);require(c>=32&&c<127&&"/\\:*?\"<>|".indexOf(c)<0,"Unsupported basename");}
    }
    private static String ascii(byte[] bytes,int begin,int length)throws IOException {
        require(begin>=0&&length>=0&&begin+(long)length<=bytes.length,"ASCII span differs");
        for(int i=begin;i<begin+length;i++)require((bytes[i]&255)<128&&bytes[i]!=0,"Non-ASCII/NUL current evidence refused");
        return new String(bytes,begin,length,StandardCharsets.US_ASCII);
    }
    private static String safeFailure(Throwable problem) {
        if(problem==null)return null;String type=problem.getClass().getSimpleName();return type.length()>128?type.substring(0,128):type;
    }
    private static <T> List<T> immutable(List<T> values){return Collections.unmodifiableList(new ArrayList<T>(values));}
    private static ByteBuffer le(byte[] bytes){return ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN);}
    private static long u32(ByteBuffer b,int at){return Integer.toUnsignedLong(b.getInt(at));}
    private static int count(long n,int max)throws IOException {require(n<=max,"Integer/span cap exceeded");return(int)n;}
    private static void zero(byte[] bytes,int begin,int end)throws IOException {for(int i=begin;i<end;i++)require(bytes[i]==0,"Reserved/non-consumed normalized field differs");}
    private static boolean hasMagic(byte[] bytes,int at,String text) {if(at<0||at+(long)text.length()>bytes.length)return false;for(int i=0;i<text.length();i++)if(bytes[at+i]!=(byte)text.charAt(i))return false;return true;}
    private static void magic(byte[] bytes,int at,String text)throws IOException {require(hasMagic(bytes,at,text),"Unknown packet magic");}
    private static String sha256(byte[] bytes)throws IOException {try{byte[] digest=MessageDigest.getInstance("SHA-256").digest(bytes);StringBuilder out=new StringBuilder();for(byte b:digest)out.append(String.format(java.util.Locale.ROOT,"%02x",b&255));return out.toString();}catch(Exception missing){throw new IOException("SHA-256 unavailable",missing);}}
    private static void digest(String value)throws IOException {require(value!=null&&value.matches("[0-9a-f]{64}"),"Exact source/component digest required");}
    private static void require(boolean value,String reason)throws IOException {if(!value)throw new IOException(reason);}
}
