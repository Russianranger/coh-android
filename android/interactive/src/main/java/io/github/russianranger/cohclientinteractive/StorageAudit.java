package io.github.russianranger.cohclientinteractive;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.util.*;

/** Read-only app-private inventory and an explicit, conservative cleanup policy.
 * No database, client state, import generation or guest cache is removable here.
 * Filesystem access is injected so the actual policy can be exercised on a JVM.
 */
public final class StorageAudit {
    private StorageAudit() {}
    public enum Kind { FILE, DIRECTORY, SYMLINK, OTHER }
    public static final class Stat {
        public final Kind kind;
        public final long device, inode, links, size, blocks, modified, changed;
        public Stat(Kind kind,long device,long inode,long links,long size,long blocks,long modified,long changed) {
            this.kind=kind;this.device=device;this.inode=inode;this.links=links;
            this.size=size;this.blocks=blocks;this.modified=modified;this.changed=changed;
        }
        public long allocated() throws IOException {
            if(size<0||blocks<0||blocks>Long.MAX_VALUE/512||links<1)throw new IOException("Invalid filesystem metadata");
            return blocks*512;
        }
        boolean same(Stat other) {
            return other!=null&&kind==other.kind&&device==other.device&&inode==other.inode&&links==other.links
                    &&size==other.size&&blocks==other.blocks&&modified==other.modified&&changed==other.changed;
        }
        boolean sameDirectory(Stat other) {
            return other!=null&&kind==Kind.DIRECTORY&&other.kind==Kind.DIRECTORY
                    &&device==other.device&&inode==other.inode;
        }
    }
    public interface Fs {
        /** Empty path is the verified application files directory. Missing paths return null. */
        Stat stat(String path) throws IOException;
        String rootPath();
        default List<String> rootAliases(){return Collections.singletonList(rootPath());}
        String readLink(String path) throws IOException;
        List<String> list(String path) throws IOException;
        /** Production uses a descriptor-anchored iterator, retaining no directory member list. */
        default void visitDirectory(String path, NameVisitor visitor) throws IOException {
            for(String name:list(path))visitor.visit(name);
        }
        /** Private temporary cache journal, outside the inventoried files directory. */
        default File cleanupJournal() throws IOException {return File.createTempFile("coh-storage-", ".journal");}
        byte[] read(String path,int limit) throws IOException;
        Map<String,Object> json(byte[] bytes) throws IOException;
        /** Bounded read of android-client-report.json inside an owned regular ZIP. */
        Map<String,Object> reportIdentity(String archive,int limit) throws IOException;
        void unlink(String path) throws IOException;
        void rmdir(String path) throws IOException;
        default void remove(String path,Stat expected,Stat expectedParent) throws IOException {
            Stat actual=stat(path);
            if(!expected.same(actual)||!expectedParent.sameDirectory(stat(parent(path))))throw new IOException("Cleanup entry or parent changed");
            if(actual.kind==Kind.DIRECTORY)rmdir(path);else unlink(path);
        }
        long nowMillis();
    }
    public interface NameVisitor {void visit(String name) throws IOException;}
    public interface ProgressListener {void update(String phase,int entries,String path,long elapsedMillis) throws IOException;}
    private static final ProgressListener NO_PROGRESS=(phase,entries,path,elapsed)->{};
    public static final class Limits {
        public final int maximumEntries,maximumDepth;
        public final long maximumMillis;
        public Limits(int entries,int depth,long millis) {
            if(entries<1||depth<1||millis<1)throw new IllegalArgumentException("Invalid scan limits");
            maximumEntries=entries;maximumDepth=depth;maximumMillis=millis;
        }
        public static Limits defaults(){return new Limits(2000000,128,600000);}
    }
    public static final class Category {
        public final String id,label;
        public final boolean removable;
        public final long apparentBytes,allocatedBytes,reclaimableBytes;
        public final int candidateCount;
        Category(Tally value) {
            id=value.id;label=value.label;removable=value.removable;
            apparentBytes=value.apparent;allocatedBytes=value.allocated;reclaimableBytes=value.reclaim;
            candidateCount=value.candidates;
        }
    }
    public static final class Candidate {
        public final String path,categoryId;
        public final long apparentBytes,allocatedBytes,reclaimableBytes;
        private final Stat root;
        private final String fingerprint;
        Candidate(MutableCandidate value) {
            path=value.path;categoryId=value.category;root=value.root;fingerprint=value.fingerprint;
            apparentBytes=value.apparent;allocatedBytes=value.allocated;reclaimableBytes=value.reclaim;
        }
    }
    public static final class Plan {
        public final String snapshotId,currentManifestSha256;
        public final boolean complete,currentRuntimeVerified,cleanupAllowed;
        public final long scannedUtcMs,apparentBytes,allocatedBytes,reclaimableBytes;
        public final int entryCount;
        public final List<Category> categories;
        public final List<Candidate> candidates;
        public final List<String> errors;
        private final String inventoryDigest,guardDigest;
        private final Stat filesRoot;
        Plan(Scanner scanner) {
            scannedUtcMs=scanner.started;complete=scanner.complete;
            currentRuntimeVerified=scanner.currentReady;cleanupAllowed=complete&&currentRuntimeVerified&&scanner.errors.isEmpty();
            currentManifestSha256=scanner.currentHash;filesRoot=scanner.root;
            entryCount=scanner.entries;inventoryDigest=hex(scanner.inventory.digest());guardDigest=scanner.guards;
            snapshotId=hash((inventoryDigest+"\n"+guardDigest+"\n"+currentHash(scanner)).getBytes(StandardCharsets.UTF_8));
            List<Category> summaries=new ArrayList<>();long logical=0,allocated=0,reclaim=0;
            for(Tally tally:scanner.tallies.values()) {
                summaries.add(new Category(tally));logical=safeAdd(logical,tally.apparent);
                allocated=safeAdd(allocated,tally.allocated);reclaim=safeAdd(reclaim,tally.reclaim);
            }
            categories=Collections.unmodifiableList(summaries);apparentBytes=logical;allocatedBytes=allocated;reclaimableBytes=cleanupAllowed?reclaim:0;
            List<Candidate> options=new ArrayList<>();for(MutableCandidate candidate:scanner.options.values())if(candidate.safe)options.add(new Candidate(candidate));
            candidates=Collections.unmodifiableList(options);errors=Collections.unmodifiableList(new ArrayList<>(scanner.errors));
        }
        private static String currentHash(Scanner scanner){return scanner.currentHash==null?"":scanner.currentHash;}
        public String toJson(){return encode(planMap(this));}
    }
    public static final class CleanupResult {
        public final Plan afterPlan;
        public final boolean stalePlan,completed;
        public final int deletedCount,skippedCount;
        /** Allocated blocks of successfully removed final inode links/directories, not free-space delta. */
        public final long reclaimedBytes;
        public final List<String> errors;
        public final String sourceSnapshotId;
        CleanupResult(Plan plan,Plan after,boolean stale,boolean completed,int removed,int skipped,long reclaimed,List<String> errors) {
            sourceSnapshotId=plan.snapshotId;afterPlan=after;stalePlan=stale;this.completed=completed;
            deletedCount=removed;skippedCount=skipped;reclaimedBytes=reclaimed;
            this.errors=Collections.unmodifiableList(new ArrayList<>(errors));
        }
        public String toJson() {
            Map<String,Object> value=new LinkedHashMap<>();value.put("format",1);value.put("scope","app_private_storage_cleanup");
            value.put("source_snapshot_id",sourceSnapshotId);value.put("stale_plan",stalePlan);value.put("completed",completed);
            value.put("deleted_entries",deletedCount);value.put("skipped_entries",skippedCount);
            value.put("removed_inode_allocated_bytes",reclaimedBytes);value.put("errors",errors);value.put("after",planMap(afterPlan));
            return encode(value);
        }
    }
    private static final String RUNTIME="runtime-[0-9a-f]{16}";
    private static final String RUN="[0-9]{13}-[0-9a-f]{12}";
    private static final String DOWNLOAD="(?:base|wine|database environment|Windows runtime)-[0-9a-f]{64}\\.tar\\.gz(?:\\.part)?";
    private static final Set<String> RUNTIME_MEMBERS=new HashSet<>(Arrays.asList("rootfs","wine","pg","assets","game-package","dbserver","schema","game-data-manifest.json","passwd","group","ready.json"));
    private static final String[] REQUIRED={"rootfs/usr/bin/python3","rootfs/usr/bin/Xtigervnc","wine/bin/wine","wine/bin/wineserver","pg/opt/coh/pgsql/bin/postgres","pg/opt/coh/pgsql/bin/initdb"};
    private static final class Tally {
        final String id,label;final boolean removable;long apparent,allocated,reclaim;int candidates;
        Tally(String id,String label,boolean removable){this.id=id;this.label=label;this.removable=removable;}
    }
    private static final class Inode {
        final long dev,ino;Inode(Stat s){dev=s.device;ino=s.inode;}
        public boolean equals(Object value){return value instanceof Inode&&((Inode)value).dev==dev&&((Inode)value).ino==ino;}
        public int hashCode(){return 31*Long.hashCode(dev)+Long.hashCode(ino);}
    }
    private static final class InodeUse {
        final Stat stat;final String firstCategory;String onlyCandidate;int seen;
        InodeUse(Stat stat,String category,String candidate){this.stat=stat;firstCategory=category;onlyCandidate=candidate;seen=1;}
    }
    private static final class MutableCandidate {
        final String path,category;final Stat root;final Fingerprint digest=new Fingerprint();
        String fingerprint;long apparent,allocated,reclaim;boolean safe=true;
        MutableCandidate(String path,String category,Stat root){this.path=path;this.category=category;this.root=root;}
    }
    public static Plan scan(Fs fs,String currentManifestSha256,Limits limits) {
        return scan(fs,currentManifestSha256,limits,NO_PROGRESS);
    }
    public static Plan scan(Fs fs,String currentManifestSha256,Limits limits,ProgressListener progress) {
        Scanner scanner=new Scanner(fs,currentManifestSha256,limits,progress);scanner.run();return new Plan(scanner);
    }
    private static final class Scanner {
        final Fs fs;final String currentHash;final Limits limits;final long started;
        final Fingerprint inventory=new Fingerprint();final Map<String,Tally> tallies=new LinkedHashMap<>();
        final Map<String,MutableCandidate> options=new LinkedHashMap<>();final Map<Inode,InodeUse> inodes=new HashMap<>();
        final List<String> errors=new ArrayList<>();final Set<String> keptReports=new HashSet<>();
        final ProgressListener progress;long nextProgress;String lastPath="";
        Stat root;boolean complete=true,currentReady=false;int entries;String guards="";
        Scanner(Fs fs,String hash,Limits limits,ProgressListener listener) {
            this.fs=fs;currentHash=hash;this.limits=limits;progress=listener==null?NO_PROGRESS:listener;started=fs.nowMillis();
            add("current_runtime","Current runtime",false);add("old_runtime","Verified older runtimes",true);
            add("runtime_other","Unverified runtime files and staging",false);add("downloads","Runtime download cache",true);
            add("old_reports","Older completed test reports",true);add("reports_kept","Recent and protected test reports",false);
            add("client_state","Character, server data, Wine and client caches",false);add("client_import","Imported client and server assets",false);
            add("other","Other protected app files",false);
        }
        void add(String id,String label,boolean removable){tallies.put(id,new Tally(id,label,removable));}
        void error(String reason){if(errors.size()<32)errors.add(reason);complete=false;}
        void run() {
            try {
                checkpoint("checking identities",true);
                root=fs.stat("");if(root==null||root.kind!=Kind.DIRECTORY)throw new IOException("App files root is not a private directory");
                if(currentHash==null||!currentHash.matches("[0-9a-f]{64}"))throw new IOException("Current package identity is invalid");
                String current="m2/runtime-"+currentHash.substring(0,16);
                currentReady=runtimeVerified(current,currentHash,true);
                guards=guardFingerprint(current);
                protectReports();identify(current);
                walk("",null,null,0);
                if(!root.same(fs.stat("")))throw new IOException("App files changed during the scan");
                if(!guards.equals(guardFingerprint(current)))throw new IOException("Protected runtime or report pointer changed during the scan");
                for(InodeUse use:inodes.values()) {
                    if(use.stat.kind==Kind.DIRECTORY)continue;
                    if(use.stat.links<use.seen)throw new IOException("Inconsistent hard-link metadata");
                    if(use.onlyCandidate!=null&&use.seen==use.stat.links) {
                        MutableCandidate candidate=options.get(use.onlyCandidate);
                        if(candidate!=null&&candidate.safe)candidate.reclaim=safeAdd(candidate.reclaim,use.stat.allocated());
                    }
                }
                for(MutableCandidate candidate:options.values()) {
                    candidate.fingerprint=hex(candidate.digest.digest());
                    if(!candidate.safe) {
                        candidate.reclaim=0;Tally source=tallies.get(candidate.category);
                        source.apparent-=candidate.apparent;source.allocated-=candidate.allocated;
                        Tally protectedTally=tallies.get(candidate.category.equals("old_reports")?"reports_kept":"runtime_other");
                        protectedTally.apparent=safeAdd(protectedTally.apparent,candidate.apparent);
                        protectedTally.allocated=safeAdd(protectedTally.allocated,candidate.allocated);continue;
                    }
                    Tally tally=tallies.get(candidate.category);tally.candidates++;
                    tally.reclaim=safeAdd(tally.reclaim,candidate.reclaim);
                }
            } catch(Exception e){error(message(e));}
            try{checkpoint(complete?"scan complete":"scan incomplete",true);}catch(IOException failure){error(message(failure));}
        }
        void checkpoint(String phase,boolean force) throws IOException {
            long now=fs.nowMillis();if(force||now>=nextProgress) {
                nextProgress=now+5000;progress.update(phase,entries,lastPath,Math.max(0,now-started));
            }
        }
        void check(int depth) throws IOException {
            if(Thread.currentThread().isInterrupted())throw new IOException("Storage scan cancelled");
            if(entries>=limits.maximumEntries||depth>limits.maximumDepth||fs.nowMillis()-started>limits.maximumMillis)
                throw new IOException("Storage scan reached its entry, depth or time limit; cleanup is disabled");
            if((entries&1023)==0) {
                ensureMemory("Storage scan reached its memory budget; cleanup is disabled");
                checkpoint("scanning files",false);
            }
        }
        boolean runtimeVerified(String path,String expected,boolean executables) throws IOException {
            Stat dir=fs.stat(path);if(dir==null||dir.kind!=Kind.DIRECTORY)return false;
            Stat ready=fs.stat(path+"/ready.json"),manifest=fs.stat(path+"/assets/runtime-manifest.json");
            if(!singleRegular(ready)||!singleRegular(manifest))return false;
            Map<String,Object> r=fs.json(fs.read(path+"/ready.json",16384));
            Object recorded=r.get("manifest_sha256");if(!(recorded instanceof String)||!((String)recorded).matches("[0-9a-f]{64}"))return false;
            String full=(String)recorded;if(expected!=null&&!expected.equals(full))return false;
            if(!path.endsWith("runtime-"+full.substring(0,16)))return false;
            byte[] bytes=fs.read(path+"/assets/runtime-manifest.json",2097152);
            if(!full.equals(hash(bytes)))return false;
            Map<String,Object> parsed=fs.json(bytes);
            if(!number(parsed.get("format"),1)||!(parsed.get("files") instanceof Map))return false;
            Map<?,?> files=(Map<?,?>)parsed.get("files");if(files.isEmpty()||files.size()>128)return false;
            for(Map.Entry<?,?> file:files.entrySet()) {
                Object key=file.getKey();if(!(key instanceof String)||!((String)key).matches("[A-Za-z0-9_.-]+")||!(file.getValue() instanceof Map))return false;
                Map<?,?> pin=(Map<?,?>)file.getValue();Object bytesValue=pin.get("bytes"),shaValue=pin.get("sha256");
                if(!(bytesValue instanceof Number)||((Number)bytesValue).longValue()<0||((Number)bytesValue).doubleValue()!=((Number)bytesValue).longValue()
                        ||!(shaValue instanceof String)||!((String)shaValue).matches("[0-9a-f]{64}"))return false;
                if(executables) {
                    Stat payload=fs.stat(path+"/assets/"+key);
                    if(!singleRegular(payload)||payload.size!=((Number)bytesValue).longValue())return false;
                }
            }
            for(String member:Arrays.asList("rootfs","wine","pg","assets")) {
                Stat stat=fs.stat(path+"/"+member);if(stat==null||stat.kind!=Kind.DIRECTORY)return false;
            }
            for(String name:fs.list(path))if(!RUNTIME_MEMBERS.contains(name))return false;
            if(executables)for(String executable:REQUIRED) {
                String scope=path+"/"+executable.substring(0,executable.indexOf('/'));
                if(!containedRegular(fs,path+"/"+executable,scope))return false;
            }
            return true;
        }
        String guardFingerprint(String current) throws IOException {
            MessageDigest digest=digest();
            for(String path:Arrays.asList("", "m2",current,current+"/ready.json",current+"/assets",current+"/assets/runtime-manifest.json","client","client/latest-report.txt","client/reports")) {
                Stat stat=fs.stat(path);feed(digest,path,stat);
                if(stat!=null&&(path.endsWith("ready.json")||path.endsWith("runtime-manifest.json")||path.endsWith("latest-report.txt"))) {
                    if(!singleRegular(stat))throw new IOException("Protected identity or pointer is linked or unreadable");
                    digest.update(fs.read(path,path.endsWith("runtime-manifest.json")?2097152:16384));
                }
            }
            return hex(digest.digest());
        }
        void protectReports() throws IOException {
            Stat reports=fs.stat("client/reports");
            if(reports!=null&&reports.kind==Kind.DIRECTORY) {
                List<String> names=new ArrayList<>(fs.list("client/reports"));
                names.removeIf(name->!name.matches(RUN));names.sort(Collections.reverseOrder());
                for(int i=0;i<Math.min(3,names.size());i++)keptReports.add(names.get(i));
            }
            Stat pointer=fs.stat("client/latest-report.txt");
            if(pointer!=null) {
                if(!singleRegular(pointer))throw new IOException("Latest report pointer is linked or not regular");
                String pointed=new String(fs.read("client/latest-report.txt",4096),StandardCharsets.UTF_8).trim();
                // Pointer is emitted as an absolute private path. Only its exact owned report suffix is used.
                int marker=pointed.lastIndexOf("/client/reports/");
                String relative=marker<0?pointed:pointed.substring(marker+1);
                if(!relative.matches("client/reports/"+RUN+"/coh-[a-z0-9-]+-"+RUN+"\\.zip"))
                    throw new IOException("Latest report pointer cannot be safely anchored");
                String[] parts=relative.split("/");
                if(!parts[3].endsWith(parts[2]+".zip"))throw new IOException("Latest report pointer and run disagree");
                // Adapter verifies an absolute pointer is inside its own files root.
                if(!singleRegular(fs.stat(relative)))throw new IOException("Latest report archive is unavailable");
                keptReports.add(parts[2]);
            }
        }
        void identify(String current) throws IOException {
            Stat home=fs.stat("m2");
            if(home!=null&&home.kind==Kind.DIRECTORY)for(String name:fs.list("m2")) {
                String path="m2/"+name;
                if(!path.equals(current)&&name.matches(RUNTIME)&&runtimeVerified(path,null,false))
                    options.put(path,new MutableCandidate(path,"old_runtime",fs.stat(path)));
            }
            Stat downloads=fs.stat("m2/downloads");
            if(currentReady&&downloads!=null&&downloads.kind==Kind.DIRECTORY)for(String name:fs.list("m2/downloads")) {
                String path="m2/downloads/"+name;Stat stat=fs.stat(path);
                if(name.matches(DOWNLOAD)&&singleRegular(stat))options.put(path,new MutableCandidate(path,"downloads",stat));
            }
            Stat reports=fs.stat("client/reports");
            if(reports!=null&&reports.kind==Kind.DIRECTORY)for(String name:fs.list("client/reports")) {
                if(!name.matches(RUN)||keptReports.contains(name))continue;
                String path="client/reports/"+name;Stat stat=fs.stat(path);
                if(stat==null||stat.kind!=Kind.DIRECTORY)continue;
                String archive=null;boolean incomplete=false;
                for(String child:fs.list(path)) {
                    if(child.endsWith(".part"))incomplete=true;
                    if(child.matches("coh-[a-z0-9-]+-"+name+"\\.zip")&&singleRegular(fs.stat(path+"/"+child))) {
                        if(archive!=null){incomplete=true;break;}archive=path+"/"+child;
                    }
                }
                if(incomplete||archive==null)continue;
                Map<String,Object> identity;
                try{identity=fs.reportIdentity(archive,2097152);}catch(IOException invalid){continue;}
                if(identity!=null&&number(identity.get("format"),1)&&name.equals(identity.get("run_id"))
                        &&Arrays.asList("passed","failed","cancelled","client_incomplete","cleanup_failed","setup_complete","import_complete","input_incomplete","display_incomplete").contains(identity.get("status")))
                    options.put(path,new MutableCandidate(path,"old_reports",stat));
            }
        }
        void walk(String path,String category,MutableCandidate candidate,int depth) throws IOException {
            check(depth);Stat stat=fs.stat(path);if(stat==null)throw new IOException("A file disappeared during the scan");
            stat.allocated();entries++;lastPath=path;feed(inventory,path,stat);
            if(options.containsKey(path))candidate=options.get(path);
            if(candidate!=null)category=candidate.category;
            else category=category(path);
            Tally tally=tallies.get(category);tally.apparent=safeAdd(tally.apparent,stat.size);
            if(candidate!=null){candidate.apparent=safeAdd(candidate.apparent,stat.size);feed(candidate.digest,path,stat);}
            // A POSIX inode with nlink=1 cannot appear at another directory entry.
            // Directories cannot be hard-linked in the app's nofollow tree. Retain only shared inode accounting.
            if(stat.kind==Kind.DIRECTORY||stat.links==1) {
                tally.allocated=safeAdd(tally.allocated,stat.allocated());
                if(candidate!=null)candidate.allocated=safeAdd(candidate.allocated,stat.allocated());
                if(candidate!=null&&stat.kind!=Kind.DIRECTORY)candidate.reclaim=safeAdd(candidate.reclaim,stat.allocated());
            } else {
                Inode key=new Inode(stat);InodeUse seen=inodes.get(key);
                if(seen==null) {
                    if(inodes.size()>=50000)throw new IOException("Storage scan reached its shared-inode accounting limit; cleanup is disabled");
                    inodes.put(key,new InodeUse(stat,category,candidate==null?null:candidate.path));
                    tally.allocated=safeAdd(tally.allocated,stat.allocated());
                    if(candidate!=null)candidate.allocated=safeAdd(candidate.allocated,stat.allocated());
                } else {
                    if(!seen.stat.same(stat))throw new IOException("Hard-linked inode changed during the scan");
                    seen.seen++;if(candidate==null||!Objects.equals(seen.onlyCandidate,candidate.path))seen.onlyCandidate=null;
                }
            }
            if(stat.kind==Kind.OTHER) {
                if(candidate!=null)candidate.safe=false;
                // Sockets in protected state are inventoried without opening them.
            }
            if(stat.kind==Kind.SYMLINK) {
                String literal=fs.readLink(path);feedLink(inventory,path,literal);if(candidate!=null)feedLink(candidate.digest,path,literal);
                String target=lexicalTarget(fs,path,literal);
                if(target!=null)for(MutableCandidate possible:options.values())
                    if((target.equals(possible.path)||target.startsWith(possible.path+"/"))&&(candidate==null||!candidate.path.equals(possible.path)))possible.safe=false;
            }
            if(stat.kind==Kind.DIRECTORY) {
                if(candidate!=null)candidate.reclaim=safeAdd(candidate.reclaim,stat.allocated());
                final MutableCandidate owner=candidate;final String assigned=category;
                fs.visitDirectory(path,name->{
                    if(!safeName(name))throw new IOException("Unsafe directory member");
                    walk(join(path,name),assigned,owner,depth+1);
                });
                if(!stat.same(fs.stat(path)))throw new IOException("A directory changed during the scan");
            }
        }
        String category(String path) {
            if(path.equals("client-import")||path.startsWith("client-import/"))return "client_import";
            if(path.equals("client/state")||path.startsWith("client/state/"))return "client_state";
            if(path.equals("client/reports")||path.startsWith("client/reports/"))return "reports_kept";
            if(path.equals("m2/runtime-"+currentHash.substring(0,16))||path.startsWith("m2/runtime-"+currentHash.substring(0,16)+"/"))return "current_runtime";
            if(path.equals("m2/downloads")||path.startsWith("m2/"))return "runtime_other";
            return "other";
        }
    }
    public static CleanupResult cleanup(Fs fs,Plan plan,Set<String> selectedCategoryIds,Limits limits) {
        return cleanup(fs,plan,selectedCategoryIds,limits,NO_PROGRESS);
    }
    public static CleanupResult cleanup(Fs fs,Plan plan,Set<String> selectedCategoryIds,Limits limits,ProgressListener listener) {
        Objects.requireNonNull(plan);ProgressListener progress=listener==null?NO_PROGRESS:listener;
        Set<String> selected=new HashSet<>(selectedCategoryIds);
        List<String> errors=new ArrayList<>();int deleted=0,skipped=0;long reclaimed=0;boolean stale=false,completed=false;
        Plan fresh=scan(fs,plan.currentManifestSha256,limits,progress);
        if(!plan.cleanupAllowed||!fresh.cleanupAllowed||!plan.inventoryDigest.equals(fresh.inventoryDigest)
                ||!plan.guardDigest.equals(fresh.guardDigest)||!plan.filesRoot.same(fresh.filesRoot)) {
            errors.add("Storage changed or the scan is incomplete. Scan again before cleanup.");stale=true;
            return new CleanupResult(plan,fresh,true,false,0,0,0,errors);
        }
        for(String id:selected)if(!Arrays.asList("old_runtime","downloads","old_reports").contains(id)) {
            errors.add("The selected category is protected");return new CleanupResult(plan,fresh,false,false,0,0,0,errors);
        }
        long started=fs.nowMillis(),nextProgress=0;
        try {
            for(Candidate candidate:plan.candidates) {
                if(!selected.contains(candidate.categoryId))continue;
                File journal=fs.cleanupJournal();
                try {
                    Fingerprint digest=new Fingerprint();JournalState state=new JournalState(fs,limits,started,progress);
                    Map<Inode,List<Node>> aliases=new HashMap<>();Map<String,Stat> parents=new HashMap<>();
                    String parent=parent(candidate.path);
                    while(true) {
                        Stat value=fs.stat(parent);if(value==null||value.kind!=Kind.DIRECTORY)throw new IOException("Candidate parent is not a directory");
                        parents.put(parent,value);if(parent.isEmpty())break;parent=parent(parent);
                    }
                    try(DataOutputStream output=new DataOutputStream(new BufferedOutputStream(Files.newOutputStream(journal.toPath(),StandardOpenOption.WRITE,StandardOpenOption.TRUNCATE_EXISTING,LinkOption.NOFOLLOW_LINKS),65536))) {
                        collect(fs,candidate.path,parents.get(parent(candidate.path)),output,digest,aliases,0,state);
                    }
                    if(!candidate.root.same(fs.stat(candidate.path))||!candidate.fingerprint.equals(hex(digest.digest())))
                        throw new IOException("A cleanup candidate changed. Scan again.");
                    try(DataInputStream input=new DataInputStream(new BufferedInputStream(Files.newInputStream(journal.toPath(),LinkOption.NOFOLLOW_LINKS),65536))) {
                        for(int index=0;index<state.entries;index++) {
                            Node node=readNode(input);Stat expectedParent=readStat(input);
                            if(!node.path.equals(candidate.path)&&!node.path.startsWith(candidate.path+"/"))
                                throw new IOException("Cleanup journal escaped its reviewed candidate");
                            checkRemovalTime(fs,started,limits);
                            try {
                                checkParents(fs,candidate.path,parents);
                                Stat candidateRoot=fs.stat(candidate.path);
                                if(candidate.root.kind==Kind.DIRECTORY?!candidate.root.sameDirectory(candidateRoot):!candidate.root.same(candidateRoot))
                                    throw new IOException("Cleanup candidate root changed");
                                if(node.stat.kind!=Kind.DIRECTORY&&node.stat.links>1) {
                                    List<Node> shared=aliases.get(new Inode(node.stat));
                                    if(shared==null)throw new IOException("Cleanup hard-link identity is unavailable");
                                    Node retained=null;for(Node possible:shared)if(possible.path.equals(node.path)){retained=possible;break;}
                                    if(retained==null)throw new IOException("Cleanup hard-link member is unavailable");
                                    node.stat=retained.stat;
                                }
                                if(!expectedParent.sameDirectory(fs.stat(parent(node.path))))throw new IOException("Cleanup parent changed");
                                Stat actual=fs.stat(node.path);
                                // Our prior removals alter directory size/mtime/nlink, but never its identity.
                                if(actual==null||(node.stat.kind==Kind.DIRECTORY?!node.stat.sameDirectory(actual):!node.stat.same(actual)))
                                    throw new IOException("A cleanup member changed. Scan again.");
                                long credit=(actual.kind==Kind.DIRECTORY||actual.links==1)?actual.allocated():0;
                                if(actual.kind!=Kind.DIRECTORY&&actual.kind!=Kind.FILE&&actual.kind!=Kind.SYMLINK)throw new IOException("Unsupported cleanup member");
                                fs.remove(node.path,actual,expectedParent);deleted++;reclaimed=safeAdd(reclaimed,credit);
                                // Only bounded shared inode paths are retained; ordinary paths live in the private disk journal.
                                if(actual.links>1)for(Node remaining:aliases.getOrDefault(new Inode(actual),Collections.emptyList())) {
                                    if(!remaining.path.equals(node.path)&&fs.stat(remaining.path)!=null) {
                                        Stat updated=fs.stat(remaining.path);
                                        if(updated==null||updated.kind!=remaining.stat.kind||updated.device!=actual.device||updated.inode!=actual.inode
                                                ||updated.size!=actual.size||updated.blocks!=actual.blocks||updated.modified!=actual.modified
                                                ||updated.links!=actual.links-1)throw new IOException("Hard-linked member changed during cleanup");
                                        remaining.stat=updated;
                                    }
                                }
                                long now=fs.nowMillis();if(now>=nextProgress) {
                                    nextProgress=now+5000;progress.update("removing reviewed files",deleted,node.path,Math.max(0,now-started));
                                }
                            } catch(IOException failure){skipped++;throw failure;}
                        }
                        if(input.read()!=-1)throw new IOException("Cleanup journal contains unreviewed entries");
                    }
                } finally {if(!journal.delete()&&journal.exists())errors.add("Private cleanup journal could not be removed");}
            }
            completed=true;
        } catch(Exception failure){errors.add(message(failure));}
        try{progress.update(completed?"cleanup complete":"cleanup stopped",deleted,"",Math.max(0,fs.nowMillis()-started));}
        catch(IOException failure){errors.add(message(failure));completed=false;}
        Plan after=scan(fs,plan.currentManifestSha256,limits,progress);
        return new CleanupResult(plan,after,stale,completed,deleted,skipped,reclaimed,errors);
    }
    private static final class Node {final String path;Stat stat;Node(String path,Stat stat){this.path=path;this.stat=stat;}}
    private static final class JournalState {
        final Fs fs;final Limits limits;final long started;final ProgressListener progress;
        int entries,sharedAliases;long bytes,nextProgress;
        JournalState(Fs fs,Limits limits,long started,ProgressListener progress){this.fs=fs;this.limits=limits;this.started=started;this.progress=progress;}
        void check(String path,int depth) throws IOException {
            checkRemovalTime(fs,started,limits);
            if(entries>=limits.maximumEntries||depth>limits.maximumDepth)throw new IOException("Cleanup reached its entry or depth limit");
            if((entries&1023)==0) {
                ensureMemory("Cleanup reached its memory budget");
                long now=fs.nowMillis();if(now>=nextProgress) {
                    nextProgress=now+5000;progress.update("validating cleanup journal",entries,path,Math.max(0,now-started));
                }
            }
        }
    }
    private static void collect(Fs fs,String path,Stat parentStat,DataOutputStream output,Fingerprint digest,
            Map<Inode,List<Node>> aliases,int depth,JournalState state) throws IOException {
        state.check(path,depth);Stat stat=fs.stat(path);
        if(stat==null||stat.kind==Kind.OTHER)throw new IOException("Cleanup candidate is unavailable or has an unsupported member");
        stat.allocated();state.entries++;feed(digest,path,stat);
        if(stat.kind==Kind.SYMLINK)feedLink(digest,path,fs.readLink(path));
        if(stat.kind!=Kind.DIRECTORY&&stat.links>1) {
            if(++state.sharedAliases>50000)throw new IOException("Cleanup reached its shared-inode path accounting limit");
            aliases.computeIfAbsent(new Inode(stat),key->new ArrayList<>()).add(new Node(path,stat));
        }
        if(stat.kind==Kind.DIRECTORY) {
            fs.visitDirectory(path,name->{
                if(!safeName(name))throw new IOException("Unsafe cleanup member");
                collect(fs,join(path,name),stat,output,digest,aliases,depth+1,state);
            });
            if(!stat.same(fs.stat(path)))throw new IOException("Candidate changed during validation");
        }
        // Postorder records remove files before their directories. Disk use is bounded even on full devices.
        state.bytes=safeAdd(state.bytes,4L+path.getBytes(StandardCharsets.UTF_8).length+130);
        if(state.bytes>128L*1024*1024)throw new IOException("Cleanup journal reached its disk budget; this candidate was not removed");
        byte[] name=path.getBytes(StandardCharsets.UTF_8);output.writeInt(name.length);output.write(name);writeStat(output,stat);writeStat(output,parentStat);
    }
    private static void writeStat(DataOutputStream out,Stat stat) throws IOException {
        out.writeByte(stat.kind.ordinal());out.writeLong(stat.device);out.writeLong(stat.inode);out.writeLong(stat.links);
        out.writeLong(stat.size);out.writeLong(stat.blocks);out.writeLong(stat.modified);out.writeLong(stat.changed);
    }
    private static Stat readStat(DataInputStream in) throws IOException {
        int kind=in.readUnsignedByte();if(kind>=Kind.values().length)throw new IOException("Cleanup journal kind is invalid");
        return new Stat(Kind.values()[kind],in.readLong(),in.readLong(),in.readLong(),in.readLong(),in.readLong(),in.readLong(),in.readLong());
    }
    private static Node readNode(DataInputStream in) throws IOException {
        int length=in.readInt();if(length<1||length>65536)throw new IOException("Cleanup journal path is invalid");
        byte[] bytes=new byte[length];in.readFully(bytes);return new Node(new String(bytes,StandardCharsets.UTF_8),readStat(in));
    }
    private static void checkRemovalTime(Fs fs,long started,Limits limits) throws IOException {
        if(Thread.currentThread().isInterrupted()||fs.nowMillis()-started>limits.maximumMillis)throw new IOException("Cleanup cancelled or reached its time limit");
    }
    private static void ensureMemory(String reason) throws IOException {
        Runtime vm=Runtime.getRuntime();
        if(vm.maxMemory()<32L*1024*1024)throw new IOException(reason);
        // Iterator/journal storage is bounded. Count live allocations after a collection before
        // treating temporary per-entry path/stat garbage as a memory limit.
        if(vm.maxMemory()-(vm.totalMemory()-vm.freeMemory())<8L*1024*1024) {
            vm.gc();if(vm.maxMemory()-(vm.totalMemory()-vm.freeMemory())<8L*1024*1024)throw new IOException(reason);
        }
    }
    private static void checkParents(Fs fs,String path,Map<String,Stat> parents) throws IOException {
        String parent=parent(path);
        while(true) {
            Stat expected=parents.get(parent);if(expected==null||!expected.sameDirectory(fs.stat(parent)))throw new IOException("Cleanup parent changed");
            if(parent.isEmpty())break;parent=parent(parent);
        }
    }
    private static boolean singleRegular(Stat stat){return stat!=null&&stat.kind==Kind.FILE&&stat.links==1;}
    private static String lexicalTarget(Fs fs,String source,String target) throws IOException {
        if(target==null||target.length()>4096||target.indexOf('\0')>=0)throw new IOException("Invalid private symlink target");
        Path root=Paths.get(fs.rootPath()).toAbsolutePath().normalize();
        Path destination=target.startsWith("/")?Paths.get(target).normalize():root.resolve(parent(source)).resolve(target).normalize();
        for(String alias:fs.rootAliases()) {
            Path prefix=Paths.get(alias).toAbsolutePath().normalize();
            if(destination.startsWith(prefix))return prefix.relativize(destination).toString().replace('\\','/');
        }
        return null;
    }
    private static boolean containedRegular(Fs fs,String path,String scope) throws IOException {
        // Only verification resolves links. Inventory and deletion never follow them.
        String pending=path;
        for(int hop=0;hop<32;hop++) {
            String[] parts=pending.split("/");String prefix="";boolean restarted=false;
            for(int i=0;i<parts.length;i++) {
                prefix=join(prefix,parts[i]);Stat stat=fs.stat(prefix);if(stat==null)return false;
                if(stat.kind==Kind.SYMLINK) {
                    String target=lexicalTarget(fs,prefix,fs.readLink(prefix));
                    if(target==null||!(target.equals(scope)||target.startsWith(scope+"/")))return false;
                    for(int j=i+1;j<parts.length;j++)target=join(target,parts[j]);pending=target;restarted=true;break;
                }
                if(i==parts.length-1)return stat.kind==Kind.FILE;
                if(stat.kind!=Kind.DIRECTORY)return false;
            }
            if(!restarted)return false;
        }
        return false;
    }
    private static boolean number(Object value,long expected){return value instanceof Number&&((Number)value).longValue()==expected&&((Number)value).doubleValue()==expected;}
    private static String join(String path,String name){return path.isEmpty()?name:path+"/"+name;}
    private static String parent(String path){int index=path.lastIndexOf('/');return index<0?"":path.substring(0,index);}
    private static boolean safeName(String name){return name!=null&&!name.isEmpty()&&!name.equals(".")&&!name.equals("..")&&name.indexOf('/')<0&&name.indexOf('\0')<0;}
    private static long safeAdd(long first,long second){return Math.addExact(first,second);}
    private static MessageDigest digest(){try{return MessageDigest.getInstance("SHA-256");}catch(Exception e){throw new IllegalStateException(e);}}
    private static String hash(byte[] bytes){return hex(digest().digest(bytes));}
    private static String hex(byte[] bytes){StringBuilder out=new StringBuilder();for(byte value:bytes)out.append(String.format(Locale.ROOT,"%02x",value&255));return out.toString();}
    /** An unordered SHA-256 multiset fingerprint permits bounded directory iteration.
     * Each stat/link record includes its complete unique path. Addition modulo 2^256
     * plus a record count is order independent without retaining paths or sorting them.
     */
    private static final class Fingerprint {
        private final MessageDigest item=StorageAudit.digest();private final byte[] sum=new byte[32];private long records;
        void add(byte[] value) {
            byte[] hashed=item.digest(value);int carry=0;
            for(int i=sum.length-1;i>=0;i--){int next=(sum[i]&255)+(hashed[i]&255)+carry;sum[i]=(byte)next;carry=next>>>8;}
            records++;
        }
        byte[] digest() {
            item.reset();item.update(sum);
            for(int i=7;i>=0;i--)item.update((byte)(records>>>(i*8)));
            return item.digest();
        }
    }
    private static void feed(Fingerprint digest,String path,Stat stat) {
        String value=path+"\0"+(stat==null?"missing":stat.kind+":"+stat.device+":"+stat.inode+":"+stat.links+":"+stat.size+":"+stat.blocks+":"+stat.modified+":"+stat.changed)+"\n";
        digest.add(value.getBytes(StandardCharsets.UTF_8));
    }
    private static void feed(MessageDigest digest,String path,Stat stat) {
        String value=path+"\0"+(stat==null?"missing":stat.kind+":"+stat.device+":"+stat.inode+":"+stat.links+":"+stat.size+":"+stat.blocks+":"+stat.modified+":"+stat.changed)+"\n";
        digest.update(value.getBytes(StandardCharsets.UTF_8));
    }
    private static void feedLink(MessageDigest digest,String target) throws IOException {
        if(target==null||target.length()>4096||target.indexOf('\0')>=0)throw new IOException("Invalid private symlink target");
        digest.update(("link:"+target+"\0").getBytes(StandardCharsets.UTF_8));
    }
    private static void feedLink(Fingerprint digest,String path,String target) throws IOException {
        if(target==null||target.length()>4096||target.indexOf('\0')>=0)throw new IOException("Invalid private symlink target");
        digest.add(("link:"+path+"\0"+target+"\0").getBytes(StandardCharsets.UTF_8));
    }
    private static String message(Exception error){String value=error.getMessage();return value==null?error.getClass().getSimpleName():value.substring(0,Math.min(240,value.length()));}
    private static Map<String,Object> planMap(Plan plan) {
        Map<String,Object> value=new LinkedHashMap<>();value.put("format",1);value.put("scope","app_private_storage_inventory");
        value.put("snapshot_id",plan.snapshotId);value.put("scanned_utc_ms",plan.scannedUtcMs);value.put("complete",plan.complete);
        value.put("current_runtime_verified",plan.currentRuntimeVerified);value.put("cleanup_allowed",plan.cleanupAllowed);
        value.put("entry_count",plan.entryCount);value.put("apparent_bytes",plan.apparentBytes);value.put("allocated_bytes",plan.allocatedBytes);
        value.put("reclaimable_bytes",plan.reclaimableBytes);value.put("allocated_bytes_basis","st_blocks * 512, unique device/inode; no symlink traversal");
        value.put("protected","All client/state and client-import, the current runtime, latest report and newest three report directories");
        value.put("errors",plan.errors);List<Object> categories=new ArrayList<>();
        for(Category category:plan.categories) {
            Map<String,Object> summary=new LinkedHashMap<>();summary.put("id",category.id);summary.put("label",category.label);
            summary.put("removable",category.removable&&plan.cleanupAllowed);summary.put("apparent_bytes",category.apparentBytes);
            summary.put("allocated_bytes",category.allocatedBytes);summary.put("reclaimable_bytes",plan.cleanupAllowed?category.reclaimableBytes:0);
            summary.put("candidate_count",category.candidateCount);categories.add(summary);
        }
        value.put("categories",categories);List<Object> candidates=new ArrayList<>();
        for(int i=0;i<Math.min(256,plan.candidates.size());i++) {
            Candidate candidate=plan.candidates.get(i);Map<String,Object> summary=new LinkedHashMap<>();
            summary.put("path",candidate.path);summary.put("category",candidate.categoryId);summary.put("apparent_bytes",candidate.apparentBytes);
            summary.put("allocated_bytes",candidate.allocatedBytes);summary.put("reclaimable_bytes",plan.cleanupAllowed?candidate.reclaimableBytes:0);
            candidates.add(summary);
        }
        value.put("candidates",candidates);value.put("candidate_count",plan.candidates.size());value.put("candidate_details_truncated",plan.candidates.size()>256);
        return value;
    }
    private static String encode(Object value) {
        if(value==null)return "null";if(value instanceof Boolean||value instanceof Number)return value.toString();
        if(value instanceof Map){StringBuilder out=new StringBuilder("{");boolean comma=false;for(Map.Entry<?,?> entry:((Map<?,?>)value).entrySet()){if(comma)out.append(',');comma=true;out.append(encode(entry.getKey().toString())).append(':').append(encode(entry.getValue()));}return out.append('}').toString();}
        if(value instanceof Iterable){StringBuilder out=new StringBuilder("[");boolean comma=false;for(Object member:(Iterable<?>)value){if(comma)out.append(',');comma=true;out.append(encode(member));}return out.append(']').toString();}
        StringBuilder out=new StringBuilder("\"");for(char c:value.toString().toCharArray()){if(c=='"'||c=='\\')out.append('\\').append(c);else if(c<32)out.append(String.format(Locale.ROOT,"\\u%04x",(int)c));else out.append(c);}return out.append('"').toString();
    }
}
