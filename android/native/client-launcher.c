/* Observe the unmodified CoH GUI client through its own hidden console. */
#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0601
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static void output(HANDLE handle, const char *text) {
    size_t remaining=strlen(text);
    while(remaining) {
        DWORD written=0;
        if(!WriteFile(handle,text,(DWORD)remaining,&written,NULL) || !written) return;
        text+=written; remaining-=written;
    }
}
#define CONSOLE_COLUMNS 256
#define CONSOLE_ROWS 128
#define CONSOLE_CHARS (CONSOLE_COLUMNS * CONSOLE_ROWS)
#define CONSOLE_NORMALIZED (CONSOLE_CHARS + CONSOLE_ROWS)
#define CONSOLE_TEXT (CONSOLE_NORMALIZED * 4 + 1)
#define CONSOLE_BUDGET (8 * 1024 * 1024)
static WCHAR console_wide[CONSOLE_CHARS];
static WCHAR normalized_wide[CONSOLE_NORMALIZED];
static char console_text[CONSOLE_TEXT], previous_text[CONSOLE_TEXT];
static size_t emitted_console;
static int console_budget_reported;
static DWORD owned_pid;

static BOOL CALLBACK position_owned_window(HWND window, LPARAM unused) {
    DWORD pid=0;
    char name[64];
    RECT rect;
    (void)unused;
    GetWindowThreadProcessId(window,&pid);
    if(pid!=owned_pid || !GetClassNameA(window,name,sizeof(name)) || strcmp(name,"CrypticWindow")) return TRUE;
    if(GetWindowRect(window,&rect) && (rect.left || rect.top || rect.right!=800 || rect.bottom!=600))
        SetWindowPos(window,NULL,0,0,800,600,SWP_NOZORDER|SWP_NOACTIVATE|SWP_ASYNCWINDOWPOS);
    return TRUE;
}

static void console_capture(HANDLE screen, HANDLE pipe) {
    CONSOLE_SCREEN_BUFFER_INFO info;
    COORD origin;
    DWORD count=0;
    size_t rows,width,row,column,used=0,prefix=0,start=0,old_len;
    int converted;
    if(console_budget_reported || !GetConsoleScreenBufferInfo(screen,&info)) return;
    if(info.dwSize.X<=0 || info.dwSize.X>CONSOLE_COLUMNS || info.dwCursorPosition.Y<0) return;
    width=(size_t)info.dwSize.X;
    rows=(size_t)info.dwCursorPosition.Y+1;
    if(rows>CONSOLE_ROWS) rows=CONSOLE_ROWS;
    origin.X=0; origin.Y=(SHORT)(info.dwCursorPosition.Y+1-(SHORT)rows);
    if(!ReadConsoleOutputCharacterW(screen,console_wide,(DWORD)(rows*width),origin,&count) || count!=rows*width) return;
    /* Keep input separate: a full-width row needs an extra output newline. */
    for(row=0; row<rows; row++) {
        size_t end=width;
        while(end && (console_wide[row*width+end-1]==' ' || console_wide[row*width+end-1]==0)) end--;
        if(used+end+1>CONSOLE_NORMALIZED) return;
        for(column=0;column<end;column++) normalized_wide[used++]=console_wide[row*width+column];
        normalized_wide[used++]='\n';
    }
    while(used && normalized_wide[used-1]=='\n') used--;
    if(!used) return;
    if(used+1>CONSOLE_NORMALIZED) return;
    normalized_wide[used++]='\n';
    converted=WideCharToMultiByte(CP_UTF8,0,normalized_wide,(int)used,console_text,CONSOLE_TEXT-1,NULL,NULL);
    if(converted<=0) return;
    console_text[converted]=0;
    if(!strcmp(console_text,previous_text)) return;
    old_len=strlen(previous_text);
    while(prefix<old_len && prefix<(size_t)converted && previous_text[prefix]==console_text[prefix]) prefix++;
    if(prefix==old_len) start=prefix;
    else if(prefix) {
        start=prefix;
        while(start && console_text[start-1]!='\n') start--;
    } else {
        /* Scrolling drops old rows: retain the largest previous suffix still visible. */
        size_t candidate;
        for(candidate=0;candidate<old_len;candidate++) {
            size_t overlap=old_len-candidate;
            if(candidate && previous_text[candidate-1]!='\n') continue;
            if(overlap<=(size_t)converted && !memcmp(previous_text+candidate,console_text,overlap)) {
                start=overlap; break;
            }
        }
    }
    if(emitted_console+(size_t)converted-start>CONSOLE_BUDGET) {
        output(pipe,"COH_CLIENT_CONSOLE_TRUNCATED_V1 budget_exhausted\n");
        console_budget_reported=1;
        return;
    }
    output(pipe,console_text+start);
    emitted_console+=(size_t)converted-start;
    memcpy(previous_text,console_text,(size_t)converted+1);
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
    HANDLE pipe=NULL, screen=INVALID_HANDLE_VALUE;
    ULONGLONG deadline;
    int attached=0, generate=argc==5 && !strcmp(argv[4],"--generate-caches");
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    char command[4096], executable[2048], message[512];
    DWORD code;
    size_t index;
    const char *flags=generate ? " -createbins -nogui 1 -console 1 -noaudio 1 -verbose 1 -physics 0" :
        " -fullscreen 1 -screen 800 600 -noaudio 1 -auth 127.0.0.1 -db 127.0.0.1 -quicklogin 0 -maxfps 10 -maxMenuFps 10 -maxInactiveFps 10 -stopinactivedisplay 0 -shader_init_logging 1 -nofilechangecheck 1 -physics 0 -verbose 1";
    if ((argc!=4 && !generate) || strlen(argv[1])!=32 || !quoted(executable,sizeof(executable),argv[2])) return 64;
    for(index=0; index<32; index++) if(!strchr("0123456789abcdef",argv[1][index])) return 64;
    if(strlen(executable)+strlen(flags)+1>sizeof(command)) return 64;
    strcpy(command, executable); strcat(command,flags);
    if(!DuplicateHandle(GetCurrentProcess(),saved[1],GetCurrentProcess(),&pipe,0,FALSE,DUPLICATE_SAME_ACCESS)) return 69;
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
        output(pipe,message); return 66;
    }
    snprintf(message,sizeof(message),"COH_CLIENT_LAUNCH_V1 {\"session_id\":\"%s\",\"pid\":%lu}\n",argv[1],(unsigned long)pi.dwProcessId);
    output(pipe,message);
    CloseHandle(pi.hThread);
    owned_pid=pi.dwProcessId;
    /* A GUI child starts detached from its parent's console. Once its own
       AllocConsole/freopen runs, attach and read the actual screen buffer. */
    FreeConsole();
    deadline=GetTickCount64()+20*60*1000;
    while(WaitForSingleObject(pi.hProcess,500)==WAIT_TIMEOUT) {
        if(GetTickCount64()>=deadline) { CloseHandle(pi.hProcess); CloseHandle(pipe); return 67; }
        if(!attached && AttachConsole(pi.dwProcessId)) {
            DWORD ids[32],number,j;
            int owned=0;
            number=GetConsoleProcessList(ids,32);
            if(number && number<=32) for(j=0;j<number;j++) if(ids[j]==pi.dwProcessId) owned=1;
            if(!owned) { FreeConsole(); continue; }
            screen=CreateFileA("CONOUT$",GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE,NULL,OPEN_EXISTING,0,NULL);
            if(screen==INVALID_HANDLE_VALUE) { FreeConsole(); continue; }
            attached=1;
            if(GetConsoleWindow()) ShowWindowAsync(GetConsoleWindow(),SW_HIDE);
            snprintf(message,sizeof(message),"COH_CLIENT_CONSOLE_V1 {\"session_id\":\"%s\",\"pid\":%lu,\"attached\":true}\n",argv[1],(unsigned long)pi.dwProcessId);
            output(pipe,message);
        }
        if(attached) console_capture(screen,pipe);
        if(!generate) EnumWindows(position_owned_window,0);
    }
    if(attached) { console_capture(screen,pipe); CloseHandle(screen); FreeConsole(); }
    if(!GetExitCodeProcess(pi.hProcess,&code)) { CloseHandle(pi.hProcess); return 68; }
    CloseHandle(pi.hProcess);
    snprintf(message,sizeof(message),"COH_CLIENT_EXIT_V1 {\"session_id\":\"%s\",\"exit_code\":%lu}\n",argv[1],(unsigned long)code);
    output(pipe,message);
    CloseHandle(pipe);
    return (int)code;
}
