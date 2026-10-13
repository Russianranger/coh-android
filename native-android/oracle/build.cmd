@echo off
setlocal
rem Run from any directory. Requires Visual Studio C++ x86 build tools.
for %%I in ("%~dp0..\..") do set "COH_ORACLE_ROOT=%%~fI"
set "COH_ORACLE_OUT=%COH_ORACLE_ROOT%\native-android\results\original-oracle"
if not "%~1"=="" set "COH_ORACLE_OUT=%~f1"
set "COH_ORACLE_VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%COH_ORACLE_VSWHERE%" exit /b 2
for /f "usebackq tokens=*" %%I in (`"%COH_ORACLE_VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "COH_ORACLE_VS=%%I"
if not defined COH_ORACLE_VS exit /b 3
call "%COH_ORACLE_VS%\VC\Auxiliary\Build\vcvars32.bat"
if errorlevel 1 exit /b 4
if not exist "%COH_ORACLE_OUT%" mkdir "%COH_ORACLE_OUT%"
if errorlevel 1 exit /b 5
python "%COH_ORACLE_ROOT%\native-android\oracle\verify_inputs.py"
if errorlevel 1 exit /b 6
cl /nologo /std:c++14 /W4 /WX /O2 /MT /EHsc /D_CRT_SECURE_NO_WARNINGS "%COH_ORACLE_ROOT%\native-android\oracle\nvdxt_reference.cpp" /Fo:"%COH_ORACLE_OUT%\nvdxt-reference.obj" /Fe:"%COH_ORACLE_OUT%\nvdxt-reference.exe" /link /MACHINE:X86 /OPT:REF /INCREMENTAL:NO "%COH_ORACLE_ROOT%\upstream\ouroboros\3rdparty\nvdxt\Release\nvDXTlibMT_S.lib" legacy_stdio_definitions.lib
if errorlevel 1 exit /b 7
dumpbin /headers /imports "%COH_ORACLE_OUT%\nvdxt-reference.exe" > "%COH_ORACLE_OUT%\pe-headers-imports.txt"
if errorlevel 1 exit /b 8
python "%COH_ORACLE_ROOT%\native-android\oracle\verify_inputs.py" --executable "%COH_ORACLE_OUT%\nvdxt-reference.exe" --receipt "%COH_ORACLE_OUT%\build-receipt.json"
if errorlevel 1 exit /b 9
exit /b 0
