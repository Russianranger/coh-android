"""DbServer external map requests (database/external-maps), run natively.

wine_external_maps.c is compiled against a small POSIX stand-in for the Win32
calls it uses and run once per scenario (its mode is decided once per process):

- absent: ordinary Launcher behaviour (mode 0, nothing published);
- malformed or unsafe settings (wrong value, manual Atlas off, missing
  directory): mode -1, nothing published;
- on: the acknowledgement is printed once and each request is one complete
  JSON record, renamed into place (no .tmp left), with every string escaped
  (quotes, backslashes, control bytes) and a command that would overflow the
  record refused rather than truncated.
The patch is also applied to the reconstructed staged DbServer sources
(upstream plus the PostgreSQL, Wine ODBC and manual-Atlas layers).
"""
from pathlib import Path
import json
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OVERLAY = ROOT / 'database/external-maps/overlay/DBServer/src'
PATCH = ROOT / 'patches/external-maps/0001-external-map-requests.patch'
LAYERS = ('patches/postgresql/0001-dbserver-postgresql.patch', 'patches/wine-dbserver/0001-wine-odbc.patch',
          'patches/startup-dbserver/0001-manual-atlas-launcher-wait.patch')

SHIM = r'''
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
typedef unsigned long DWORD; typedef int BOOL; typedef void *HANDLE;
#define MAX_PATH 260
#define ERROR_SUCCESS 0
#define ERROR_ENVVAR_NOT_FOUND 203
#define ERROR_INVALID_PARAMETER 87
#define ERROR_INSUFFICIENT_BUFFER 122
#define ERROR_BUFFER_OVERFLOW 111
#define INVALID_FILE_ATTRIBUTES ((DWORD)-1)
#define FILE_ATTRIBUTE_DIRECTORY 0x10
#define FILE_ATTRIBUTE_REPARSE_POINT 0x400
#define FILE_ATTRIBUTE_NORMAL 0x80
#define GENERIC_WRITE 0x40000000
#define CREATE_ALWAYS 2
#define MOVEFILE_REPLACE_EXISTING 1
#define MOVEFILE_WRITE_THROUGH 8
#define INVALID_HANDLE_VALUE ((HANDLE)-1)
#define _snprintf snprintf
static DWORD last_error;
static void SetLastError(DWORD e) { last_error = e; }
static DWORD GetLastError(void) { return last_error; }
static DWORD GetEnvironmentVariableA(const char *n, char *b, DWORD s) {
    const char *v = getenv(n); size_t l;
    if (!v) { last_error = ERROR_ENVVAR_NOT_FOUND; return 0; }
    l = strlen(v); if (l + 1 > s) return (DWORD)(l + 1);
    memcpy(b, v, l + 1); return (DWORD)l; }
static void slashes(char *p) { for (; *p; p++) if (*p == '\\') *p = '/'; }
static DWORD GetFileAttributesA(const char *p) {
    char q[1024]; struct stat s; snprintf(q, sizeof(q), "%s", p); slashes(q);
    if (lstat(q, &s)) return INVALID_FILE_ATTRIBUTES;
    return (S_ISDIR(s.st_mode) ? FILE_ATTRIBUTE_DIRECTORY : 0) | (S_ISLNK(s.st_mode) ? FILE_ATTRIBUTE_REPARSE_POINT : 0); }
static HANDLE CreateFileA(const char *p, DWORD a, DWORD sh, void *sa, DWORD c, DWORD f, HANDLE t) {
    char q[1024]; FILE *file; (void)a; (void)sh; (void)sa; (void)c; (void)f; (void)t;
    snprintf(q, sizeof(q), "%s", p); slashes(q); file = fopen(q, "wb");
    return file ? (HANDLE)file : INVALID_HANDLE_VALUE; }
static BOOL WriteFile(HANDLE h, const void *b, DWORD n, DWORD *w, void *o) {
    (void)o; *w = (DWORD)fwrite(b, 1, n, (FILE *)h); return *w == n; }
static BOOL FlushFileBuffers(HANDLE h) { return fflush((FILE *)h) == 0; }
static BOOL CloseHandle(HANDLE h) { return fclose((FILE *)h) == 0; }
static BOOL MoveFileExA(const char *a, const char *b, DWORD f) {
    char p[1024], q[1024]; (void)f; snprintf(p, sizeof(p), "%s", a); snprintf(q, sizeof(q), "%s", b);
    slashes(p); slashes(q); return rename(p, q) == 0; }
static BOOL DeleteFileA(const char *a) { char p[1024]; snprintf(p, sizeof(p), "%s", a); slashes(p); return unlink(p) == 0; }
static DWORD GetCurrentProcessId(void) { return (DWORD)getpid(); }
'''

MAIN = r'''
int main(int argc, char **argv) {
    int mode = cohDbExternalMapsMode(), again = cohDbExternalMapsMode(), published = 0;
    static char long_command[5000];
    if (argc > 1 && !strcmp(argv[1], "publish")) {
        published = cohDbPublishMapRequest(5, 42, 0, 1, 0, 0, 0, "maps/City_Zones/City_01_02/City_01_02.txt",
            "", ".\\mapserver.exe -db 127.0.0.1 -udp -1 -map_id 5 -launcher -cookie 42 -locale 0");
        published += 10 * cohDbPublishMapRequest(915, 43, 0, 0, 1, 1, 1, "maps/Missions/Office/\"quoted\"\\path\t.txt",
            "M:1:2:3:\x01", "cmd");
        memset(long_command, 'x', sizeof(long_command) - 1);
        published += 100 * cohDbPublishMapRequest(916, 44, 0, 0, 0, 0, 0, "m", "", long_command);
    }
    printf("RESULT mode=%d again=%d published=%d\n", mode, again, published);
    return 0;
}
'''


def run(exe, environment, *arguments):
    result = subprocess.run([str(exe), *arguments], capture_output=True, text=True, env=environment, check=True)
    return result.stdout


def build(work):
    """POSIX: the overlay against the stand-in above. Windows (CI, inside vcvars32):
    the unchanged overlay against the real Win32 API with MSVC, as the DbServer builds it."""
    source = work / 'fixture.c'
    overlay = (OVERLAY / 'wine_external_maps.c').read_text()
    if os.name == 'nt':
        source.write_text(overlay + '\n#include <stdlib.h>\n' + MAIN)
        exe = work / 'fixture.exe'
        subprocess.run(['cl', '/nologo', '/W3', '/WX', '/wd4996', '/I', str(OVERLAY), str(source),
                        '/Fe' + str(exe)], check=True, cwd=work)
        return exe
    source.write_text(SHIM + '#include "wine_external_maps.h"\n' + overlay.replace('#include <windows.h>\n', '') + MAIN)
    exe = work / 'fixture'
    subprocess.run(['cc', '-std=gnu11', '-O1', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                    '-I', str(OVERLAY), str(source), '-o', str(exe)], check=True)
    return exe


def main():
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        exe = build(work)
        requests = work / 'requests'
        requests.mkdir()
        base = {'PATH': os.environ.get('PATH', '/usr/bin:/bin')}
        if os.name == 'nt':
            base.update({name: os.environ[name] for name in ('SYSTEMROOT', 'TEMP', 'TMP') if name in os.environ})
        on = dict(base, COH_WINE_DB_EXTERNAL_MAPS='1', COH_WINE_DB_MANUAL_ATLAS='1',
                  COH_WINE_DB_EXTERNAL_MAPS_DIR=str(requests))
        cases = {
            'absent': (base, 'mode=0 again=0 published=0'),
            'wrong value': (dict(on, COH_WINE_DB_EXTERNAL_MAPS='2'), 'mode=-1 again=-1 published=0'),
            'manual Atlas off': ({k: v for k, v in on.items() if k != 'COH_WINE_DB_MANUAL_ATLAS'},
                                 'mode=-1 again=-1 published=0'),
            'missing directory': (dict(on, COH_WINE_DB_EXTERNAL_MAPS_DIR=str(work / 'absent')),
                                  'mode=-1 again=-1 published=0'),
        }
        for name, (environment, expected) in cases.items():
            output = run(exe, environment, 'publish')
            assert ('RESULT ' + expected) in output, (name, output)
            assert not list(requests.iterdir()), (name, 'published while not on')
        output = run(exe, on, 'publish')
        # Requests 1 and 2 succeed; the overflowing command (third) is refused.
        assert 'RESULT mode=1 again=1 published=11' in output, output
        assert output.count('COH_WINE_DB_EXTERNAL_MAPS=1 active') == 1, output
        assert 'COH_WINE_DB_EXTERNAL_MAP_REQUEST_V1 map_id=5 cookie=42 static=1' in output, output
        names = sorted(path.name for path in requests.iterdir())
        assert names == ['map-5-42.json', 'map-915-43.json'], names
        zone = json.loads((requests / 'map-5-42.json').read_text())
        assert zone == {'format': 1, 'sequence': 1, 'map_id': 5, 'cookie': 42, 'base_map_id': 0, 'is_static': 1,
                        'transient': 0, 'dont_auto_start': 0, 'preload_transient': 0, 'db_process_id': zone['db_process_id'],
                        'map_name': 'maps/City_Zones/City_01_02/City_01_02.txt', 'mission_info': '',
                        'command': '.\\mapserver.exe -db 127.0.0.1 -udp -1 -map_id 5 -launcher -cookie 42 -locale 0'}, zone
        mission = json.loads((requests / 'map-915-43.json').read_text())
        assert mission['map_name'] == 'maps/Missions/Office/"quoted"\\path\t.txt' and mission['mission_info'] == 'M:1:2:3:\x01'
        assert (mission['is_static'], mission['transient'], mission['dont_auto_start'], mission['preload_transient'],
                mission['sequence']) == (0, 1, 1, 1, 2), mission
        # The patch applies to the staged DbServer sources it was written against.
        staged = work / 'staged'
        upstream = ROOT / 'upstream/ouroboros'
        for name in ('DBServer/CMakeLists.txt', 'DBServer/src/launchercomm.c', 'DBServer/src/mapxfer.c'):
            (staged / name).parent.mkdir(parents=True, exist_ok=True)
            (staged / name).write_bytes((upstream / name).read_bytes())
        def lf(path):   # Windows checkouts may hold the patches with CRLF
            return path.read_bytes().replace(b'\r\n', b'\n')
        git = ['git', '-c', 'core.autocrlf=false', 'apply']
        for layer in LAYERS:
            subprocess.run(git + ['--include=DBServer/CMakeLists.txt', '-'], input=lf(ROOT / layer), cwd=staged, check=True)
        subprocess.run(git + ['--check', '-'], input=lf(PATCH), cwd=staged, check=True)
        print('PASS: external map requests (' + ('MSVC, Win32' if os.name == 'nt' else 'POSIX stand-in')
              + '): 5 modes, escaped JSON records, overflow refused, patch applies to the staged sources')


if __name__ == '__main__':
    main()
