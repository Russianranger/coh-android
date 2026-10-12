package io.github.russianranger.cohclientinteractive;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.ByteArrayOutputStream;
import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.channels.Channels;
import java.nio.channels.FileChannel;
import java.nio.channels.SeekableByteChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.LinkedHashMap;
import java.util.Set;
import java.util.HashSet;
import java.util.UUID;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;
import java.util.zip.ZipInputStream;
import java.util.zip.ZipFile;

/** Bounded private diagnostic preservation. Recovery records never confer a pass. */
public final class ClientReports {
    public static final long MAX_REPORT_BYTES = 512L * 1024 * 1024;
    public static final long MAX_EXPORT_MILLIS = 5L * 60 * 1000;
    /** Android supplies lstat identity because not every provider exposes unix attributes. */
    public interface IdentityReader { FileIdentity read(File file) throws IOException; }
    public static final class FileIdentity {
        public final long linkCount;
        public final String key;
        public FileIdentity(long linkCount, String key) { this.linkCount = linkCount; this.key = key; }
    }
    private static volatile IdentityReader identityReader;
    public static synchronized void setIdentityReader(IdentityReader reader) {
        if (reader == null) throw new IllegalArgumentException("Missing file identity reader");
        if (identityReader != null && identityReader != reader) throw new IllegalStateException("File identity reader already initialized");
        identityReader = reader;
    }
    interface SourceOpener { SeekableByteChannel open(Path file) throws IOException; }
    private static volatile SourceOpener sourceOpener;
    static synchronized void setSourceOpener(SourceOpener opener) {sourceOpener=opener;}
    private static SeekableByteChannel openSource(Path file) throws IOException {
        SourceOpener selected=sourceOpener;
        return selected==null?Files.newByteChannel(file,StandardOpenOption.READ,LinkOption.NOFOLLOW_LINKS):selected.open(file);
    }
    private static final long MAX_GUEST_BYTES = 260L * 1024 * 1024;
    private static final long MAX_JSON_BYTES = 2L * 1024 * 1024;
    // A normal wrapper embeds the bounded guest JSON plus Android observations.
    private static final long MAX_ANDROID_JSON_BYTES = 4L * 1024 * 1024;
    private static final int MAX_CHECKPOINT_BYTES = 256 * 1024;
    private static final int MAX_PNG_BYTES = 4 * 1024 * 1024;
    private static final long MAX_CAPTURE_BYTES = 64L * 1024 * 1024;
    private static final int MAX_CAPTURES = 128, MAX_DIRECTORY_ENTRIES = 2048, MAX_OMISSIONS = 128;
    private static final String[] GUEST_FILES = {"latest-report.json", "report.zip", "character-logout.json",
            "interaction-finish.json", "character-relocation.json", "character-task-contact.json",
            "character-task-completion.json", "character-zoning-request.json", "character-zoning-delivery.json"};
    private static final String[] CAPTURE_DIRS = {"android-surface", "android-login", "android-connected",
            "android-relocated", "android-character", "android-interaction", "android-contact", "android-task", "android-zoning"};
    private static final byte[] PNG = {(byte)137,80,78,71,13,10,26,10};
    private ClientReports() {}

    /** Newest completed archives, including explicitly interrupted recovery archives. No pointer is needed. */
    public static synchronized List<File> reports(File filesRoot, int max) throws IOException {
        if (max < 0 || max > 50) throw new IOException("Invalid report inventory limit");
        List<Path> found = new ArrayList<>();
        final Map<Path,String> sourceRuns=new LinkedHashMap<>();
        Path root = reportRoot(filesRoot, false);
        if (root == null || max == 0) return new ArrayList<>();
        for (Path run : children(root)) {
            if (!runName(run.getFileName().toString())) continue;
            try {
                if (!directoryEntry(run)) continue;
                for (Path file : children(run)) {
                    if (!archiveName(file.getFileName().toString())) continue;
                    try { completedArchive(file); found.add(file); sourceRuns.put(file,sourceRunId(file)); }
                    catch (IOException unsafe) { /* An unsafe archive is never offered for export. */ }
                }
            } catch (IOException unavailable) { /* Keep a damaged historical run from hiding safely validated current carriers. */ }
        }
        Collections.sort(found, new Comparator<Path>() {
            @Override public int compare(Path a, Path b) {
                // The per-run timestamp is stable even after a recovery archive is assembled later.
                int value = sourceRuns.get(b).compareTo(sourceRuns.get(a));
                return value != 0 ? value : b.getFileName().toString().compareTo(a.getFileName().toString());
            }
        });
        List<File> result = new ArrayList<>();
        for (Path file : found) { if (result.size() == max) break; result.add(file.toFile()); }
        return result;
    }

    /** Fail closed: callers may retire guest outputs only after this returns successfully. */
    public static synchronized File preservePrevious(File filesRoot) throws IOException {
        Path files = directory(filesRoot.toPath());
        Path client = files.resolve("client");
        if (!Files.exists(client, LinkOption.NOFOLLOW_LINKS)) return null;
        directory(client);
        Path state = client.resolve("state");
        if (!Files.exists(state, LinkOption.NOFOLLOW_LINKS)) return null;
        directory(state);
        List<Path> sources = guestSources(state);
        if (sources.isEmpty()) return null;
        Path root = reportRoot(filesRoot, true);
        String fingerprint=guestFingerprint(sources);
        Path completedMarker=root.resolve("completed-guest-preservation.txt");
        if (Files.exists(completedMarker,LinkOption.NOFOLLOW_LINKS)) {
            regular(completedMarker,4096);
            String[] receipt=readText(completedMarker,4096).split("\n");
            String observedSession=guestSession(sources,false);
            if (receipt.length==5 && "1".equals(receipt[0]) && receipt[1].equals(observedSession)
                    && fingerprint.equals(receipt[2]) && receipt[4].matches("[0-9a-f]{64}")) {
                String[] relative=receipt[3].split("/",-1);
                if (relative.length==2 && runName(relative[0]) && normalArchiveName(relative[1],relative[0])) {
                    Path completed=root.resolve(relative[0]).resolve(relative[1]);
                    if (Files.exists(completed,LinkOption.NOFOLLOW_LINKS)) {
                        regular(completed,MAX_REPORT_BYTES); // Linked/foreign carriers are refused, never followed.
                        try {
                            if (receipt[4].equals(fileDigest(completed,MAX_REPORT_BYTES))
                                    && completedCarrier(completed,sources,observedSession)
                                    && fingerprint.equals(guestFingerprint(sources))
                                    && receipt[4].equals(fileDigest(completed,MAX_REPORT_BYTES))) return completed.toFile();
                        } catch (IOException invalidCarrier) {
                            // A deleted, changed or truncated safe carrier requires a fresh recovery.
                            if (Files.exists(completed,LinkOption.NOFOLLOW_LINKS)) regular(completed,MAX_REPORT_BYTES);
                        }
                    }
                }
            }
        }
        Path marker=root.resolve("previous-guest-preservation.txt");
        if(Files.exists(marker,LinkOption.NOFOLLOW_LINKS)) {
            regular(marker,4096);java.io.ByteArrayOutputStream saved=new java.io.ByteArrayOutputStream();copy(marker,saved,4096);
            String[] receipt=new String(saved.toByteArray(),StandardCharsets.UTF_8).split("\n");
            if(receipt.length==4 && "1".equals(receipt[0]) && fingerprint.equals(receipt[1])) {
                String[] relative=receipt[2].split("/");
                if(relative.length==2&&runName(relative[0])&&archiveName(relative[1])) {
                    Path previous=root.resolve(relative[0]).resolve(relative[1]);
                    if(Files.exists(previous,LinkOption.NOFOLLOW_LINKS)&&receipt[3].equals(fileDigest(previous,MAX_REPORT_BYTES)))return previous.toFile();
                }
            }
        }
        long sourceUtc=0;for(Path source:sources)sourceUtc=Math.max(sourceUtc,Files.getLastModifiedTime(source,LinkOption.NOFOLLOW_LINKS).toMillis());
        sourceUtc=Math.max(1000000000L,Math.min(System.currentTimeMillis(),sourceUtc));
        Path run = root.resolve(sourceUtc + "-" + UUID.randomUUID().toString().replace("-", "").substring(0,12));
        Files.createDirectory(run);
        Path target = run.resolve("coh-interrupted-guest-" + run.getFileName() + ".zip");
        archive(target, sources, state, null, "previous_guest_outputs", false);
        if(!fingerprint.equals(guestFingerprint(sources)))throw new IOException("Previous guest evidence changed during preservation");
        String receipt="1\n"+fingerprint+"\n"+root.relativize(target).toString().replace(File.separatorChar,'/')+"\n"+fileDigest(target,MAX_REPORT_BYTES)+"\n";
        atomicBytes(marker,receipt.getBytes(StandardCharsets.UTF_8));
        return target.toFile();
    }

    /** Include each bounded fixed guest request/report in the completed Android carrier.
     * The large guest ZIP already occupies guest-report.zip and is not duplicated. */
    public static synchronized void writeGuestOutputs(File filesRoot, ZipOutputStream zip) throws IOException {
        Path state=directory(directory(filesRoot.toPath()).resolve("client/state"));
        List<Path> sources=guestSources(state);
        String before=guestFingerprint(sources);
        for (Path source:sources) {
            if ("report.zip".equals(source.getFileName().toString())) continue;
            zip.putNextEntry(new ZipEntry("guest-output/"+source.getFileName()));
            copy(source,zip,MAX_JSON_BYTES);zip.closeEntry();
        }
        if (!before.equals(guestFingerprint(sources))) throw new IOException("Guest evidence changed during report assembly");
    }

    /** Commit a new complete normal archive while retaining any pre-existing evidence. */
    public static synchronized void commitNormalArchive(File filesRoot,File partial,File archive) throws IOException {
        Path root=reportRoot(filesRoot,false);
        if(root==null || partial==null || archive==null)throw new IOException("Missing normal report paths");
        Path target=archive.toPath().toAbsolutePath().normalize(),part=partial.toPath().toAbsolutePath().normalize();
        if(target.getParent()==null || !root.equals(target.getParent().getParent())
                || !runName(target.getParent().getFileName().toString())
                || !normalArchiveName(target.getFileName().toString(),target.getParent().getFileName().toString())
                || !target.getParent().equals(part.getParent()) || !part.getFileName().toString().equals("support.zip.part"))
            throw new IOException("Invalid normal report publication namespace");
        BasicFileAttributes before=regular(part,MAX_REPORT_BYTES);FileIdentity owned=identity(part);
        try(ZipFile complete=new ZipFile(part.toFile())){if(complete.size()==0)throw new IOException("Empty normal report ZIP");}
        same(before,regular(part,MAX_REPORT_BYTES));
        if(!owned.key.equals(identity(part).key))throw new IOException("Normal report part was replaced");
        try(FileChannel committed=FileChannel.open(part,StandardOpenOption.READ,LinkOption.NOFOLLOW_LINKS)){committed.force(true);}
        if(Files.exists(target,LinkOption.NOFOLLOW_LINKS))throw new IOException("A retained normal report already exists");
        Files.move(part,target,StandardCopyOption.ATOMIC_MOVE);
        regular(target,MAX_REPORT_BYTES);
        if(!owned.key.equals(identity(target).key))throw new IOException("Normal report publication identity differs");
    }

    /** Record reuse only after the caller atomically committed its complete normal ZIP.
     * This receipt certifies preservation of bytes, never a successful Android/game test. */
    public static synchronized void completedGuest(File filesRoot, File archive, String session) throws IOException {
        if (session==null || !session.matches("[0-9a-f]{32}")) throw new IOException("Invalid completed guest session");
        Path root=reportRoot(filesRoot,false);
        if (root==null || archive==null) throw new IOException("Missing completed report");
        Path target=archive.toPath().toAbsolutePath().normalize();
        if (target.getParent()==null || !root.equals(target.getParent().getParent())
                || !runName(target.getParent().getFileName().toString())
                || !normalArchiveName(target.getFileName().toString(),target.getParent().getFileName().toString()))
            throw new IOException("Completed report is outside its owned normal archive namespace");
        regular(target,MAX_REPORT_BYTES);
        List<Path> sources=guestSources(directory(root.getParent().resolve("state")));
        String fingerprint=guestFingerprint(sources);
        String before=fileDigest(target,MAX_REPORT_BYTES);
        if (!session.equals(guestSession(sources,true)) || !completedCarrier(target,sources,session))
            throw new IOException("Completed archive does not preserve the matching guest session");
        String digest=fileDigest(target,MAX_REPORT_BYTES);
        if (!before.equals(digest) || !fingerprint.equals(guestFingerprint(sources))) throw new IOException("Evidence changed before completed receipt");
        try(FileChannel committed=FileChannel.open(target,StandardOpenOption.READ,LinkOption.NOFOLLOW_LINKS)){committed.force(true);}
        String receipt="1\n"+session+"\n"+fingerprint+"\n"+root.relativize(target).toString().replace(File.separatorChar,'/')+"\n"+digest+"\n";
        atomicBytes(root.resolve("completed-guest-preservation.txt"),receipt.getBytes(StandardCharsets.UTF_8));
    }

    private static List<Path> guestSources(Path state) throws IOException {
        directory(state);List<Path> sources=new ArrayList<>();
        for (String name:GUEST_FILES) {
            Path file=state.resolve(name);
            if (!Files.exists(file,LinkOption.NOFOLLOW_LINKS)) continue;
            regular(file,name.equals("report.zip")?MAX_GUEST_BYTES:MAX_JSON_BYTES);sources.add(file);
        }
        return sources;
    }
    private static String readText(Path source,long limit) throws IOException {
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();copy(source,bytes,limit);
        return decodeText(bytes.toByteArray());
    }
    private static String decodeText(byte[] bytes) throws IOException {
        return StandardCharsets.UTF_8.newDecoder().onMalformedInput(java.nio.charset.CodingErrorAction.REPORT)
                .onUnmappableCharacter(java.nio.charset.CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
    }
    private static String guestSession(List<Path> sources,boolean required) throws IOException {
        for (Path source:sources) if (source.getFileName().toString().equals("latest-report.json")) {
            try { return new SessionJson(readText(source,MAX_JSON_BYTES)).session(); }
            catch(IOException malformed) { if(required)throw malformed;return null; }
        }
        if(required)throw new IOException("Missing guest session report");return null;
    }
    private static boolean normalArchiveName(String name,String run) {
        return name.equals("coh-character-creation-"+run+".zip") || name.equals("coh-character-reopen-"+run+".zip");
    }
    private static boolean completedCarrier(Path carrier,List<Path> sources,String session) throws IOException {
        BasicFileAttributes before=regular(carrier,MAX_REPORT_BYTES);FileIdentity owned=identity(carrier);
        Map<String,String> expected=new LinkedHashMap<>();
        for (Path source:sources) {
            String name=source.getFileName().toString();
            expected.put(name.equals("report.zip")?"guest-report.zip":"guest-output/"+name,
                    fileDigest(source,name.equals("report.zip")?MAX_GUEST_BYTES:MAX_JSON_BYTES));
        }
        if (!expected.containsKey("guest-report.zip") || !expected.containsKey("guest-output/latest-report.json")) return false;
        Set<String> seen=new HashSet<>();boolean android=false;long total=0;
        long deadline=System.nanoTime()+MAX_EXPORT_MILLIS*1000000L;
        // ZipFile requires the complete central directory; streaming alone also accepts a missing ZIP tail.
        try (ZipFile central=new ZipFile(carrier.toFile());
             InputStream input=Files.newInputStream(carrier,StandardOpenOption.READ,LinkOption.NOFOLLOW_LINKS);
             ZipInputStream zip=new ZipInputStream(input)) {
            for (ZipEntry entry;(entry=zip.getNextEntry())!=null;) {
                String name=entry.getName();
                if (entry.isDirectory() || name.startsWith("/") || name.contains("\\")
                        || name.contains("\u0000") || !seen.add(name)) throw new IOException("Unsafe or colliding completed report entry");
                for(String component:name.split("/",-1)) if(component.isEmpty() || component.equals(".") || component.equals(".."))
                    throw new IOException("Unsafe completed report entry path");
                if (central.getEntry(name)==null) throw new IOException("Completed report directory differs");
                if(name.startsWith("guest-output/") && !expected.containsKey(name)) throw new IOException("Foreign guest output in completed report");
                java.security.MessageDigest digest;
                try{digest=java.security.MessageDigest.getInstance("SHA-256");}
                catch(java.security.NoSuchAlgorithmException impossible){throw new IOException("SHA-256 unavailable",impossible);}
                ByteArrayOutputStream wrapper="android-client-report.json".equals(name)?new ByteArrayOutputStream():null;
                long count=0;byte[] buffer=new byte[65536];
                long maximum="guest-report.zip".equals(name)?MAX_GUEST_BYTES:wrapper!=null?MAX_ANDROID_JSON_BYTES:name.startsWith("guest-output/")?MAX_JSON_BYTES:MAX_REPORT_BYTES;
                for(int length;(length=zip.read(buffer))!=-1;) {
                    count+=length;total+=length;
                    if(count>maximum || total>MAX_REPORT_BYTES || Thread.currentThread().isInterrupted() || System.nanoTime()>deadline)
                        throw new IOException("Completed report exceeds its bounds");
                    digest.update(buffer,0,length);if(wrapper!=null)wrapper.write(buffer,0,length);
                }
                zip.closeEntry();
                if(count!=entry.getSize() || count!=central.getEntry(name).getSize()
                        || entry.getCrc()!=central.getEntry(name).getCrc())throw new IOException("Completed report entry metadata differs");
                if(expected.containsKey(name) && !expected.get(name).equals(digestHex(digest.digest()))) return false;
                if(wrapper!=null) {
                    SessionJson record=new SessionJson(decodeText(wrapper.toByteArray()));
                    String operation=carrier.getFileName().toString().startsWith("coh-character-reopen-")?"character_reopen":"character_creation";
                    android=session.equals(record.session()) && "1".equals(record.root.get("format"))
                            && "io.github.russianranger.cohclientinteractive".equals(record.root.get("app_id"))
                            && operation.equals(record.root.get("operation"))
                            && carrier.getParent().getFileName().toString().equals(record.root.get("run_id"))
                            && record.root.containsKey("app_version") && record.root.get("app_version").matches("[0-9]+\\.[0-9]+\\.[0-9]+");
                }
            }
            if(central.size()!=seen.size())throw new IOException("Completed report inventory differs");
        }
        same(before,regular(carrier,MAX_REPORT_BYTES));
        if(!owned.key.equals(identity(carrier).key))throw new IOException("Completed report was replaced");
        return android && seen.containsAll(expected.keySet());
    }

    /** The original operation time remains authoritative after a repair creates a new carrier directory. */
    public static synchronized long reportStartedUtc(File archive) throws IOException {
        completedArchive(archive.toPath());
        String run=sourceRunId(archive.toPath());
        return Long.parseLong(run.substring(0,run.indexOf('-')));
    }
    private static String sourceRunId(Path file) {
        String fallback=file.getParent().getFileName().toString();
        try(ZipFile zip=new ZipFile(file.toFile())) {
            String[] names={"android-client-report.json","recovery-manifest.json"};
            for(String name:names) {
                ZipEntry entry=zip.getEntry(name);if(entry==null)continue;
                SessionJson record=new SessionJson(zipText(zip,entry,name.equals("android-client-report.json")?MAX_ANDROID_JSON_BYTES:MAX_CHECKPOINT_BYTES));record.parse();
                String run=record.root.get(name.equals("android-client-report.json")?"run_id":"source_run_id");
                if(run!=null && runName(run))return run;
            }
        }catch(IOException invalid){/* Unknown provenance retains the physical run timestamp without inferring attribution. */}
        return fallback;
    }

    /** Read only the bounded stored outcome; a label does not independently qualify gameplay. */
    public static synchronized String reportStatus(File archive) throws IOException {
        Path file=archive.toPath();completedArchive(file);
        BasicFileAttributes before=regular(file,MAX_REPORT_BYTES);FileIdentity owned=identity(file);
        String result="unknown";
        try(ZipFile zip=new ZipFile(file.toFile())) {
            ZipEntry entry=zip.getEntry("android-client-report.json");
            if(entry!=null) {
                SessionJson record=new SessionJson(zipText(zip,entry,MAX_ANDROID_JSON_BYTES));record.parse();
                String status=record.root.get("status");
                if("failed_report_assembly".equals(status) || "true".equals(record.root.get("normal_report_assembly_failed"))) result="finalization_failed";
                else if("passed".equals(status) && "true".equals(record.root.get("passed"))) result="successful";
                else if("client_incomplete".equals(status)) result="incomplete";
                else if("cancelled".equals(status)) result="interrupted";
                else if("failed".equals(status) || "cleanup_failed".equals(status)) result="failed";
            }
            if("unknown".equals(result)) {
                entry=zip.getEntry("recovery-manifest.json");
                if(entry!=null) {
                    SessionJson record=new SessionJson(zipText(zip,entry,MAX_CHECKPOINT_BYTES));record.parse();
                    result="terminal_report_failure".equals(record.root.get("recovery_kind"))?"finalization_failed":"recovered";
                }
            }
        }
        same(before,regular(file,MAX_REPORT_BYTES));
        if(!owned.key.equals(identity(file).key))throw new IOException("Report changed during outcome inspection");
        return result;
    }
    private static String zipText(ZipFile zip,ZipEntry entry,long maximum) throws IOException {
        if(entry.getSize()<0 || entry.getSize()>maximum)throw new IOException("Report outcome exceeds limit");
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();long total=0;
        try(InputStream input=zip.getInputStream(entry)) {
            byte[] buffer=new byte[8192];
            for(int length;(length=input.read(buffer))!=-1;) {
                total+=length;if(total>maximum || Thread.currentThread().isInterrupted())throw new IOException("Report outcome exceeds limit");
                bytes.write(buffer,0,length);
            }
        }
        if(total!=entry.getSize())throw new IOException("Report outcome was truncated");
        return decodeText(bytes.toByteArray());
    }

    /** Parse only a root session identity while validating bounded JSON syntax.
     * Nested session keys and duplicate root keys cannot establish attribution. */
    private static final class SessionJson {
        final String text;int offset;String session;int sessions;final Map<String,String> root=new LinkedHashMap<>();
        SessionJson(String value){text=value;}
        void parse() throws IOException {
            space();if(offset>=text.length() || text.charAt(offset)!='{')throw invalid();value(0);space();
            if(offset!=text.length())throw invalid();
        }
        String session() throws IOException {
            parse();
            if(sessions!=1 || session==null || !session.matches("[0-9a-f]{32}"))throw invalid();return session;
        }
        IOException invalid(){return new IOException("Invalid root report session JSON");}
        void space(){while(offset<text.length() && " \t\r\n".indexOf(text.charAt(offset))>=0)offset++;}
        boolean take(char c){space();if(offset<text.length() && text.charAt(offset)==c){offset++;return true;}return false;}
        String string() throws IOException {
            if(!take('"'))throw invalid();StringBuilder result=new StringBuilder();
            while(offset<text.length()) {
                char c=text.charAt(offset++);if(c=='"')return result.toString();if(c<32)throw invalid();
                if(c=='\\') {
                    if(offset>=text.length())throw invalid();c=text.charAt(offset++);
                    switch(c){case '"':case '\\':case '/':break;case 'b':c='\b';break;case 'f':c='\f';break;
                        case 'n':c='\n';break;case 'r':c='\r';break;case 't':c='\t';break;
                        case 'u':if(offset+4>text.length())throw invalid();try{c=(char)Integer.parseInt(text.substring(offset,offset+4),16);}catch(NumberFormatException wrong){throw invalid();}offset+=4;break;
                        default:throw invalid();}
                }result.append(c);
            }throw invalid();
        }
        void value(int depth) throws IOException {
            if(depth>64)throw invalid();space();if(offset>=text.length())throw invalid();char c=text.charAt(offset);
            if(c=='{') {
                offset++;if(take('}'))return;
                do {String key=string();if(!take(':'))throw invalid();
                    if(depth==0 && (key.equals("session_id") || key.equals("operation") || key.equals("run_id")
                            || key.equals("app_id") || key.equals("app_version") || key.equals("status") || key.equals("recovery_kind") || key.equals("source_run_id"))) {
                        if(root.containsKey(key))throw invalid();space();String selected;
                        if(key.equals("session_id") && text.startsWith("null",offset)){offset+=4;selected=null;}
                        else selected=string();
                        root.put(key,selected);
                        if(key.equals("session_id")){sessions++;session=selected;}
                    } else if(depth==0 && (key.equals("format") || key.equals("passed") || key.equals("normal_report_assembly_failed"))) {
                        if(root.containsKey(key))throw invalid();space();int start=offset;value(depth+1);root.put(key,text.substring(start,offset));
                    } else value(depth+1);
                    if(take('}'))return;if(!take(','))throw invalid();
                }while(true);
            }
            if(c=='['){offset++;if(take(']'))return;do{value(depth+1);if(take(']'))return;if(!take(','))throw invalid();}while(true);}
            if(c=='"'){string();return;}
            int start=offset;while(offset<text.length() && ",]} \t\r\n".indexOf(text.charAt(offset))<0)offset++;
            String scalar=text.substring(start,offset);
            if(!scalar.equals("true") && !scalar.equals("false") && !scalar.equals("null")
                    && !scalar.matches("-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?"))throw invalid();
        }
    }

    /** Call before creating a new operation, while no runtime operation owns these directories.
     * An unsafe/incomplete source throws before startup; callers must retain the guest outputs.
     */
    public static synchronized void recoverAll(File filesRoot) throws IOException {
        Path root = reportRoot(filesRoot, false);
        if (root == null) return;
        IOException failure = null;
        for (Path run : children(root)) {
            if (!runName(run.getFileName().toString())) continue;
            try {
                if (!directoryEntry(run)) continue;
                Path checkpoint = run.resolve("checkpoint.json");
                Path terminal = run.resolve("terminal-failure.json");
                if (!Files.exists(checkpoint, LinkOption.NOFOLLOW_LINKS) && !Files.exists(terminal, LinkOption.NOFOLLOW_LINKS)) continue;
                boolean completed = false;
                for (Path file : children(run)) {
                    if (!archiveName(file.getFileName().toString())) continue;
                    try { completedArchive(file); completed = true; break; }
                    catch (IOException unsafe) { /* An invalid carrier cannot suppress recovery. */ }
                }
                if (Files.exists(terminal, LinkOption.NOFOLLOW_LINKS)) {
                    byte[] note = readText(terminal, MAX_CHECKPOINT_BYTES).getBytes(StandardCharsets.UTF_8);
                    Path log = run.resolve("operation.log");
                    byte[] output = Files.exists(log, LinkOption.NOFOLLOW_LINKS)
                            ? readText(log, 4L * 1024 * 1024).getBytes(StandardCharsets.UTF_8) : new byte[0];
                    retainTerminalFailure(filesRoot, run.toFile(), note, output);
                } else if (!completed) retainInterruptedCheckpoint(run, checkpoint);
            } catch (IOException unsafe) {
                // One damaged historical run must not discard another session's
                // safe evidence. Keep the refusal visible after all runs are read.
                if (failure == null) failure = new IOException("Some interrupted evidence could not be recovered safely");
                failure.addSuppressed(unsafe);
            }
        }
        if (failure != null) throw failure;
    }

    /** Commit the current Android checkpoint before opening optional captures. */
    private static void retainInterruptedCheckpoint(Path run, Path checkpoint) throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        copy(checkpoint, bytes, MAX_CHECKPOINT_BYTES);
        byte[] note = bytes.toByteArray();
        if(findInterruptedCarrier(run.getParent(),run.getFileName().toString(),note)!=null)return;
        Path target = run.resolve("coh-interrupted-" + run.getFileName() + ".zip");
        if (Files.exists(target, LinkOption.NOFOLLOW_LINKS)) {
            Path replacement = run.getParent().resolve(System.currentTimeMillis() + "-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12));
            Files.createDirectory(replacement);
            target = replacement.resolve("coh-interrupted-" + replacement.getFileName() + ".zip");
        }
        Map<String, Path> sources = new LinkedHashMap<>();
        List<String> omitted = new ArrayList<>();
        writeRecoveryArchive(target, null, null, note, omitted, "pending", null,
                Collections.<String, Path>emptyMap(), null, null,run.getFileName().toString());
        FileIdentity compact = identity(target);
        String[] active = {null};
        try {
            recoveryCaptures(run, sources, omitted);
            terminalSource(sources, omitted, "operation.log", run.resolve("operation.log"), 4L * 1024 * 1024);
            writeRecoveryArchive(target, null, null, note, omitted, "complete", null, sources, compact, active,run.getFileName().toString());
        } catch (Exception | OutOfMemoryError unavailable) {
            for (String name : sources.keySet()) if (!omitted.contains(name)) addOmission(omitted,name);
            String reason = unavailable.getClass().getSimpleName().replaceAll("[^A-Za-z0-9_$]", "_");
            if (reason.isEmpty()) reason = "Failure";
            try { writeRecoveryArchive(target, null, null, note, omitted, "failed", reason + (active[0] == null ? "" : ":" + active[0]),
                    Collections.<String, Path>emptyMap(), compact, null,run.getFileName().toString()); }
            catch (Exception | OutOfMemoryError metadataUnavailable) { /* The complete compact checkpoint remains exportable. */ }
        }
    }

    private static Path findInterruptedCarrier(Path root,String sourceRun,byte[] checkpoint) throws IOException {
        for(Path run:children(root)) {
            if(!runName(run.getFileName().toString()))continue;
            Path carrier=run.resolve("coh-interrupted-"+run.getFileName()+".zip");
            try {
                if(!directoryEntry(run) || !Files.exists(carrier,LinkOption.NOFOLLOW_LINKS))continue;
                completedArchive(carrier);
                try(ZipFile zip=new ZipFile(carrier.toFile())) {
                    ZipEntry manifest=zip.getEntry("recovery-manifest.json");
                    if(manifest==null)continue;
                    SessionJson record=new SessionJson(zipText(zip,manifest,MAX_CHECKPOINT_BYTES));record.parse();
                    if(!"interrupted_android_operation".equals(record.root.get("recovery_kind"))
                            || !sourceRun.equals(record.root.get("source_run_id")) || !"false".equals(record.root.get("passed")))continue;
                    ZipEntry entry=zip.getEntry("android-recovery-checkpoint.json");
                    if(entry==null || entry.getSize()!=checkpoint.length)continue;
                    try(InputStream in=zip.getInputStream(entry)) {
                        byte[] buffer=new byte[8192];int offset=0;boolean matches=true;
                        for(int length;(length=in.read(buffer))!=-1;) {
                            if(offset+length>checkpoint.length){matches=false;break;}
                            for(int i=0;i<length;i++)if(buffer[i]!=checkpoint[offset+i]){matches=false;break;}
                            offset+=length;if(!matches)break;
                        }
                        if(matches && offset==checkpoint.length)return carrier;
                    }
                }
            }catch(IOException invalid){/* A corrupt or foreign carrier cannot suppress this run's recovery. */}
        }
        return null;
    }

    private static void addOmission(List<String> omitted,String name) {
        if(omitted.contains(name))return;
        if(omitted.size()<MAX_OMISSIONS)omitted.add(name);
        else if(!omitted.contains("additional_sources_omitted"))omitted.add("additional_sources_omitted");
    }

    private static void recoveryCaptures(Path run, Map<String, Path> sources, List<String> omitted) throws IOException {
        int count = 0; long bytes = 0;
        for (String name : CAPTURE_DIRS) {
            Path dir = run.resolve(name);
            if (!Files.exists(dir, LinkOption.NOFOLLOW_LINKS)) continue;
            try {
                for (Path file : children(dir)) {
                    String relative = name + "/" + file.getFileName();
                    if (!captureName(relative)) continue;
                    try {
                        long length = regular(file, MAX_PNG_BYTES).size();
                        if (count >= MAX_CAPTURES || bytes + length > MAX_CAPTURE_BYTES) throw new IOException("Capture limit");
                        count++; bytes += length; sources.put(relative, file);
                    } catch (IOException invalid) { addOmission(omitted,relative); }
                }
            } catch (IOException invalid) { addOmission(omitted,name); }
        }
    }

    /** A ZIP publication failure must not discard the failed session's diagnostics.
     * Persist a compact terminal record first, then assemble an explicitly unverified
     * carrier from individually safe bounded sources. A bad capture or guest output
     * is listed as omitted; it cannot prevent all the other evidence being exported.
     * This helper never certifies a save, rendering, cleanup or a successful test. */
    public static synchronized File retainTerminalFailure(File filesRoot,File operationDir,
                                                           byte[] terminalJson,byte[] operationLog) throws IOException {
        Path root=reportRoot(filesRoot,true),run=operationDirectory(operationDir);
        if(!root.equals(run.getParent()))throw new IOException("Terminal report is outside private storage");
        if(terminalJson==null || terminalJson.length==0 || terminalJson.length>MAX_CHECKPOINT_BYTES
                || operationLog==null || operationLog.length>4L*1024*1024)
            throw new IOException("Terminal diagnostic evidence exceeds limit");
        atomicBytes(run.resolve("terminal-failure.json"),terminalJson);
        atomicBytes(run.resolve("operation.log"),operationLog);
        // A reuse receipt is optional. Independently locate an exact
        // current carrier, including compact carriers whose receipt write failed.
        Path retained=findTerminalCarrier(root,terminalJson,operationLog);
        if(retained!=null)return retained.toFile();
        Path target=run.resolve("coh-interrupted-"+run.getFileName()+".zip");
        if(Files.exists(target,LinkOption.NOFOLLOW_LINKS)) {
            // Never overwrite corrupt or older evidence while selecting a new carrier.
            Path replacement=root.resolve(System.currentTimeMillis()+"-"+UUID.randomUUID().toString().replace("-","").substring(0,12));
            Files.createDirectory(replacement);target=replacement.resolve("coh-interrupted-"+replacement.getFileName()+".zip");
        }
        final Map<String,Path> sources=new LinkedHashMap<>();final List<String> omitted=new ArrayList<>();
        byte[] checkpoint=null;Path checkpointPath=run.resolve("checkpoint.json");
        if(Files.exists(checkpointPath,LinkOption.NOFOLLOW_LINKS)) {
            try{ByteArrayOutputStream bytes=new ByteArrayOutputStream();copy(checkpointPath,bytes,MAX_CHECKPOINT_BYTES);checkpoint=bytes.toByteArray();}
            catch(Exception | OutOfMemoryError unavailable){addOmission(omitted,"android-recovery-checkpoint.json");}
        }
        // This complete, fsynced carrier exists before any optional guest/capture
        // open, read, archive write or mutation can fail. Only this newly owned
        // compact file may be atomically enriched below; its path never changes.
        writeTerminalArchive(target,terminalJson,operationLog,checkpoint,omitted,"pending",null,
                Collections.<String,Path>emptyMap(),null,null);
        FileIdentity compactIdentity=identity(target);
        String[] activeSource={null};
        try {
            recoveryCaptures(run,sources,omitted);
            Path state=root.getParent().resolve("state");
            boolean sameSession=true;
            try {
                SessionJson expected=new SessionJson(decodeText(terminalJson));String terminalSession=expected.session();
                Path latest=state.resolve("latest-report.json");
                if(Files.exists(latest,LinkOption.NOFOLLOW_LINKS)) {
                    String guestSession=new SessionJson(readText(latest,MAX_JSON_BYTES)).session();
                    sameSession=terminalSession.equals(guestSession);
                }
            }catch(IOException unavailable){/* Raw optional evidence remains unverified when a root identity is unavailable. */}
            if(!sameSession)addOmission(omitted,"guest_session_mismatch");
            if(Files.exists(state,LinkOption.NOFOLLOW_LINKS))for(String name:GUEST_FILES) {
                String archiveName=name.equals("report.zip")?"guest-report.zip":"guest-output/"+name;
                if(!sameSession){if(Files.exists(state.resolve(name),LinkOption.NOFOLLOW_LINKS))addOmission(omitted,archiveName);}
                else terminalSource(sources,omitted,archiveName,state.resolve(name),name.equals("report.zip")?MAX_GUEST_BYTES:MAX_JSON_BYTES);
            }
            writeTerminalArchive(target,terminalJson,operationLog,checkpoint,omitted,"complete",null,
                    sources,compactIdentity,activeSource);
        }catch(Exception | OutOfMemoryError unavailable) {
            // A failed optional entry belongs only to a discarded staging ZIP.
            // The committed compact carrier is still complete and exportable.
            for(String name:sources.keySet())if(!omitted.contains(name))addOmission(omitted,name);
            String failureKind=unavailable.getClass().getSimpleName().replaceAll("[^A-Za-z0-9_$]","_");
            if(failureKind.isEmpty())failureKind="Failure";
            try {writeTerminalArchive(target,terminalJson,operationLog,checkpoint,omitted,"failed",
                    failureKind+(activeSource[0]==null?"":":"+activeSource[0]),
                    Collections.<String,Path>emptyMap(),compactIdentity,null);}
            catch(Exception | OutOfMemoryError metadataUnavailable){/* Retain the complete pending compact carrier. */}
        }
        Path marker=run.resolve("terminal-carrier.txt");
        String fingerprint=digestBytes(terminalJson)+":"+digestBytes(operationLog);
        try {atomicBytes(marker,("1\n"+fingerprint+"\n"+root.relativize(target).toString().replace(File.separatorChar,'/')+"\n").getBytes(StandardCharsets.UTF_8));}
        catch(IOException unavailable){/* Exact namespace discovery does not depend on this hint. */}
        return target.toFile();
    }
    /** Bounded exact discovery prevents duplicate replacement carriers without a writable receipt. */
    private static Path findTerminalCarrier(Path root,byte[] terminal,byte[] log) throws IOException {
        for(Path run:children(root)) {
            if(!runName(run.getFileName().toString()))continue;
            Path carrier=run.resolve("coh-interrupted-"+run.getFileName()+".zip");
            try{if(!directoryEntry(run) || !Files.exists(carrier,LinkOption.NOFOLLOW_LINKS))continue;
                completedArchive(carrier);if(terminalCarrierMatches(carrier,terminal,log))return carrier;}
            catch(IOException invalid){/* Partial, unsafe or foreign carriers cannot satisfy exact discovery. */}
        }return null;
    }
    private static void writeTerminalArchive(Path target,byte[] terminal,byte[] log,byte[] checkpoint,
            List<String> omitted,String enrichment,String enrichmentError,Map<String,Path> sources,
            FileIdentity ownedCompact,String[] activeSource) throws IOException {
        writeRecoveryArchive(target,terminal,log,checkpoint,omitted,enrichment,enrichmentError,sources,ownedCompact,activeSource,null);
    }
    private static void writeRecoveryArchive(Path target,byte[] terminal,byte[] log,byte[] checkpoint,
            List<String> omitted,String enrichment,String enrichmentError,Map<String,Path> sources,
            FileIdentity ownedCompact,String[] activeSource,String sourceRunId) throws IOException {
        Path part=target.resolveSibling("."+target.getFileName()+"."+UUID.randomUUID()+".part");
        try {
            try(FileChannel channel=FileChannel.open(part,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE,LinkOption.NOFOLLOW_LINKS);
                ZipOutputStream zip=new ZipOutputStream(Channels.newOutputStream(channel))) {
                StringBuilder excluded=new StringBuilder();for(String name:omitted){if(excluded.length()>0)excluded.append(',');excluded.append('"').append(name).append('"');}
                String status=terminal==null?"interrupted_unverified":"failed_unverified";
                String kind=terminal==null?"interrupted_android_operation":"terminal_report_failure";
                terminalBytes(zip,"recovery-manifest.json",("{\"format\":1,\"status\":\""+status+"\",\"passed\":false,\"verified\":false,"
                        +"\"recovery_kind\":\""+kind+"\",\"session_attribution_verified\":false,\"enrichment_status\":\""+enrichment+"\","
                        +"\"enrichment_error\":"+(enrichmentError==null?"null":"\""+enrichmentError+"\"")+",\"omitted_sources\":["+excluded+"]"+(sourceRunId==null?"":",\"source_run_id\":\""+sourceRunId+"\"")+"}").getBytes(StandardCharsets.UTF_8));
                if(terminal!=null)terminalBytes(zip,"android-client-report.json",terminal);
                if(log!=null)terminalBytes(zip,"operation.log",log);
                if(checkpoint!=null)terminalBytes(zip,"android-recovery-checkpoint.json",checkpoint);
                for(Map.Entry<String,Path> source:sources.entrySet()) {
                    if(activeSource!=null)activeSource[0]=source.getKey();
                    zip.putNextEntry(new ZipEntry(source.getKey()));
                    copy(source.getValue(),zip,source.getKey().equals("guest-report.zip")?MAX_GUEST_BYTES
                            :source.getKey().startsWith("guest-output/")?MAX_JSON_BYTES
                            :source.getKey().equals("operation.log")?4L*1024*1024:MAX_PNG_BYTES);zip.closeEntry();
                }
                if(activeSource!=null)activeSource[0]=null;
                zip.finish();zip.flush();channel.force(true);
            }
            completedArchive(part);
            if(ownedCompact==null) {
                if(Files.exists(target,LinkOption.NOFOLLOW_LINKS))throw new IOException("Terminal report appeared during publication");
                Files.move(part,target,StandardCopyOption.ATOMIC_MOVE);
            }else {
                regular(target,MAX_REPORT_BYTES);
                if(!ownedCompact.key.equals(identity(target).key))throw new IOException("Owned compact carrier changed during enrichment");
                Files.move(part,target,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
            }
            // The complete staged ZIP was validated and fsynced before the atomic
            // rename. No optional read after replacement may invalidate that commit.
        }finally{try{Files.deleteIfExists(part);}catch(IOException cleanupUnavailable){/* A part is never inventoried as a report. */}}
    }
    private static void terminalBytes(ZipOutputStream zip,String name,byte[] bytes) throws IOException {
        zip.putNextEntry(new ZipEntry(name));zip.write(bytes);zip.closeEntry();
    }
    private static boolean terminalCarrierMatches(Path target,byte[] terminal,byte[] log) throws IOException {
        try(ZipFile zip=new ZipFile(target.toFile())) {
            ZipEntry manifest=zip.getEntry("recovery-manifest.json");
            if(manifest==null || manifest.getSize()<0 || manifest.getSize()>MAX_CHECKPOINT_BYTES)return false;
            ByteArrayOutputStream evidence=new ByteArrayOutputStream();
            try(InputStream in=zip.getInputStream(manifest)) {
                byte[] buffer=new byte[8192];int count;long total=0;
                while((count=in.read(buffer))!=-1){total+=count;if(total>MAX_CHECKPOINT_BYTES)return false;evidence.write(buffer,0,count);}
            }
            String expectedPrefix="{\"format\":1,\"status\":\"failed_unverified\",\"passed\":false,\"verified\":false,"
                    +"\"recovery_kind\":\"terminal_report_failure\",\"session_attribution_verified\":false,\"enrichment_status\":\"";
            String safeName="[A-Za-z0-9_$/.-]+";
            if(!decodeText(evidence.toByteArray()).matches(java.util.regex.Pattern.quote(expectedPrefix)
                    +"(?:pending|complete|failed)\",\"enrichment_error\":(?:null|\""+safeName+"(?::"+safeName+")?\"),"
                    +"\"omitted_sources\":\\[(?:\""+safeName+"\"(?:,\""+safeName+"\")*)?\\]\\}"))return false;
            String[] names={"android-client-report.json","operation.log"};byte[][] expected={terminal,log};
            for(int i=0;i<names.length;i++) {
                ZipEntry entry=zip.getEntry(names[i]);if(entry==null || entry.getSize()!=expected[i].length)return false;
                try(InputStream in=zip.getInputStream(entry)) {
                    byte[] buffer=new byte[8192];int offset=0;
                    for(int n;(n=in.read(buffer))!=-1;) {
                        if(offset+n>expected[i].length)return false;
                        for(int at=0;at<n;at++)if(buffer[at]!=expected[i][offset+at])return false;offset+=n;
                    }
                    if(offset!=expected[i].length)return false;
                }
            }return true;
        }
    }
    private static void terminalSource(Map<String,Path> sources,List<String> omitted,String name,Path file,long limit) {
        if(!Files.exists(file,LinkOption.NOFOLLOW_LINKS))return;
        try{regular(file,limit);sources.put(name,file);}catch(IOException invalid){addOmission(omitted,name);}
    }
    /** Inventory needs a complete central directory, rather than just a .zip suffix.
     * The carrier's content is diagnostic evidence, independent of its pass value. */
    private static void completedArchive(Path file) throws IOException {
        BasicFileAttributes before=regular(file,MAX_REPORT_BYTES);Set<String> names=new HashSet<>();long total=0;
        try(ZipFile zip=new ZipFile(file.toFile())) {
            if(zip.size()==0 || zip.size()>MAX_DIRECTORY_ENTRIES)throw new IOException("Incomplete report archive");
            java.util.Enumeration<? extends ZipEntry> entries=zip.entries();
            while(entries.hasMoreElements()) {
                ZipEntry entry=entries.nextElement();String name=entry.getName();
                if(entry.isDirectory() || name.startsWith("/") || name.contains("\\") || name.contains("\u0000")
                        || !names.add(name) || entry.getSize()<0 || entry.getSize()>MAX_REPORT_BYTES)
                    throw new IOException("Invalid report archive inventory");
                for(String component:name.split("/",-1))if(component.isEmpty() || component.equals(".") || component.equals(".."))
                    throw new IOException("Invalid report archive entry");
                total+=entry.getSize();if(total>MAX_REPORT_BYTES)throw new IOException("Report archive exceeds limit");
            }
        }
        same(before,regular(file,MAX_REPORT_BYTES));
    }

    /** Replace a compact checkpoint atomically; JSON is supplied by the Android runtime. */
    public static synchronized void checkpoint(File operationDir, byte[] json) throws IOException {
        if (json == null || json.length == 0 || json.length > MAX_CHECKPOINT_BYTES)
            throw new IOException("Recovery checkpoint exceeds limit");
        Path run = operationDirectory(operationDir);
        atomicBytes(run.resolve("checkpoint.json"), json);
    }

    /** A fixed capture namespace prevents arbitrary app files from entering a recovery report. */
    public static synchronized void png(File operationDir, String relative, byte[] bytes) throws IOException {
        if (!captureName(relative) || bytes == null || bytes.length < PNG.length || bytes.length > MAX_PNG_BYTES)
            throw new IOException("Invalid recovery capture");
        for (int i = 0; i < PNG.length; i++) if (bytes[i] != PNG[i]) throw new IOException("Recovery capture is not PNG");
        Path run = operationDirectory(operationDir);
        List<Path> existing = captures(run);
        Path target = run.resolve(relative);
        long total = bytes.length;
        int count = 1;
        for (Path file : existing) if (!file.equals(target)) { total += regular(file, MAX_PNG_BYTES).size(); count++; }
        if (total > MAX_CAPTURE_BYTES || count > MAX_CAPTURES) throw new IOException("Recovery capture inventory exceeds limit");
        ensureDirectory(target.getParent());
        atomicBytes(target, bytes);
    }

    /** Stream a selected private report into an already opened SAF output; caller owns the stream. */
    public static long export(File filesRoot, File report, OutputStream destination) throws IOException {
        if (destination == null || report == null) throw new IOException("Report export is unavailable");
        Path root = reportRoot(filesRoot, false);
        Path file = report.toPath().toAbsolutePath().normalize();
        if (root == null || file.getParent() == null || !root.equals(file.getParent().getParent())
                || !runName(file.getParent().getFileName().toString()) || !archiveName(file.getFileName().toString()))
            throw new IOException("Selected report is outside private report storage");
        long copied = copy(file, destination, MAX_REPORT_BYTES);
        destination.flush();
        return copied;
    }

    private static String guestFingerprint(List<Path> sources) throws IOException {
        StringBuilder content=new StringBuilder();
        for(Path file:sources)content.append(file.getFileName()).append(':').append(fileDigest(file,file.getFileName().toString().equals("report.zip")?MAX_GUEST_BYTES:MAX_JSON_BYTES)).append('\n');
        return digestBytes(content.toString().getBytes(StandardCharsets.UTF_8));
    }
    private static String fileDigest(Path file,long max) throws IOException {
        try {
            java.security.MessageDigest digest=java.security.MessageDigest.getInstance("SHA-256");
            OutputStream sink=new java.security.DigestOutputStream(new OutputStream(){@Override public void write(int b){}@Override public void write(byte[] b,int o,int n){}},digest);
            copy(file,sink,max);return digestHex(digest.digest());
        }catch(java.security.NoSuchAlgorithmException impossible){throw new IOException("SHA-256 unavailable",impossible);}
    }
    private static String digestBytes(byte[] bytes) throws IOException {
        try{return digestHex(java.security.MessageDigest.getInstance("SHA-256").digest(bytes));}
        catch(java.security.NoSuchAlgorithmException impossible){throw new IOException("SHA-256 unavailable",impossible);}
    }
    private static String digestHex(byte[] bytes){StringBuilder result=new StringBuilder();for(byte value:bytes)result.append(String.format(java.util.Locale.ROOT,"%02x",value&255));return result.toString();}

    private static boolean runName(String name) { return name.matches("[0-9]{10,17}-[0-9a-f]{12}"); }
    private static boolean archiveName(String name) {
        return name.matches("coh-(?:character-(?:creation|reopen)|interrupted(?:-guest)?)-[0-9]{10,17}-[0-9a-f]{12}\\.zip");
    }
    private static boolean captureName(String value) {
        if (value == null || !value.matches("android-(?:surface|login|connected|relocated|character|interaction|contact|task|zoning)/(?:accepted-|completed-)?capture-[1-9][0-9]{0,2}\\.png")) return false;
        if ((value.contains("/accepted-") || value.contains("/completed-")) && !value.startsWith("android-task/")) return false;
        int dash = value.lastIndexOf('-'), dot = value.lastIndexOf('.');
        return Integer.parseInt(value.substring(dash + 1, dot)) <= 256;
    }
    private static Path operationDirectory(File operationDir) throws IOException {
        Path run = directory(operationDir.toPath());
        if (!runName(run.getFileName().toString()) || run.getParent() == null
                || !"reports".equals(run.getParent().getFileName().toString())
                || run.getParent().getParent() == null || !"client".equals(run.getParent().getParent().getFileName().toString()))
            throw new IOException("Invalid recovery operation directory");
        return run;
    }
    private static Path reportRoot(File filesRoot, boolean create) throws IOException {
        Path files = directory(filesRoot.toPath());
        Path client = files.resolve("client"), reports = client.resolve("reports");
        if (create) { ensureDirectory(client); ensureDirectory(reports); }
        else if (!Files.exists(reports, LinkOption.NOFOLLOW_LINKS)) {
            if (Files.exists(client, LinkOption.NOFOLLOW_LINKS)) directory(client);
            return null;
        }
        return directory(reports);
    }
    private static void ensureDirectory(Path path) throws IOException {
        directory(path.getParent());
        if (!Files.exists(path, LinkOption.NOFOLLOW_LINKS)) Files.createDirectory(path);
        directory(path);
    }
    private static Path directory(Path source) throws IOException {
        Path path = source.toAbsolutePath().normalize();
        Path current = path.getRoot();
        for (Path component : path) {
            current = current.resolve(component);
            BasicFileAttributes info = Files.readAttributes(current, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
            if (!info.isDirectory() || info.isSymbolicLink()) throw new IOException("Unsafe diagnostic directory");
        }
        return path;
    }
    private static boolean directoryEntry(Path path) throws IOException {
        BasicFileAttributes info = Files.readAttributes(path, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
        return info.isDirectory() && !info.isSymbolicLink();
    }
    private static List<Path> children(Path path) throws IOException {
        directory(path);
        List<Path> list = new ArrayList<>();
        try (DirectoryStream<Path> entries = Files.newDirectoryStream(path)) {
            for (Path entry : entries) {
                if (list.size() >= MAX_DIRECTORY_ENTRIES) throw new IOException("Diagnostic inventory exceeds limit");
                list.add(entry);
            }
        }
        return list;
    }
    private static BasicFileAttributes regular(Path file, long max) throws IOException {
        directory(file.getParent());
        BasicFileAttributes info = Files.readAttributes(file, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
        if (!info.isRegularFile() || info.isSymbolicLink() || info.size() < 0 || info.size() > max)
            throw new IOException("Unsafe or oversized diagnostic file");
        identity(file);
        return info;
    }
    private static FileIdentity identity(Path file) throws IOException {
        FileIdentity value;
        IdentityReader reader = identityReader;
        if (reader != null) value = reader.read(file.toFile());
        else try {
            Object links = Files.getAttribute(file, "unix:nlink", LinkOption.NOFOLLOW_LINKS);
            Object device = Files.getAttribute(file, "unix:dev", LinkOption.NOFOLLOW_LINKS);
            Object inode = Files.getAttribute(file, "unix:ino", LinkOption.NOFOLLOW_LINKS);
            if (!(device instanceof Number) || !(inode instanceof Number)) throw new IOException("Diagnostic file identity is unavailable");
            value = new FileIdentity(links instanceof Number ? ((Number)links).longValue() : -1, device + ":" + inode);
        } catch (UnsupportedOperationException | IllegalArgumentException unsupported) {
            throw new IOException("Diagnostic file identity provider is unavailable", unsupported);
        }
        if (value == null || value.linkCount != 1 || value.key == null || value.key.length() == 0)
            throw new IOException("Diagnostic file identity or link count is unsafe");
        return value;
    }
    private static List<Path> captures(Path run) throws IOException {
        List<Path> found = new ArrayList<>(); long total = 0;
        for (String name : CAPTURE_DIRS) {
            Path dir = run.resolve(name);
            if (!Files.exists(dir, LinkOption.NOFOLLOW_LINKS)) continue;
            directory(dir);
            for (Path file : children(dir)) {
                String relative = name + "/" + file.getFileName();
                if (!captureName(relative)) continue;
                total += regular(file, MAX_PNG_BYTES).size();
                found.add(file);
                if (found.size() > MAX_CAPTURES || total > MAX_CAPTURE_BYTES) throw new IOException("Recovery capture inventory exceeds limit");
            }
        }
        return found;
    }
    private static void same(BasicFileAttributes before, BasicFileAttributes after) throws IOException {
        if (before.size() != after.size() || !before.lastModifiedTime().equals(after.lastModifiedTime())
                || before.fileKey() != null && !before.fileKey().equals(after.fileKey()))
            throw new IOException("Diagnostic evidence changed during copy");
    }
    private static long copy(Path file, OutputStream out, long max) throws IOException {
        if (Thread.currentThread().isInterrupted()) throw new IOException("Diagnostic export was cancelled");
        BasicFileAttributes before = regular(file, max);
        FileIdentity identityBefore = identity(file);
        long deadline = System.nanoTime() + MAX_EXPORT_MILLIS * 1000000L;
        long copied = 0;
        try (SeekableByteChannel channel = openSource(file)) {
            same(before, regular(file, max));
            if (!identityBefore.key.equals(identity(file).key)) throw new IOException("Diagnostic file was replaced");
            ByteBuffer data = ByteBuffer.allocate(65536);
            for (int count; (count = channel.read(data)) != -1;) {
                if (System.nanoTime() >= deadline || Thread.currentThread().isInterrupted()) throw new IOException("Diagnostic export timed out or was cancelled");
                if (count == 0) continue;
                copied += count;
                if (copied > max || copied > before.size()) throw new IOException("Diagnostic evidence grew during copy");
                out.write(data.array(), 0, count); data.clear();
                if (System.nanoTime() >= deadline || Thread.currentThread().isInterrupted()) throw new IOException("Diagnostic export timed out or was cancelled");
            }
        }
        same(before, regular(file, max));
        if (!identityBefore.key.equals(identity(file).key)) throw new IOException("Diagnostic file was replaced");
        if (copied != before.size()) throw new IOException("Diagnostic evidence truncated during copy");
        return copied;
    }
    private static void atomicBytes(Path target, byte[] bytes) throws IOException {
        directory(target.getParent());
        if (Files.exists(target, LinkOption.NOFOLLOW_LINKS)) regular(target, Math.max(MAX_CHECKPOINT_BYTES, MAX_PNG_BYTES));
        Path part = target.resolveSibling("." + target.getFileName() + "." + UUID.randomUUID() + ".part");
        try {
            try (FileChannel out = FileChannel.open(part, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS)) {
                ByteBuffer buffer = ByteBuffer.wrap(bytes);
                while (buffer.hasRemaining()) out.write(buffer);
                out.force(true);
            }
            directory(target.getParent()); regular(part, bytes.length);
            if (Files.exists(target, LinkOption.NOFOLLOW_LINKS)) regular(target, Math.max(MAX_CHECKPOINT_BYTES, MAX_PNG_BYTES));
            Files.move(part, target, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            regular(target, bytes.length);
        } finally { Files.deleteIfExists(part); }
    }
    private static void archive(Path target, List<Path> sources, Path base, Path checkpoint,
                                String kind, boolean androidCheckpoint) throws IOException {
        directory(target.getParent());
        if (Files.exists(target, LinkOption.NOFOLLOW_LINKS)) throw new IOException("Recovery report already exists");
        Path part = target.resolveSibling("." + target.getFileName() + "." + UUID.randomUUID() + ".part");
        try {
            try (FileChannel channel = FileChannel.open(part, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS)) {
                try (ZipOutputStream zip = new ZipOutputStream(Channels.newOutputStream(channel))) {
                String manifest = "{\"format\":1,\"status\":\"interrupted_unverified\",\"passed\":false,\"verified\":false,"
                        + "\"recovery_kind\":\"" + kind + "\",\"session_attribution_verified\":false,"
                        + "\"note\":\"Preserved diagnostic evidence only. No successful Finish, character save, or zoning qualification is inferred.\"}";
                zip.putNextEntry(new ZipEntry("recovery-manifest.json")); zip.write(manifest.getBytes(StandardCharsets.UTF_8)); zip.closeEntry();
                if (checkpoint != null) {
                    zip.putNextEntry(new ZipEntry("android-recovery-checkpoint.json")); copy(checkpoint, zip, MAX_CHECKPOINT_BYTES); zip.closeEntry();
                }
                for (Path source : sources) {
                    String name = base.relativize(source).toString().replace(File.separatorChar, '/');
                    zip.putNextEntry(new ZipEntry(androidCheckpoint ? name : "previous-guest/" + name));
                    copy(source, zip, androidCheckpoint ? MAX_PNG_BYTES : name.equals("report.zip") ? MAX_GUEST_BYTES : MAX_JSON_BYTES);
                    zip.closeEntry();
                }
                zip.finish(); zip.flush(); channel.force(true);
                }
            }
            regular(part, MAX_REPORT_BYTES); directory(target.getParent());
            if (Files.exists(target, LinkOption.NOFOLLOW_LINKS)) throw new IOException("Recovery report appeared during publication");
            Files.move(part, target, StandardCopyOption.ATOMIC_MOVE);
            regular(target, MAX_REPORT_BYTES);
        } finally { Files.deleteIfExists(part); }
    }
}
