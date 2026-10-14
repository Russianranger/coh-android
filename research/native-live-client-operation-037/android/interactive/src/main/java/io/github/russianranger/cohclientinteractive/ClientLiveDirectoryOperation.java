package io.github.russianranger.cohclientinteractive;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Collections;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Dormant, current-operation owner for the initial Game directory constructor.
 *
 * This class does not load a native library, parse an activation artifact, enable
 * a runtime feature, or claim Android qualification. Its trusted caller must
 * validate the compiled artifacts and current packaged PRoot/Wine/FEX fixture
 * before returning a ReviewedActivation. Descriptor provenance alone grants no
 * authority. Current lstat observations are rechecked by native held-FD custody.
 */
final class ClientLiveDirectoryOperation implements AutoCloseable {
    static final String RECIPE = "wine-b073-constructor-v1";
    static final String ACTIVATION_SCHEMA = "COH_CLIENT_LIVE_DIRECTORY_ACTIVATION_V1";
    static final long CORE_HEAP_LIMIT = 32L * 1024 * 1024;

    enum Gate {
        REVIEWED_NATIVE_SOURCE, NATIVE_GAME_COMPATIBILITY, ARM64_HELPER_ABI,
        CURRENT_PACKAGED_PROOT_WINE_FEX_FIXTURE, APK_COMPONENT_PROVENANCE,
        CURRENT_RUNTIME_IDENTITY
    }

    /** Implemented only by the operation owner's reviewed artifact validator.
     * A mock implementation in host tests is not native or Android authority. */
    interface ActivationContract {
        ReviewedActivation verifyCurrent(ClientGuestNamespace namespace,
                String canonicalAppFilesRoot, String currentGuestDataRoot) throws IOException;
    }

    /** Immutable result of external validation, not a parser for untrusted data. */
    static final class ReviewedActivation {
        final String schema, artifactSha256, namespaceSha256, appFilesRoot, guestDataRoot;
        final ClientGuestNamespace.Provenance identity;
        final String recipe;
        final boolean showDotFiles, caseSensitive;
        final Map<Gate,String> gateProofSha256;
        ReviewedActivation(String artifact, String namespace, String files, String data,
                ClientGuestNamespace.Provenance current, String selectedRecipe,
                boolean dots, boolean sensitive, Map<Gate,String> proofs) throws IOException {
            require(current != null && proofs != null, "Complete reviewed activation required");
            sha(artifact); sha(namespace);
            EnumMap<Gate,String> copied = new EnumMap<>(Gate.class);
            copied.putAll(proofs);
            require(copied.size() == Gate.values().length, "Every current activation gate required");
            for (Gate gate : Gate.values()) sha(copied.get(gate));
            require(RECIPE.equals(selectedRecipe) && !dots && !sensitive,
                    "Unqualified Wine constructor settings refused");
            schema = ACTIVATION_SCHEMA; artifactSha256 = artifact; namespaceSha256 = namespace;
            appFilesRoot = files; guestDataRoot = data; identity = current; recipe = selectedRecipe;
            showDotFiles = dots; caseSensitive = sensitive;
            gateProofSha256 = Collections.unmodifiableMap(copied);
        }
        private void bind(ClientGuestNamespace namespace, String files, String data) throws IOException {
            ClientGuestNamespace.Provenance actual = namespace.provenance();
            require(namespaceSha256.equals(namespace.sha256()) && same(appFilesRoot, files)
                    && same(guestDataRoot, data) && identity.operationId.equals(actual.operationId)
                    && identity.sessionId.equals(actual.sessionId)
                    && identity.processInstance.equals(actual.processInstance) && identity.realUid == actual.realUid
                    && identity.runtimeManifestSha256.equals(actual.runtimeManifestSha256)
                    && identity.nativeConsumerSha256.equals(actual.nativeConsumerSha256)
                    && identity.nativeConsumerBytes == actual.nativeConsumerBytes
                    && identity.helperIdentitySha256.equals(actual.helperIdentitySha256),
                    "Reviewed activation does not belong to this exact current operation");
        }
    }

    /** Android caller must implement this with actual current nofollow lstat;
     * canonical strings or mock fixture results are not filesystem authority. */
    interface Metadata { DirectoryIdentity currentDirectory(String canonicalPath) throws IOException; }
    static final class DirectoryIdentity {
        final String canonicalPath;
        final long device, inode;
        final int uid;
        final boolean directory, symbolicLink;
        DirectoryIdentity(String path, long dev, long ino, int owner, boolean isDirectory, boolean isLink) {
            canonicalPath = path; device = dev; inode = ino; uid = owner;
            directory = isDirectory; symbolicLink = isLink;
        }
    }

    interface NativeApi {
        long create(String[] guest, String[] host, long[] device, long[] inode, int[] uid,
                int nativeUid, int guestUid, boolean showDotFiles, boolean caseSensitive) throws IOException;
        long open(long namespace, String guestDirectory, byte[] operation, byte[] directory) throws IOException;
        byte[] next(long cursor) throws IOException;
        void closeCursor(long cursor) throws IOException;
        void closeNamespace(long namespace) throws IOException;
        long[] stats(long namespace) throws IOException;
        long[] identity(long cursor) throws IOException;
        String canonicalGuestPath(long cursor) throws IOException;
    }

    /** No loadLibrary or registration occurs while obtaining this facade. */
    static NativeApi jniFacade() {
        return new NativeApi() {
            public long create(String[] g,String[] h,long[] d,long[] i,int[] u,int n,int v,boolean dot,boolean sensitive)throws IOException {
                return NativeLiveDirectory.nativeCreate(g,h,d,i,u,n,v,dot,sensitive);
            }
            public long open(long n,String g,byte[] o,byte[] d)throws IOException { return NativeLiveDirectory.nativeOpen(n,g,o,d); }
            public byte[] next(long c)throws IOException { return NativeLiveDirectory.nativeNext(c); }
            public void closeCursor(long c)throws IOException { NativeLiveDirectory.nativeCloseCursor(c); }
            public void closeNamespace(long n)throws IOException { NativeLiveDirectory.nativeCloseNamespace(n); }
            public long[] stats(long n)throws IOException { return NativeLiveDirectory.nativeStats(n); }
            public long[] identity(long c)throws IOException { return NativeLiveDirectory.nativeIdentity(c); }
            public String canonicalGuestPath(long c)throws IOException { return NativeLiveDirectory.nativeCanonicalGuestPath(c); }
        };
    }

    /** Test seam for construction failures; a starter owns any partially opened
     * socket, while this factory retains namespace ownership until return. */
    interface ServiceStarter {
        ClientLiveDirectoryService start(byte[] operation, long device, int uid,
                ClientLiveDirectoryService.Backend backend, ClientLiveDirectoryService.PathAdmission paths,
                ClientLiveDirectoryService.Journal journal) throws IOException;
    }

    private final ClientGuestNamespace descriptor;
    private final ReviewedActivation activation;
    private final NativeBackend backend;
    private final ClientLiveDirectoryService service;
    private boolean closed;

    private ClientLiveDirectoryOperation(ClientGuestNamespace descriptor, ReviewedActivation activation,
            NativeBackend backend, ClientLiveDirectoryService service) {
        this.descriptor=descriptor; this.activation=activation; this.backend=backend; this.service=service;
    }

    static ClientLiveDirectoryOperation create(ClientGuestNamespace descriptor, String canonicalAppFilesRoot,
            String currentGuestDataRoot, ActivationContract activation, Metadata metadata, NativeApi nativeApi,
            ClientLiveDirectoryService.Journal journal) throws IOException {
        return create(descriptor,canonicalAppFilesRoot,currentGuestDataRoot,activation,metadata,nativeApi,journal,
            (operation,device,uid,backend,paths,events) ->
                new ClientLiveDirectoryService(operation,device,uid,backend,paths,events));
    }

    static ClientLiveDirectoryOperation create(ClientGuestNamespace descriptor, String canonicalAppFilesRoot,
            String currentGuestDataRoot, ActivationContract contract, Metadata metadata, NativeApi nativeApi,
            ClientLiveDirectoryService.Journal journal, ServiceStarter starter) throws IOException {
        require(descriptor!=null && contract!=null && metadata!=null && nativeApi!=null && journal!=null && starter!=null,
                "Complete current operation dependencies required");
        require(currentGuestDataRoot!=null && currentGuestDataRoot.matches(
                "/state/diagnostic/client-work-[0-9a-f]{24}/data"), "Current Game view required");
        require(canonicalAppFilesRoot!=null && canonicalAppFilesRoot.startsWith("/")
                && descriptor.canonicalStatement().contains("\napp_files_root:"
                    +canonicalAppFilesRoot.getBytes(StandardCharsets.UTF_8).length+":"+canonicalAppFilesRoot+"\n"),
                "App files root differs from finalized namespace");
        ReviewedActivation admitted = contract.verifyCurrent(descriptor,canonicalAppFilesRoot,currentGuestDataRoot);
        require(admitted!=null, "Current reviewed activation was refused");
        admitted.bind(descriptor,canonicalAppFilesRoot,currentGuestDataRoot);
        List<ClientGuestNamespace.Binding> bindings=descriptor.ownedDirectoryBindings();
        require(bindings.size()==7, "Exact seven finalized owned directory bindings required");
        int uid=descriptor.provenance().realUid;
        DirectoryIdentity app=owned(metadata.currentDirectory(canonicalAppFilesRoot),canonicalAppFilesRoot,uid);
        String[] guest=new String[7], host=new String[7];
        long[] device=new long[7], inode=new long[7]; int[] owner=new int[7];
        DirectoryIdentity[] observations=new DirectoryIdentity[7];
        for(int i=0;i<7;i++) {
            ClientGuestNamespace.Binding binding=bindings.get(i);
            require(binding.kind==ClientGuestNamespace.Kind.DIRECTORY
                    && binding.hostRoot.startsWith(canonicalAppFilesRoot+"/"), "Foreign directory binding refused");
            DirectoryIdentity item=owned(metadata.currentDirectory(binding.hostRoot),binding.hostRoot,uid);
            require(item.device==app.device, "Cross-device directory binding refused");
            for(int prior=0;prior<i;prior++) require(item.device!=device[prior] || item.inode!=inode[prior],
                    "Aliased owned directory bindings refused");
            guest[i]=binding.guestPrefix; host[i]=binding.hostRoot;
            device[i]=item.device; inode[i]=item.inode; owner[i]=item.uid; observations[i]=item;
        }
        long namespace=0; NativeBackend backend=null; ClientLiveDirectoryService service=null;
        try {
            // Native create independently opens/rechecks/holds all ancestors and
            // expected dev/inode/UID values. Java observations do not replace it.
            namespace=nativeApi.create(guest,host,device,inode,owner,uid,1000,false,false);
            require(namespace!=0, "Native current namespace missing");
            backend=new NativeBackend(namespace,nativeApi,descriptor,currentGuestDataRoot,app.device,uid);
            stable(app,owned(metadata.currentDirectory(canonicalAppFilesRoot),canonicalAppFilesRoot,uid));
            for(int i=0;i<7;i++) stable(observations[i],owned(metadata.currentDirectory(host[i]),host[i],uid));
            final String root=currentGuestDataRoot;
            ClientLiveDirectoryService.PathAdmission paths=path -> {
                try { descriptor.initialCensusDirectory(path,root); return true; }
                catch(IOException refused) { return false; }
            };
            service=starter.start(descriptor.operationWireIdentity(),app.device,uid,backend,paths,journal);
            require(service!=null, "Owned metadata service missing");
            return new ClientLiveDirectoryOperation(descriptor,admitted,backend,service);
        } catch(Throwable problem) {
            try {
                if(service!=null) service.close();
                else if(backend!=null) backend.close();
                else if(namespace!=0) nativeApi.closeNamespace(namespace);
            } catch(Throwable cleanup) { problem.addSuppressed(cleanup); }
            throwFailure(problem);
            throw new AssertionError("Unreachable");
        }
    }

    private static DirectoryIdentity owned(DirectoryIdentity value,String path,int uid)throws IOException {
        require(value!=null && same(value.canonicalPath,path) && value.directory && !value.symbolicLink
                && value.uid==uid, "Current directory path/type/owner differs");
        return value;
    }
    private static void stable(DirectoryIdentity before,DirectoryIdentity after)throws IOException {
        require(before.device==after.device && before.inode==after.inode && before.uid==after.uid,
                "Current directory was retargeted during registration");
    }

    private static final class NativeCursor {
        final String requestedPath, resolvedPath;
        final long[] identity;
        NativeCursor(String requested,String resolved,long[] identity) {
            requestedPath=requested; resolvedPath=resolved; this.identity=identity.clone();
        }
    }
    enum StatisticsPhase {
        CURRENT, CURRENT_STATISTICS_OMITTED,
        VALIDATED_FINAL_BEFORE_NAMESPACE_CLOSE, FINAL_STATISTICS_OMITTED
    }
    /** Optional six-counter evidence. Owned heap is observed at this snapshot,
     * before namespace free; it is not Game/process/device memory or RSS. */
    static final class StatisticsSnapshot {
        final StatisticsPhase phase;
        final Map<String,Long> values;
        final String omission;
        private static final StatisticsSnapshot CURRENT_UNAVAILABLE=new StatisticsSnapshot(
                StatisticsPhase.CURRENT_STATISTICS_OMITTED,Collections.emptyMap(),
                "Current scoped counter capture omitted");
        private static final StatisticsSnapshot FINAL_UNAVAILABLE=new StatisticsSnapshot(
                StatisticsPhase.FINAL_STATISTICS_OMITTED,Collections.emptyMap(),
                "Final scoped counter capture omitted before namespace close");
        private StatisticsSnapshot(StatisticsPhase phase,Map<String,Long> values,String omission) {
            this.phase=phase; this.values=Collections.unmodifiableMap(values); this.omission=omission;
        }
        private static StatisticsSnapshot omitted(boolean finalCapture,Throwable problem) {
            // Do not copy a native exception message into diagnostics: it can
            // contain private paths or credentials. Even optional allocation
            // failure here must leave a usable omission and permit cleanup.
            try {
                String type=problem.getClass().getSimpleName();
                if(type.length()>128) type=type.substring(0,128);
                return new StatisticsSnapshot(finalCapture ? StatisticsPhase.FINAL_STATISTICS_OMITTED
                        : StatisticsPhase.CURRENT_STATISTICS_OMITTED,Collections.emptyMap(),
                        (finalCapture ? "Final" : "Current")+" scoped counter capture omitted: "
                            +type);
            } catch(Throwable unavailable) {
                return finalCapture ? FINAL_UNAVAILABLE : CURRENT_UNAVAILABLE;
            }
        }
    }
    private static final class NativeBackend implements ClientLiveDirectoryService.Backend {
        private long namespace;
        private final NativeApi api;
        private final ClientGuestNamespace descriptor;
        private final String dataRoot;
        private final long device;
        private final int uid;
        private final Map<Long,NativeCursor> cursors=new LinkedHashMap<>();
        // Initialize fallback storage during backend construction. Any failure
        // there remains inside the factory's owned-namespace cleanup boundary.
        private final StatisticsSnapshot finalOmissionFallback=StatisticsSnapshot.FINAL_UNAVAILABLE;
        private StatisticsSnapshot finalStatistics;
        NativeBackend(long namespace,NativeApi api,ClientGuestNamespace descriptor,String dataRoot,long device,int uid) {
            this.namespace=namespace; this.api=api; this.descriptor=descriptor; this.dataRoot=dataRoot;
            this.device=device; this.uid=uid;
        }
        public synchronized long open(String path,byte[] operation,byte[] token)throws IOException {
            require(namespace!=0, "Owned metadata namespace is closed");
            descriptor.initialCensusDirectory(path,dataRoot);
            require(Arrays.equals(operation,descriptor.operationWireIdentity()) && token!=null && token.length==16,
                    "Metadata cursor belongs to another operation");
            long handle=0;
            try {
                handle=api.open(namespace,path,operation.clone(),token.clone());
                require(handle!=0 && !cursors.containsKey(handle), "Native metadata cursor missing or reused");
                String resolved=api.canonicalGuestPath(handle);
                resolvedTarget(path,resolved);
                long[] identity=checkedIdentity(api.identity(handle));
                cursors.put(handle,new NativeCursor(path,resolved,identity));
                return handle;
            } catch(Throwable problem) {
                if(handle!=0 && cursors.containsKey(handle)) {
                    // A reused native handle cannot be distinguished from the
                    // already owned cursor. Close the namespace, never retry.
                    poison(problem);
                } else if(handle!=0) {
                    try { api.closeCursor(handle); } catch(Throwable cleanup) {
                        problem.addSuppressed(cleanup); poison(problem);
                    }
                }
                throwFailure(problem); throw new AssertionError("Unreachable");
            }
        }
        public synchronized long[] identity(long handle)throws IOException {
            NativeCursor cursor=current(handle);
            long[] now=checkedIdentity(api.identity(handle));
            require(Arrays.equals(cursor.identity,now), "Held native directory identity changed");
            return now.clone();
        }
        public synchronized byte[] next(long handle)throws IOException {
            NativeCursor cursor=current(handle);
            try {
                // Core stores requested_guest and its separately resolved guest
                // target. Qualified current-view links and Wine case resolution
                // may change the spelling. Pin that resolved target; core still
                // re-resolves the original request before/after every batch.
                require(cursor.resolvedPath.equals(api.canonicalGuestPath(handle)),
                        "Current resolved guest directory was retargeted");
                descriptor.initialCensusDirectory(cursor.requestedPath,dataRoot);
                require(Arrays.equals(cursor.identity,checkedIdentity(api.identity(handle))),
                        "Held native directory identity changed");
                byte[] batch=api.next(handle);
                require(batch!=null, "Native metadata allocation did not produce a batch");
                return batch;
            } catch(Throwable problem) {
                // nativeNext may already have advanced before a Java allocation
                // fails. Close this operation's namespace; never retry a cursor.
                poison(problem); throwFailure(problem); throw new AssertionError("Unreachable");
            }
        }
        private long[] checkedIdentity(long[] value)throws IOException {
            require(value!=null && value.length==3 && value[0]==device && value[2]==uid,
                    "Held native directory differs from current registered device/owner");
            return value;
        }
        private void resolvedTarget(String requested,String resolved)throws IOException {
            require(resolved!=null, "Native resolved guest directory missing");
            ClientGuestNamespace.Route route=descriptor.route(resolved);
            require(route.binding.kind==ClientGuestNamespace.Kind.DIRECTORY,
                    "Resolved guest directory is not an owned binding");
            String targetRoot;
            if(resolved.startsWith(dataRoot+"/")) {
                require(route.binding.guestPrefix.equals("/state"), "Current Game view binding differs");
                targetRoot=dataRoot;
            } else if(resolved.startsWith("/game-import/data/")) {
                require(route.binding.guestPrefix.equals("/game-import"), "Current imported data binding differs");
                targetRoot="/game-import/data";
            } else {
                throw new IOException("Resolved directory is outside the two qualified current data views");
            }
            String requestedBranch=requested.substring(dataRoot.length()+1).split("/",2)[0];
            String resolvedBranch=resolved.substring(targetRoot.length()+1).split("/",2)[0];
            require((resolvedBranch.equalsIgnoreCase("fx") || resolvedBranch.equalsIgnoreCase("scripts.loc"))
                    && resolvedBranch.equalsIgnoreCase(requestedBranch),
                    "Resolved directory changed the qualified constructor branch");
        }
        private NativeCursor current(long handle)throws IOException {
            require(namespace!=0, "Owned metadata namespace is closed");
            NativeCursor cursor=cursors.get(handle); require(cursor!=null, "Unowned native metadata cursor");
            return cursor;
        }
        public synchronized void closeCursor(long handle)throws IOException {
            if(namespace==0) return;
            NativeCursor cursor=cursors.remove(handle); if(cursor==null) return;
            try { api.closeCursor(handle); }
            catch(Throwable problem) { poison(problem); throwFailure(problem); }
        }
        private void poison(Throwable problem) {
            try { close(); } catch(Throwable cleanup) { problem.addSuppressed(cleanup); }
        }
        public synchronized void close()throws IOException {
            if(namespace==0) return;
            long owned=namespace; namespace=0; IOException problems=null;
            for(long cursor:cursors.keySet()) try { api.closeCursor(cursor); }
            catch(Throwable problem) { problems=append(problems,problem); }
            cursors.clear();
            // Preserve validated optional observations after cursor cleanup,
            // while the exclusively owned namespace still exists. Metrics do
            // not turn a normal Game close into a failed operation, and never
            // replace a native failure or prevent namespace release.
            finalStatistics=finalOmissionFallback;
            try {
                try { finalStatistics=readStatistics(owned,StatisticsPhase.VALIDATED_FINAL_BEFORE_NAMESPACE_CLOSE); }
                catch(Throwable omitted) { finalStatistics=StatisticsSnapshot.omitted(true,omitted); }
            } finally {
                try { api.closeNamespace(owned); } catch(Throwable problem) { problems=append(problems,problem); }
            }
            if(problems!=null) throw problems;
        }
        synchronized StatisticsSnapshot statistics() {
            if(namespace==0) return finalStatistics!=null ? finalStatistics : finalOmissionFallback;
            try { return readStatistics(namespace,StatisticsPhase.CURRENT); }
            catch(Throwable omitted) { return StatisticsSnapshot.omitted(false,omitted); }
        }
        private StatisticsSnapshot readStatistics(long owned,StatisticsPhase phase)throws IOException {
            long[] counters=api.stats(owned);
            require(counters!=null && counters.length==6, "Bounded native statistics required");
            for(long counter:counters) require(counter>=0, "Negative native counter refused");
            require(counters[4]<=counters[5] && counters[5]<=CORE_HEAP_LIMIT, "Native core heap bound differs");
            String[] labels={"entry_metadata_requests","directory_names_snapshotted","observation_batches",
                "missing_entries_at_observation","bounded_core_owned_heap_bytes","bounded_core_peak_heap_bytes"};
            Map<String,Long> result=new LinkedHashMap<>();
            for(int i=0;i<6;i++) result.put(labels[i],counters[i]);
            return new StatisticsSnapshot(phase,result,null);
        }
        synchronized StatisticsSnapshot retainedFinalStatistics() { return finalStatistics; }
        synchronized boolean isOpen() { return namespace!=0; }
    }

    synchronized Map<String,String> diagnosticDescriptor() {
        Map<String,String> result=new LinkedHashMap<>();
        ClientGuestNamespace.Provenance identity=descriptor.provenance();
        result.put("schema",ACTIVATION_SCHEMA); result.put("operation_id",identity.operationId);
        result.put("session_id",identity.sessionId); result.put("process_instance",identity.processInstance);
        result.put("namespace_sha256",descriptor.sha256()); result.put("activation_artifact_sha256",activation.artifactSha256);
        result.put("runtime_manifest_sha256",identity.runtimeManifestSha256);
        result.put("native_consumer_sha256",identity.nativeConsumerSha256);
        result.put("native_consumer_bytes",Long.toString(identity.nativeConsumerBytes));
        result.put("helper_identity_sha256",identity.helperIdentitySha256);
        result.put("recipe",activation.recipe); result.put("guest_data_root",activation.guestDataRoot);
        result.put("scope","initial_Game_fx_and_scripts.loc_constructor_fields_only");
        result.put("statistics_scope","entry_metadata_requests_and_bounded_core_heap_not_total_syscalls_or_RSS");
        StatisticsSnapshot retained=backend.retainedFinalStatistics();
        if(retained!=null) {
            result.put("statistics_capture_phase",retained.phase.name());
            result.put("statistics_owned_heap_scope","observation_before_final_namespace_close_not_after_free_memory");
            if(retained.omission!=null) result.put("statistics_omission",retained.omission);
        }
        for(Gate gate:Gate.values()) result.put("gate_"+gate.name(),activation.gateProofSha256.get(gate));
        return Collections.unmodifiableMap(result);
    }
    synchronized StatisticsSnapshot statistics() {
        return backend.statistics();
    }
    /** Secret-bearing fields for an exclusively owned mode-0600 control file.
     * The owner supplies these only to Game, never general Wine/Map/argv/logs. */
    synchronized Map<String,String> privateGameControlFields()throws IOException {
        require(!closed && backend.isOpen() && service.failure()==null,
                "Current metadata operation is closed or failed");
        Map<String,String> result=new LinkedHashMap<>(); String prefix="COH_CLIENT_LIVE_DIRECTORY";
        result.put(prefix,"1"); result.put(prefix+"_ENDPOINT","127.0.0.1:"+service.port());
        result.put(prefix+"_SESSION",descriptor.provenance().sessionId);
        result.put(prefix+"_AUTH",ClientLiveDirectoryService.hex(service.authenticationNonce()));
        result.put(prefix+"_DEVICE",Long.toUnsignedString(backend.device));
        result.put(prefix+"_GUEST_ROOT",activation.guestDataRoot); result.put(prefix+"_RECIPE",activation.recipe);
        result.put(prefix+"_DESCRIPTOR",descriptor.sha256());
        return Collections.unmodifiableMap(result);
    }
    /** Exact document for /tmp/client-live-directory-control.json. This method
     * writes no file and supplies no JSON enable/qualification authority. */
    synchronized Map<String,Object> privateGameControlDocument()throws IOException {
        Map<String,String> control=privateGameControlFields();
        ClientGuestNamespace.Provenance identity=descriptor.provenance();
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("format",1); result.put("session_id",identity.sessionId);
        result.put("operation_id",identity.operationId); result.put("process_instance",identity.processInstance);
        result.put("game_sha256",identity.nativeConsumerSha256); result.put("game_bytes",identity.nativeConsumerBytes);
        result.put("runtime_sha256",identity.runtimeManifestSha256); result.put("helper_sha256",identity.helperIdentitySha256);
        result.put("descriptor_sha256",descriptor.sha256()); result.put("guest_root",activation.guestDataRoot);
        result.put("recipe",activation.recipe); result.put("device",control.get("COH_CLIENT_LIVE_DIRECTORY_DEVICE"));
        result.put("endpoint",control.get("COH_CLIENT_LIVE_DIRECTORY_ENDPOINT"));
        result.put("auth_nonce",control.get("COH_CLIENT_LIVE_DIRECTORY_AUTH"));
        return Collections.unmodifiableMap(result);
    }
    IOException failure() { return service.failure(); }
    public synchronized void close()throws IOException {
        if(closed) return; closed=true; service.close();
    }
    private static IOException append(IOException previous,Throwable problem) {
        IOException wrapped=problem instanceof IOException ? (IOException)problem
            : new IOException("Owned native metadata cleanup failed",problem);
        if(previous==null) return wrapped; previous.addSuppressed(wrapped); return previous;
    }
    private static void throwFailure(Throwable problem)throws IOException {
        if(problem instanceof IOException) throw (IOException)problem;
        if(problem instanceof RuntimeException) throw (RuntimeException)problem;
        if(problem instanceof Error) throw (Error)problem;
        throw new IOException("Current live metadata operation failed",problem);
    }
    private static boolean same(String first,String second) { return first!=null && first.equals(second); }
    private static void sha(String value)throws IOException {
        require(value!=null && value.matches("[0-9a-f]{64}"), "Exact reviewed evidence digest required");
    }
    private static void require(boolean condition,String reason)throws IOException {
        if(!condition) throw new IOException(reason);
    }
}
