#include "wininclude.h"

C_DECLARATIONS_BEGIN

// Helper function to align all of the elements in a dialog.
// Call once with the initial width and heigh, and then after that
//  call it with the new width/height (from WM_SIZE), and an ID of two controls:
//        idAlignMe:    Everything to the right of the left of this control will translate horizontally upon resize
//                    Everything below the top of this control will translate vertically upon resize
//        idUpperLeft:    Everything whose top aligns with the top of this control will stretch vertically upon resize
//                        Everything whose left aligns with the left of this control will stretch horizontally upon resize
void doDialogOnResize(HWND hDlg, WORD w, WORD h, int idAlignMe, int idUpperLeft);
void setDialogMinSize(HWND hDlg, WORD minw, WORD minh);

int NumLines(LPSTR text);
int LongestWord(LPSTR text); 
void OffsetWindow(HWND hDlg, HWND hWnd, int xdelta, int ydelta);

void errorDialog(HWND hwnd, char *str, char* title, char* fault, int highlight); // title & fault optional
void msgAlert(HWND hwnd, char *str);

/* Outputs a character to a bitmap in memory and returns a Windows-compatible icon.
   This generally appears to be a black square with a colored letter overlaid in the center.

 * @return A pointer to an icon in memory with a resolution of `sizeX` * `sizeY`.

 * @param letter A Unicode/UTF-16 character (ranges well beyond -127 through 127 for a typical character type) to write to the bitmap.
 * @param colorRGB Font color to use; for a human-readable format this can be sent as a hex number (i.e. 0xFFFFFF).
 * @param sizeX The bitmap width.
 * @param sizeY The bitmap height.
*/
HICON getIconColoredLetter(wchar_t letter, U32 colorRGB, U32 sizeX, U32 sizeY);

/* Generates two icons (16x16 and 64x64) to use during the application's lifetime.

 * @param letter A Unicode/UTF-16 character (ranges well beyond -127 through 127 for a typical character type) to write to the bitmap.
 * @param colorRGB Font color to use; for a human-readable format this can be sent as a hex number (i.e. 0xFFFFFF).
*/
void setWindowIconColoredLetter(HWND hwnd, wchar_t letter, U32 colorRGB);

char* getIconColoredLetterBytes(int letter, U32 colorRGB); // returns an achr array

void winRegisterMe(const char *command, const char *extension); // Registers the current executable to handle files of the given extension
char *winGetFileName_s(HWND hwnd, const char *fileMask, char *fileName, size_t fileName_size, bool save);

void winSetHInstance(HINSTANCE hInstance);
HINSTANCE winGetHInstance(void);

void winAddToPath(const char *path, int prefix);
bool winExistsInRegPath(const char *path);
bool winExistsInEnvPath(const char *path);

char *winGetLastErrorStr();
bool winCreateProcess(char *command_line, PROCESS_INFORMATION *res_pi);
bool winProcessRunning(PROCESS_INFORMATION *pi);
bool winProcessExitCode(PROCESS_INFORMATION *pi, U32 *res_exit);

C_DECLARATIONS_END
