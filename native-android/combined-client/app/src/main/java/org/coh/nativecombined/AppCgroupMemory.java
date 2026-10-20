package org.coh.nativecombined;

import java.io.IOException;
import java.nio.file.*;
import java.util.*;

/** Optional kernel charge observation; never RSS/PSS, admission or process ownership. */
final class AppCgroupMemory {
    static final int SOURCE_LIMIT=65536, PATH_LIMIT=512;
    private static final class Membership {
        final String path;final boolean unified;
        Membership(String path,boolean unified){this.path=path;this.unified=unified;}
    }
    private static final class Mount {
        final Path root,point;final boolean unified;
        Mount(Path root,Path point,boolean unified){this.root=root;this.point=point;this.unified=unified;}
    }
    private static String read(ProcessSetMemory.ProcReader reader,Path path,int cap)throws IOException {
        String value=reader.read(path,cap);if(value==null||value.length()>cap)throw new IOException("SOURCE_LIMIT");return value;
    }
    private static String unescape(String value)throws IOException {
        StringBuilder result=new StringBuilder();
        for(int i=0;i<value.length();i++){
            char c=value.charAt(i);
            if(c=='\\'){
                if(i+3>=value.length())throw new IOException("MOUNT_ESCAPE");String code=value.substring(i+1,i+4);i+=3;
                if(code.equals("040"))c=' ';else if(code.equals("134"))c='\\';else throw new IOException("MOUNT_ESCAPE");
            }
            if(c<32||c>126)throw new IOException("SOURCE_PATH");result.append(c);
        }
        return result.toString();
    }
    private static Path path(String value)throws IOException {
        if(value.length()>PATH_LIMIT||!value.startsWith("/"))throw new IOException("SOURCE_PATH");
        for(int i=0;i<value.length();i++)if(value.charAt(i)<32||value.charAt(i)>126)throw new IOException("SOURCE_PATH");
        for(String part:value.split("/"))if(part.equals(".")||part.equals(".."))throw new IOException("SOURCE_PATH");
        Path result=Paths.get(value);if(!result.toString().equals(value)||!result.normalize().equals(result))throw new IOException("SOURCE_PATH");return result;
    }
    private static Path uidAncestor(String membership,long uid)throws IOException {
        Path candidate=path(membership),prefix=Paths.get("/");String wanted="uid_"+uid;Path result=null;
        for(Path part:candidate){prefix=prefix.resolve(part);if(part.toString().equals(wanted)){
            if(result!=null)throw new IOException("AMBIGUOUS_UID");result=prefix;
        }}return result;
    }
    private static List<Membership> memberships(String raw)throws IOException {
        List<Membership> result=new ArrayList<>();boolean v1=false,v2=false;
        for(String line:raw.split("\n")){
            if(line.isEmpty())continue;String[] fields=line.split(":",3);if(fields.length!=3)throw new IOException("CGROUP_FORMAT");
            if(fields[0].equals("0")&&fields[1].isEmpty()){
                if(v2)throw new IOException("AMBIGUOUS_MEMBERSHIP");v2=true;result.add(0,new Membership(fields[2],true));
            }else if(Arrays.asList(fields[1].split(",")).contains("memory")){
                if(v1)throw new IOException("AMBIGUOUS_MEMBERSHIP");v1=true;result.add(new Membership(fields[2],false));
            }
        }return result;
    }
    private static List<Mount> mounts(String raw)throws IOException {
        List<Mount> result=new ArrayList<>();
        for(String line:raw.split("\n")){
            int separator=line.indexOf(" - ");if(separator<0)continue;
            String[] left=line.substring(0,separator).split(" "),right=line.substring(separator+3).split(" ");
            if(left.length<6||right.length<3)continue;
            boolean unified=right[0].equals("cgroup2"),memory=right[0].equals("cgroup")&&Arrays.asList(right[2].split(",")).contains("memory");
            if(unified||memory)result.add(new Mount(path(unescape(left[3])),path(unescape(left[4])),unified));
        }return result;
    }
    private static boolean aliases(Path path){
        Path prefix=path.getRoot();for(Path part:path){prefix=prefix.resolve(part);if(Files.isSymbolicLink(prefix))return true;}return false;
    }
    private static Long bytes(String raw){
        String value=raw.trim();if(!value.matches("[0-9]{1,19}"))return null;
        try{return Long.parseLong(value);}catch(NumberFormatException invalid){return null;}
    }
    static Map<String,Object> observe(Path proc,long uid,ProcessSetMemory.ProcReader reader){
        Map<String,Object> out=new LinkedHashMap<>();out.put("status","unavailable");out.put("reason","CGROUP_SOURCE_UNAVAILABLE");out.put("uid",uid);out.put("charge_bytes",null);
        out.put("scope","kernel UID-named cgroup charge; not same-UID RSS/PSS or whole-device RAM");
        out.put("source","proc/self/cgroup and proc/self/mountinfo");
        try {
            String membership=read(reader,proc.resolve("self/cgroup"),SOURCE_LIMIT),mountinfo=read(reader,proc.resolve("self/mountinfo"),SOURCE_LIMIT);
            List<Membership> memberships=memberships(membership);List<Mount> mounts=mounts(mountinfo);
            out.put("reason","NO_APP_UID_MEMORY_CGROUP");
            for(Membership member:memberships){
                Path group=uidAncestor(member.path,uid);if(group==null)continue;
                Mount selected=null;Path directory=null;
                for(Mount mount:mounts)if(mount.unified==member.unified&&group.startsWith(mount.root)){
                    Path candidate=mount.point.resolve(mount.root.relativize(group)).normalize();
                    if(selected==null||mount.root.getNameCount()>selected.root.getNameCount()){selected=mount;directory=candidate;}
                    else if(mount.root.getNameCount()==selected.root.getNameCount()&&!candidate.equals(directory))throw new IOException("AMBIGUOUS_MEMORY_MOUNT");
                }
                if(selected==null){out.put("reason","UID_MEMORY_MOUNT_UNAVAILABLE");continue;}
                Path counter=directory.resolve(member.unified?"memory.current":"memory.usage_in_bytes");
                if(counter.toString().length()>PATH_LIMIT||aliases(counter)){out.put("reason","CGROUP_PATH_ALIAS_OR_LIMIT");continue;}
                if(!Files.isRegularFile(counter,LinkOption.NOFOLLOW_LINKS)){out.put("reason","CGROUP_COUNTER_UNAVAILABLE");continue;}
                Long charge;
                try{charge=bytes(read(reader,counter,128));}catch(IOException inaccessible){out.put("reason","CGROUP_COUNTER_UNREADABLE");continue;}
                if(charge==null){out.put("reason","CGROUP_COUNTER_INVALID");continue;}
                if(!membership.equals(read(reader,proc.resolve("self/cgroup"),SOURCE_LIMIT))){out.put("reason","CGROUP_MEMBERSHIP_CHANGED");return out;}
                if(!mountinfo.equals(read(reader,proc.resolve("self/mountinfo"),SOURCE_LIMIT))||aliases(counter)){out.put("reason","CGROUP_MOUNT_CHANGED");return out;}
                Boolean hierarchy=member.unified?Boolean.TRUE:null;
                if(!member.unified)try{String value=read(reader,directory.resolve("memory.use_hierarchy"),64).trim();hierarchy=value.equals("1")?Boolean.TRUE:value.equals("0")?Boolean.FALSE:null;}catch(IOException unavailable){/* No hierarchy guess. */}
                out.put("status","observed");out.put("reason","");out.put("charge_bytes",charge);out.put("hierarchical_accounting",hierarchy);
                out.put("counter",counter.getFileName().toString());out.put("counter_path",counter.toString());out.put("membership_path",member.path);
                out.put("mount_point",selected.point.toString());out.put("mount_root",selected.root.toString());
                // kernel.org/admin-guide/cgroup-v1/memory.html: v1 usage is an
                // approximate charge counter. It is not converted into PSS.
                out.put("counter_semantics",member.unified?"v2_hierarchical_charge_bytes":"v1_approximate_charge_bytes");return out;
            }
        }catch(IOException|RuntimeException unavailable){out.put("reason","CGROUP_SOURCE_INVALID_OR_UNREADABLE");}
        return out;
    }
}
