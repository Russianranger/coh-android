/* Source-only admission for the startup constructor. No provider authority. */
#ifndef COH_LIVE_NATIVE_POLICY_H
#define COH_LIVE_NATIVE_POLICY_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#define COH_LIVE_GUEST_PATH_CAP 1025u
#define COH_LIVE_NATIVE_RECIPE "wine-b073-constructor-v1"

static int cohLiveAsciiHex(const char *text, unsigned char *out, size_t count) {
 size_t i;
 if(!text||!out||strlen(text)!=count*2u)return 0;
 for(i=0;i<count;i++) {
  unsigned int a=(unsigned char)text[i*2],b=(unsigned char)text[i*2+1];
  if(a>='0'&&a<='9')a-='0';else if(a>='a'&&a<='f')a=a-'a'+10;else return 0;
  if(b>='0'&&b<='9')b-='0';else if(b>='a'&&b<='f')b=b-'a'+10;else return 0;
  out[i]=(unsigned char)((a<<4)|b);
 }
 return 1;
}
static int cohLiveDecimalU64(const char *text,uint64_t *out) {
 uint64_t value=0;size_t i,n;
 if(!text||!out||!(n=strlen(text))||n>20||(n>1&&text[0]=='0'))return 0;
 for(i=0;i<n;i++) {unsigned int digit=(unsigned char)text[i]-'0';
  if(digit>9||value>(UINT64_MAX-digit)/10u)return 0;value=value*10u+digit;
 }
 *out=value;return 1;
}
static int cohLiveGuestPathValid(const char *path) {
 size_t i,start=1,n;
 if(!path||!(n=strlen(path))||n>=COH_LIVE_GUEST_PATH_CAP||path[0]!='/'||n==1||path[n-1]=='/')return 0;
 for(i=1;i<=n;i++) {
  unsigned char c=(unsigned char)path[i];
  if(i<n&&(c<32||c>=127||strchr("\\:*?\"<>|",c)))return 0;
  if(i==n||c=='/') {
   size_t len=i-start;
   if(!len||(len==1&&path[start]=='.')||(len==2&&path[start]=='.'&&path[start+1]=='.'))return 0;
   start=i+1;
  }
 }
 return 1;
}
/* The Wine mapping is only the reviewed Z: guest root. No foreign drive,
 * host realpath, UNC path or lexical dot-path guessing is accepted. */
static int cohLiveGuestFromDos(const char *dos,char out[COH_LIVE_GUEST_PATH_CAP]) {
 size_t i,n;
 if(!dos||!out||!(n=strlen(dos))||n<4||n>=COH_LIVE_GUEST_PATH_CAP+2u||
    (dos[0]!='Z'&&dos[0]!='z')||dos[1]!=':'||(dos[2]!='/'&&dos[2]!='\\'))return 0;
 for(i=2;i<=n;i++)out[i-2]=dos[i]=='\\'?'/':dos[i];
 return cohLiveGuestPathValid(out);
}
static unsigned char cohLiveAsciiUpper(unsigned char c) {
 return c>='a'&&c<='z'?(unsigned char)(c-'a'+'A'):c;
}
static int cohLiveBranchEqual(const char *text,size_t length,const char *literal) {
 size_t i;if(strlen(literal)!=length)return 0;
 for(i=0;i<length;i++)if(cohLiveAsciiUpper((unsigned char)text[i])!=cohLiveAsciiUpper((unsigned char)literal[i]))return 0;
 return 1;
}
/* The exact registered root remains case-sensitive. Only the first admitted
 * branch component is canonicalized; actual held-directory inode comparison
 * and backend ambiguity refusal must precede NEXT. Descendant names retain
 * their bytes from ordinary native rows. This is not generic Wine path lookup. */
static int cohLiveSelectedGuestPath(const char *registered_root,const char *gdd_guest,
 const char *directory_guest,char out[COH_LIVE_GUEST_PATH_CAP]) {
 const char *rel,*slash,*branch=NULL;size_t root_len,branch_len,tail_len;
 if(!cohLiveGuestPathValid(registered_root)||!cohLiveGuestPathValid(gdd_guest)||
    !cohLiveGuestPathValid(directory_guest)||strcmp(registered_root,gdd_guest))return 0;
 root_len=strlen(registered_root);
 if(strncmp(registered_root,directory_guest,root_len)||directory_guest[root_len]!='/')return 0;
 rel=directory_guest+root_len+1;slash=strchr(rel,'/');branch_len=slash?(size_t)(slash-rel):strlen(rel);
 if(cohLiveBranchEqual(rel,branch_len,"fx"))branch="fx";
 else if(cohLiveBranchEqual(rel,branch_len,"scripts.loc"))branch="scripts.loc";
 else return 0;
 tail_len=slash?strlen(slash):0;
 if(root_len+1+strlen(branch)+tail_len>=COH_LIVE_GUEST_PATH_CAP)return 0;
 memcpy(out,registered_root,root_len);out[root_len]='/';
 memcpy(out+root_len+1,branch,strlen(branch));
 if(slash)memcpy(out+root_len+1+strlen(branch),slash,tail_len);
 out[root_len+1+strlen(branch)+tail_len]=0;return 1;
}
static int cohLiveEndpoint(const char *endpoint,unsigned short *port) {
 uint64_t value;const char *prefix="127.0.0.1:";
 if(!endpoint||!port||strncmp(endpoint,prefix,strlen(prefix))||
    !cohLiveDecimalU64(endpoint+strlen(prefix),&value)||value==0||value>65535)return 0;
 *port=(unsigned short)value;return 1;
}
/* A normalized native object may name an admitted directory alias target in
 * /game-import/data. Request identity remains the original registered root;
 * same-branch scope is only a path guard, never a replacement for held inode
 * + independently registered physical-device agreement. */
static int cohLiveAuthorizedFinalScope(const char *registered_root,const char *request,
 const char *final_guest) {
 char original[COH_LIVE_GUEST_PATH_CAP],resolved[COH_LIVE_GUEST_PATH_CAP];
 const char *original_branch,*resolved_branch;size_t original_len,resolved_len;
 if(!cohLiveSelectedGuestPath(registered_root,registered_root,request,original))return 0;
 original_branch=original+strlen(registered_root)+1;
 original_len=strcspn(original_branch,"/");
 if(cohLiveSelectedGuestPath(registered_root,registered_root,final_guest,resolved))
  resolved_branch=resolved+strlen(registered_root)+1;
 else if(cohLiveSelectedGuestPath("/game-import/data","/game-import/data",final_guest,resolved))
  resolved_branch=resolved+strlen("/game-import/data")+1;
 else return 0;
 resolved_len=strcspn(resolved_branch,"/");
 return original_len==resolved_len&&!memcmp(original_branch,resolved_branch,original_len);
}
#endif
