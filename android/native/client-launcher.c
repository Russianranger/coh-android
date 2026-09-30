/* Keep the unmodified CoH GUI client's hidden console on our owned pipe. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static void output(HANDLE handle, const char *text) {
    DWORD written;
    WriteFile(handle, text, (DWORD)strlen(text), &written, NULL);
}
static int quoted(char *out, size_t limit, const char *text) {
    size_t used=0, slashes=0;
    if (limit<3) return 0;
    out[used++]='"';
    while (*text) {
        if (*text=='\\') { slashes++; text++; continue; }
        if (*text=='"') {
            if (used+slashes*2+2>=limit) return 0;
            while(slashes) { out[used++]='\\'; out[used++]='\\'; slashes--; }
            slashes=0; out[used++]='\\'; out[used++]=*text++;
        } else {
            if (used+slashes+1>=limit) return 0;
            while(slashes) { out[used++]='\\'; slashes--; }
            out[used++]=*text++;
        }
    }
    if (used+slashes*2+2>limit) return 0;
    while(slashes) { out[used++]='\\'; out[used++]='\\'; slashes--; }
    out[used++]='"'; out[used]=0; return 1;
}
int main(int argc, char **argv) {
    HANDLE saved[3]={GetStdHandle(STD_INPUT_HANDLE), GetStdHandle(STD_OUTPUT_HANDLE), GetStdHandle(STD_ERROR_HANDLE)};
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    char command[4096], executable[2048], message[512];
    DWORD code;
    size_t index;
    const char *flags=" -fullscreen 0 -screen 800 600 -noaudio 1 -auth 127.0.0.1 -db 127.0.0.1 -quicklogin 0 -maxfps 10 -maxMenuFps 10 -maxInactiveFps 10 -stopinactivedisplay 0 -shader_init_logging 1 -nofilechangecheck 1 -physics 0 -verbose 1";
    if (argc!=4 || strlen(argv[1])!=32 || !quoted(executable,sizeof(executable),argv[2])) return 64;
    for(index=0; index<32; index++) if(!strchr("0123456789abcdef",argv[1][index])) return 64;
    if(strlen(executable)+strlen(flags)+1>sizeof(command)) return 64;
    strcpy(command, executable); strcat(command,flags);
    AllocConsole();
    if(GetConsoleWindow()) ShowWindow(GetConsoleWindow(),SW_HIDE);
    SetStdHandle(STD_INPUT_HANDLE,saved[0]); SetStdHandle(STD_OUTPUT_HANDLE,saved[1]); SetStdHandle(STD_ERROR_HANDLE,saved[2]);
    for(index=0; index<3; index++) {
        if(saved[index]==NULL || saved[index]==INVALID_HANDLE_VALUE ||
           !SetHandleInformation(saved[index],HANDLE_FLAG_INHERIT,HANDLE_FLAG_INHERIT)) return 65;
    }
    ZeroMemory(&si,sizeof(si)); ZeroMemory(&pi,sizeof(pi)); si.cb=sizeof(si);
    si.dwFlags=STARTF_USESTDHANDLES;
    si.hStdInput=saved[0]; si.hStdOutput=saved[1]; si.hStdError=saved[2];
    if(!CreateProcessA(argv[2],command,NULL,NULL,TRUE,0,NULL,argv[3],&si,&pi)) {
        snprintf(message,sizeof(message),"COH_CLIENT_LAUNCH_ERROR_V1 %lu\n",(unsigned long)GetLastError());
        output(saved[1],message); return 66;
    }
    snprintf(message,sizeof(message),"COH_CLIENT_LAUNCH_V1 {\"session_id\":\"%s\",\"pid\":%lu}\n",argv[1],(unsigned long)pi.dwProcessId);
    output(saved[1],message);
    CloseHandle(pi.hThread);
    if(WaitForSingleObject(pi.hProcess,20*60*1000)!=WAIT_OBJECT_0) { CloseHandle(pi.hProcess); return 67; }
    if(!GetExitCodeProcess(pi.hProcess,&code)) { CloseHandle(pi.hProcess); return 68; }
    CloseHandle(pi.hProcess);
    snprintf(message,sizeof(message),"COH_CLIENT_EXIT_V1 {\"session_id\":\"%s\",\"exit_code\":%lu}\n",argv[1],(unsigned long)code);
    output(saved[1],message);
    return (int)code;
}
