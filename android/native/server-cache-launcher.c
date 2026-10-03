/* Bound an unchanged MapServer TSR preload and send Escape to its owned console.
   The host requests normal exit only after its fresh completed-preload record. */
#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0601
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void output(HANDLE pipe, const char *text) {
    size_t size = strlen(text);
    while(size) {
        DWORD written = 0;
        if(!WriteFile(pipe, text, (DWORD)size, &written, NULL) || !written) return;
        text += written; size -= written;
    }
}

static int quote(char *destination, size_t limit, const char *source) {
    size_t used=0, slashes=0;
    if(limit<3) return 0;
    destination[used++]='"';
    while(*source) {
        if(*source=='\\') { slashes++; source++; continue; }
        if(*source=='"') {
            if(used+slashes*2+2>=limit) return 0;
            while(slashes) { destination[used++]='\\'; destination[used++]='\\'; slashes--; }
            destination[used++]='\\'; destination[used++]=*source++;
        } else {
            if(used+slashes+1>=limit) return 0;
            while(slashes) { destination[used++]='\\'; slashes--; }
            destination[used++]=*source++;
        }
    }
    if(used+slashes*2+2>limit) return 0;
    while(slashes) { destination[used++]='\\'; destination[used++]='\\'; slashes--; }
    destination[used++]='"'; destination[used]=0;
    return 1;
}

static int exit_requested(const char *path, const char *session) {
    char bytes[34];
    DWORD attributes=GetFileAttributesA(path), read=0;
    HANDLE file;
    if(attributes==INVALID_FILE_ATTRIBUTES) return 0;
    if(attributes & (FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT)) return -1;
    file=CreateFileA(path,GENERIC_READ,FILE_SHARE_READ,NULL,OPEN_EXISTING,0,NULL);
    if(file==INVALID_HANDLE_VALUE) return -1;
    if(!ReadFile(file,bytes,sizeof(bytes),&read,NULL)) { CloseHandle(file); return -1; }
    CloseHandle(file);
    return read==33 && !memcmp(bytes,session,32) && bytes[32]=='\n' ? 1 : -1;
}

static int owned_console(DWORD pid) {
    DWORD processes[32], count=GetConsoleProcessList(processes,32), index;
    if(!count || count>32) return 0;
    for(index=0;index<count;index++) if(processes[index]==pid) return 1;
    return 0;
}

int main(int argc, char **argv) {
    HANDLE saved[3]={GetStdHandle(STD_INPUT_HANDLE),GetStdHandle(STD_OUTPUT_HANDLE),GetStdHandle(STD_ERROR_HANDLE)};
    HANDLE pipe=NULL, input=INVALID_HANDLE_VALUE;
    STARTUPINFOA startup;
    PROCESS_INFORMATION child;
    char executable[2048], command[4096], event[512], *end;
    DWORD index, code;
    ULONGLONG deadline;
    unsigned long seconds;
    int attached=0, escaped=0, requested;
    /* Without -nogui, existing newConsoleWindow makes inherited stdout/stderr
       unbuffered even when AllocConsole finds this already-created console.
       TSR2 suppresses data-error dialogs; STDERR|EXIT asserts remain bounded. */
    const char *flags=" -nosharedmemory -tsr2 -assertmode 8256";
    if(argc!=6 || strlen(argv[1])!=32 || !quote(executable,sizeof(executable),argv[2])) return 64;
    for(index=0;index<32;index++) if(!strchr("0123456789abcdef",argv[1][index])) return 64;
    seconds=strtoul(argv[5],&end,10);
    if(*end || seconds<30 || seconds>3600 || strlen(executable)+strlen(flags)+1>sizeof(command)) return 64;
    strcpy(command,executable); strcat(command,flags);
    if(!DuplicateHandle(GetCurrentProcess(),saved[1],GetCurrentProcess(),&pipe,0,FALSE,DUPLICATE_SAME_ACCESS)) return 65;
    for(index=0;index<3;index++) if(saved[index]==NULL || saved[index]==INVALID_HANDLE_VALUE ||
        !SetHandleInformation(saved[index],HANDLE_FLAG_INHERIT,HANDLE_FLAG_INHERIT)) return 65;
    FreeConsole();
    ZeroMemory(&startup,sizeof(startup)); ZeroMemory(&child,sizeof(child)); startup.cb=sizeof(startup);
    startup.dwFlags=STARTF_USESTDHANDLES; startup.hStdInput=saved[0]; startup.hStdOutput=saved[1]; startup.hStdError=saved[2];
    if(!CreateProcessA(argv[2],command,NULL,NULL,TRUE,CREATE_NEW_CONSOLE,NULL,argv[3],&startup,&child)) {
        snprintf(event,sizeof(event),"COH_SERVER_CACHE_LAUNCH_ERROR_V1 %lu\n",(unsigned long)GetLastError());
        output(pipe,event); CloseHandle(pipe); return 66;
    }
    CloseHandle(child.hThread);
    snprintf(event,sizeof(event),"COH_SERVER_CACHE_LAUNCH_V1 {\"session_id\":\"%s\",\"pid\":%lu}\n",argv[1],(unsigned long)child.dwProcessId);
    output(pipe,event);
    deadline=GetTickCount64()+(ULONGLONG)seconds*1000;
    while(WaitForSingleObject(child.hProcess,100)==WAIT_TIMEOUT) {
        if(GetTickCount64()>=deadline) {
            output(pipe,"COH_SERVER_CACHE_TIMEOUT_V1\n");
            /* Failure cleanup only; a timeout can never be a generation pass. */
            TerminateProcess(child.hProcess,67); WaitForSingleObject(child.hProcess,5000);
            CloseHandle(child.hProcess); CloseHandle(pipe); return 67;
        }
        if(!attached && AttachConsole(child.dwProcessId)) {
            if(!owned_console(child.dwProcessId)) { FreeConsole(); continue; }
            input=CreateFileA("CONIN$",GENERIC_READ|GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,NULL,OPEN_EXISTING,0,NULL);
            if(input==INVALID_HANDLE_VALUE) { FreeConsole(); continue; }
            attached=1;
            if(GetConsoleWindow()) ShowWindowAsync(GetConsoleWindow(),SW_HIDE);
            snprintf(event,sizeof(event),"COH_SERVER_CACHE_CONSOLE_V1 {\"session_id\":\"%s\",\"pid\":%lu,\"owned\":true}\n",argv[1],(unsigned long)child.dwProcessId);
            output(pipe,event);
        }
        requested=exit_requested(argv[4],argv[1]);
        if(requested<0) { output(pipe,"COH_SERVER_CACHE_STOP_REFUSED_V1\n"); TerminateProcess(child.hProcess,68); CloseHandle(child.hProcess); CloseHandle(pipe); return 68; }
        if(requested && attached && !escaped) {
            INPUT_RECORD records[2]; DWORD written=0;
            if(!owned_console(child.dwProcessId)) return 69;
            ZeroMemory(records,sizeof(records));
            records[0].EventType=records[1].EventType=KEY_EVENT;
            records[0].Event.KeyEvent.bKeyDown=TRUE;
            records[0].Event.KeyEvent.wRepeatCount=records[1].Event.KeyEvent.wRepeatCount=1;
            records[0].Event.KeyEvent.wVirtualKeyCode=records[1].Event.KeyEvent.wVirtualKeyCode=VK_ESCAPE;
            records[0].Event.KeyEvent.uChar.UnicodeChar=records[1].Event.KeyEvent.uChar.UnicodeChar=27;
            if(!WriteConsoleInputW(input,records,2,&written) || written!=2) return 69;
            escaped=1;
            snprintf(event,sizeof(event),"COH_SERVER_CACHE_ESCAPE_V1 {\"session_id\":\"%s\",\"pid\":%lu,\"sent\":true}\n",argv[1],(unsigned long)child.dwProcessId);
            output(pipe,event);
        }
    }
    if(!GetExitCodeProcess(child.hProcess,&code)) return 70;
    if(attached) { CloseHandle(input); FreeConsole(); }
    CloseHandle(child.hProcess);
    snprintf(event,sizeof(event),"COH_SERVER_CACHE_EXIT_V1 {\"session_id\":\"%s\",\"pid\":%lu,\"exit_code\":%lu,\"escape_sent\":%s}\n",argv[1],(unsigned long)child.dwProcessId,(unsigned long)code,escaped ? "true" : "false");
    output(pipe,event); CloseHandle(pipe);
    return code==0 && escaped ? 0 : 71;
}
