/* NONSHIPPING Win32/host diagnostic sink. New owned output only; never overwrite.
 * Configuration is supplied by separately pinned build inputs, not read from the
 * file being exported. Caller records actual source/profile/bin/run association.
 * Partial owned output cleanup is attempted on ordinary failure; unlink failure
 * returns3 and explicitly reports the retained path. Crash cleanup is external.
 */
#include <stdlib.h>
#include <stdio.h>
#include <fcntl.h>
#include <sys/stat.h>
#ifdef _WIN32
#include <io.h>
#define COH_COSTUME_OPEN _open
#ifndef COH_COSTUME_WRITE
#define COH_COSTUME_WRITE _write
#endif
#define COH_COSTUME_CLOSE _close
#ifndef COH_COSTUME_UNLINK
#define COH_COSTUME_UNLINK _unlink
#endif
#define COH_COSTUME_FLAGS (_O_WRONLY|_O_CREAT|_O_EXCL|_O_BINARY)
#define COH_COSTUME_MODE (_S_IREAD|_S_IWRITE)
#else
#include <unistd.h>
#define COH_COSTUME_OPEN open
#ifndef COH_COSTUME_WRITE
#define COH_COSTUME_WRITE write
#endif
#define COH_COSTUME_CLOSE close
#ifndef COH_COSTUME_UNLINK
#define COH_COSTUME_UNLINK unlink
#endif
#define COH_COSTUME_FLAGS (O_WRONLY|O_CREAT|O_EXCL)
#define COH_COSTUME_MODE (S_IRUSR|S_IWUSR)
#endif
#include "coh_costume_export_configuration.inc"
static int coh_costume_output_safe(const char*p){
 size_t n=0;int absolute=0;
 if(!p)return 0;
 while(n<=240&&p[n])n++;
 if(!n||n>240||strstr(p,".."))return 0;
#ifdef _WIN32
 absolute=((p[0]>='A'&&p[0]<='Z')||(p[0]>='a'&&p[0]<='z'))&&p[1]==':'&&(p[2]=='/'||p[2]=='\\');
#else
 absolute=p[0]=='/';
#endif
 return absolute;
}
int coh_source_costume_snapshot_startup(void){
 const char*path=getenv("COH_NATIVE_COSTUME_OUTPUT");unsigned char*buffer;size_t bytes=0,at=0;int fd,rc;
 if(!path)return 0;
 if(!coh_costume_output_safe(path))return 1;
 buffer=(unsigned char*)malloc(4u*1024u*1024u);if(!buffer)return 1;
 rc=coh_source_costume_export(buffer,4u*1024u*1024u,coh_costume_export_generation,coh_costume_export_inventory,coh_costume_export_profile,coh_costume_export_run,&bytes);
 if(rc){free(buffer);return rc;}
 fd=COH_COSTUME_OPEN(path,COH_COSTUME_FLAGS,COH_COSTUME_MODE);if(fd<0){free(buffer);return 1;}
 while(at<bytes){int n=(int)COH_COSTUME_WRITE(fd,buffer+at,(unsigned)(bytes-at));if(n<=0)break;at+=(size_t)n;}
 rc=COH_COSTUME_CLOSE(fd);free(buffer);
 if(at!=bytes||rc){
  if(COH_COSTUME_UNLINK(path)!=0){fprintf(stderr,"COH_NATIVE_COSTUME_EXPORT_CLEANUP_FAILED owned_partial=1 path=%s\n",path);return 3;}
  return 1;
 }
 printf("COH_NATIVE_COSTUME_EXPORT_COMPLETE bytes=%u source_snapshot_only=1 actor_authority=0\n",(unsigned)bytes);
 return 0;
}
#undef COH_COSTUME_OPEN
#undef COH_COSTUME_WRITE
#undef COH_COSTUME_CLOSE
#undef COH_COSTUME_UNLINK
#undef COH_COSTUME_FLAGS
#undef COH_COSTUME_MODE
