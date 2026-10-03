package io.github.russianranger.cohclientinteractive;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.nio.file.Paths;
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
        final String path,category;final Stat root;final MessageDigest digest=digest();
        String fingerprint;long apparent,allocated,reclaim;boolean safe=true;
        MutableCandidate(String path,String category,Stat root){this.path=path;this.category=category;this.root=root;}
    }
    public static Plan scan(Fs fs,String currentManifestSha256,Limits limits) {
        Scanner scanner=new Scanner(fs,currentManifestSha256,limits);scanner.run();return new Plan(scanner);
    }
    private static final class Scanner {
        final Fs fs;final String currentHash;final Limits limits;final long started;
        final MessageDigest inventory=digest();final Map<String,Tally> tallies=new LinkedHashMap<>();
        final Map<String,MutableCandidate> options=new LinkedHashMap<>();final Map<Inode,InodeUse> inodes=new HashMap<>();
        final List<String> errors=new ArrayList<>();final Set<String> keptReports=new HashSet<>();
        Stat root;boolean complete=true,currentReady=false;int entries;String guards="";
        Scanner(Fs fs,String hash,Limits limits) {
            this.fs=fs;currentHash=hash;this.limits=limits;started=fs.nowMillis();
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
        }
        void check(int depth) throws IOException {
            if(Thread.currentThread().isInterrupted())throw new IOException("Storage scan cancelled");
            if(entries>=limits.maximumEntries||depth>limits.maximumDepth||fs.nowMillis()-started>limits.maximumMillis)
                throw new IOException("Storage scan reached its entry, depth or time limit; cleanup is disabled");
            if((entries&1023)==0) {
                Runtime vm=Runtime.getRuntime();long available=vm.maxMemory()-(vm.totalMemory()-vm.freeMemory());
                if(available<24L*1024*1024)throw new IOException("Storage scan reached its memory budget; cleanup is disabled");
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
            stat.allocated();entries++;feed(inventory,path,stat);
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
                String literal=fs.readLink(path);feedLink(inventory,literal);if(candidate!=null)feedLink(candidate.digest,literal);
                String target=lexicalTarget(fs,path,literal);
                if(target!=null)for(MutableCandidate possible:options.values())
                    if((target.equals(possible.path)||target.startsWith(possible.path+"/"))&&(candidate==null||!candidate.path.equals(possible.path)))possible.safe=false;
            }
            if(stat.kind==Kind.DIRECTORY) {
                if(candidate!=null)candidate.reclaim=safeAdd(candidate.reclaim,stat.allocated());
                List<String> names=fs.list(path);Collections.sort(names);
                for(String name:names) {
                    if(!safeName(name))throw new IOException("Unsafe directory member");
                    walk(join(path,name),category,candidate,depth+1);
                }
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
        Objects.requireNonNull(plan);Set<String> selected=new HashSet<>(selectedCategoryIds);
        List<String> errors=new ArrayList<>();int deleted=0,skipped=0;long reclaimed=0;boolean stale=false,completed=false;
        Plan fresh=scan(fs,plan.currentManifestSha256,limits);
        if(!plan.cleanupAllowed||!fresh.cleanupAllowed||!plan.inventoryDigest.equals(fresh.inventoryDigest)
                ||!plan.guardDigest.equals(fresh.guardDigest)||!plan.filesRoot.same(fresh.filesRoot)) {
            errors.add("Storage changed or the scan is incomplete. Scan again before cleanup.");stale=true;
            return new CleanupResult(plan,fresh,true,false,0,0,0,errors);
        }
        for(String id:selected)if(!Arrays.asList("old_runtime","downloads","old_reports").contains(id)) {
            errors.add("The selected category is protected");return new CleanupResult(plan,fresh,false,false,0,0,0,errors);
        }
        long started=fs.nowMillis();
        try {
            for(Candidate candidate:plan.candidates) {
                if(!selected.contains(candidate.categoryId))continue;
                List<Node> nodes=new ArrayList<>();MessageDigest digest=digest();
                collect(fs,candidate.path,nodes,digest,0,limits,started);
                if(!candidate.root.same(fs.stat(candidate.path))||!candidate.fingerprint.equals(hex(digest.digest())))
                    throw new IOException("A cleanup candidate changed. Scan again.");
                Map<String,Stat> parents=new HashMap<>();
                Map<Inode,List<Node>> aliases=new HashMap<>();
                for(Node node:nodes) {
                    if(node.stat.kind==Kind.DIRECTORY)parents.put(node.path,node.stat);
                    else if(node.stat.links>1)aliases.computeIfAbsent(new Inode(node.stat),key->new ArrayList<>()).add(node);
                }
                String parent=parent(candidate.path);
                while(true){Stat value=fs.stat(parent);if(value==null||value.kind!=Kind.DIRECTORY)throw new IOException("Candidate parent is not a directory");parents.put(parent,value);if(parent.isEmpty())break;parent=parent(parent);}
                for(int i=nodes.size()-1;i>=0;i--) {
                    Node node=nodes.get(i);checkRemovalTime(fs,started,limits);
                    try {
                        checkParents(fs,node.path,parents);
                        Stat actual=fs.stat(node.path);
                        // Own deletions change directory size/mtime/nlink, so directory identity alone is retained.
                        if(actual==null||(node.stat.kind==Kind.DIRECTORY?!node.stat.sameDirectory(actual):!node.stat.same(actual)))
                            throw new IOException("A cleanup member changed. Scan again.");
                        long credit=(actual.kind==Kind.DIRECTORY||actual.links==1)?actual.allocated():0;
                        if(actual.kind!=Kind.DIRECTORY&&actual.kind!=Kind.FILE&&actual.kind!=Kind.SYMLINK)throw new IOException("Unsupported cleanup member");
                        fs.remove(node.path,actual,parents.get(parent(node.path)));
                        deleted++;reclaimed=safeAdd(reclaimed,credit);
                        // Removing one hard-link updates ctime/nlink of remaining links in this candidate.
                        if(actual.links>1)for(Node remaining:aliases.getOrDefault(new Inode(actual),Collections.emptyList())) {
                            if(!remaining.path.equals(node.path)&&fs.stat(remaining.path)!=null) {
                                Stat updated=fs.stat(remaining.path);
                                if(updated==null||updated.kind!=remaining.stat.kind||updated.device!=actual.device||updated.inode!=actual.inode
                                        ||updated.size!=actual.size||updated.blocks!=actual.blocks||updated.modified!=actual.modified
                                        ||updated.links!=actual.links-1)throw new IOException("Hard-linked member changed during cleanup");
                                remaining.stat=updated;
                            }
                        }
                    } catch(IOException failure){skipped++;throw failure;}
                }
            }
            completed=true;
        } catch(Exception failure){errors.add(message(failure));}
        Plan after=scan(fs,plan.currentManifestSha256,limits);
        return new CleanupResult(plan,after,stale,completed,deleted,skipped,reclaimed,errors);
    }
    private static final class Node {final String path;Stat stat;Node(String path,Stat stat){this.path=path;this.stat=stat;}}
    private static void collect(Fs fs,String path,List<Node> nodes,MessageDigest digest,int depth,Limits limits,long started) throws IOException {
        checkRemovalTime(fs,started,limits);
        if((nodes.size()&255)==0) {
            Runtime vm=Runtime.getRuntime();if(vm.maxMemory()-(vm.totalMemory()-vm.freeMemory())<24L*1024*1024)
                throw new IOException("Cleanup reached its memory budget");
        }
        if(nodes.size()>=limits.maximumEntries||depth>limits.maximumDepth)throw new IOException("Cleanup reached its entry or depth limit");
        Stat stat=fs.stat(path);if(stat==null||stat.kind==Kind.OTHER)throw new IOException("Cleanup candidate is unavailable or has an unsupported member");
        stat.allocated();nodes.add(new Node(path,stat));feed(digest,path,stat);
        if(stat.kind==Kind.SYMLINK)feedLink(digest,fs.readLink(path));
        if(stat.kind==Kind.DIRECTORY) {
            List<String> names=fs.list(path);Collections.sort(names);
            for(String name:names){if(!safeName(name))throw new IOException("Unsafe cleanup member");collect(fs,join(path,name),nodes,digest,depth+1,limits,started);}
            if(!stat.same(fs.stat(path)))throw new IOException("Candidate changed during validation");
        }
    }
    private static void checkRemovalTime(Fs fs,long started,Limits limits) throws IOException {
        if(Thread.currentThread().isInterrupted()||fs.nowMillis()-started>limits.maximumMillis)throw new IOException("Cleanup cancelled or reached its time limit");
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
    private static void feed(MessageDigest digest,String path,Stat stat) {
        String value=path+"\0"+(stat==null?"missing":stat.kind+":"+stat.device+":"+stat.inode+":"+stat.links+":"+stat.size+":"+stat.blocks+":"+stat.modified+":"+stat.changed)+"\n";
        digest.update(value.getBytes(StandardCharsets.UTF_8));
    }
    private static void feedLink(MessageDigest digest,String target) throws IOException {
        if(target==null||target.length()>4096||target.indexOf('\0')>=0)throw new IOException("Invalid private symlink target");
        digest.update(("link:"+target+"\0").getBytes(StandardCharsets.UTF_8));
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
