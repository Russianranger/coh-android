/* NONSHIPPING source-owned startup sink, no heap allocation. The loader/static
 * witness and borrowed engine owner are external to Android process accounting.
 * Output is exclusive; every normal path wipes pointer/byte state. */
#include <stdio.h>
#include <fcntl.h>
#include <sys/stat.h>
#ifdef _WIN32
#include <io.h>
#define COH_BODY_OPEN _open
#define COH_BODY_WRITE _write
#define COH_BODY_CLOSE _close
#define COH_BODY_UNLINK _unlink
#define COH_BODY_FLAGS (_O_WRONLY|_O_CREAT|_O_EXCL|_O_BINARY)
#define COH_BODY_MODE (_S_IREAD|_S_IWRITE)
#else
#include <unistd.h>
#ifndef COH_BODY_OPEN
#define COH_BODY_OPEN open
#endif
#ifndef COH_BODY_WRITE
#define COH_BODY_WRITE write
#endif
#ifndef COH_BODY_CLOSE
#define COH_BODY_CLOSE close
#endif
#ifndef COH_BODY_UNLINK
#define COH_BODY_UNLINK unlink
#endif
#define COH_BODY_FLAGS (O_WRONLY|O_CREAT|O_EXCL)
#define COH_BODY_MODE (S_IRUSR|S_IWUSR)
#endif
static int coh_body_witness_path_safe(const char*p){
 size_t n=0;if(!p)return 0;while(n<=240&&p[n])n++;if(n<3||n>240||strstr(p,".."))return 0;
#ifdef _WIN32
 return((p[0]>='A'&&p[0]<='Z')||(p[0]>='a'&&p[0]<='z'))&&p[1]==':'&&(p[2]=='/'||p[2]=='\\');
#else
 return p[0]=='/';
#endif
}
int coh_source_body_witness_snapshot_startup(void){
 const char*path=getenv("COH_NATIVE_BODY_WITNESS_OUTPUT");size_t bytes=0,at=0;unsigned rc=0;int fd=-1,closed;
 if(!path)goto done;
 if(!coh_body_witness_path_safe(path)){rc=1;goto done;}
 if(coh_body_witness.error||!coh_body_witness.ready||coh_body_witness.root!=&bodyPartList||
  coh_body_witness.rows!=bodyPartList.bodyParts||coh_body_witness.count!=GetBodyPartCount()){rc=4;goto done;}
 rc=coh_body_witness_serialize(1,coh_body_witness.used,&bytes);
 if(rc||bytes!=coh_body_witness.used){if(!rc)rc=3;goto done;}
 fd=COH_BODY_OPEN(path,COH_BODY_FLAGS,COH_BODY_MODE);if(fd<0){rc=1;goto done;}
 while(at<bytes){int n=(int)COH_BODY_WRITE(fd,coh_body_witness.bytes+at,(unsigned)(bytes-at));if(n<=0||(size_t)n>bytes-at)break;at+=(size_t)n;}
 closed=COH_BODY_CLOSE(fd);fd=-1;
 if(closed){fprintf(stderr,"COH_NATIVE_BODY_WITNESS_CLOSE_FAILED descriptor_state_unknown=1 path=%s\n",path);rc=6;}
 if(at!=bytes||closed){if(!rc)rc=1;if(COH_BODY_UNLINK(path)!=0){fprintf(stderr,"COH_NATIVE_BODY_WITNESS_CLEANUP_FAILED owned_partial=1 path=%s\n",path);rc=5;}}
 if(!rc)printf("COH_NATIVE_BODY_WITNESS_COMPLETE bytes=%u current_map_generation_verified=0 actor_authority=0\n",(unsigned)bytes);
 done:
 coh_body_witness_wipe(&coh_body_witness,sizeof(coh_body_witness));coh_body_witness_last_status=rc;return(int)rc;
}
#undef COH_BODY_OPEN
#undef COH_BODY_WRITE
#undef COH_BODY_CLOSE
#undef COH_BODY_UNLINK
#undef COH_BODY_FLAGS
#undef COH_BODY_MODE
