/* ModTrap's launcher for Windows (MT51).

   Starts Python with ModTrap ("-m modtrap"), hands on whatever was given on its own command line, waits for it, and
   ends with its result. ModTrap lies in the "app" folder beside this program.

   Which Python: the one in a "python" folder beside this program, where the package has one (it finds ModTrap
   through python\python313._pth and takes nothing else of the PC into its path); else the Python installed on the
   PC, found as Windows finds programs: the "py" launcher first, then "python". Nothing on the PC is changed.

   Built with EXTRA_ARGS set to ModTrap's switch for changes: ModTrap.exe is the one program, able to do all of
   ModTrap's work. Built plain, it would start ModTrap as its command line does without the switch. */

#define WIN32_LEAN_AND_MEAN
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#include <windows.h>
#include <wchar.h>

#ifndef EXTRA_ARGS
#define EXTRA_ARGS L""
#endif

#define LONGEST 32767                        /* the longest command line Windows takes */

static wchar_t dir[LONGEST + 1];
static wchar_t python[LONGEST + 64];
static wchar_t app[LONGEST + 64];
static wchar_t command[LONGEST + 1];

/* What followed this program's own name on its command line, as it was typed. */
static const wchar_t *rest_of_command_line(void)
{
    const wchar_t *p = GetCommandLineW();
    if (*p == L'"') {
        p++;
        while (*p && *p != L'"') p++;
        if (*p) p++;
    } else {
        while (*p && *p != L' ' && *p != L'\t') p++;
    }
    while (*p == L' ' || *p == L'\t') p++;
    return p;
}

/* Ctrl+C in the console is Python's to act on; this program only waits. */
static BOOL WINAPI on_console_event(DWORD kind)
{
    return kind == CTRL_C_EVENT || kind == CTRL_BREAK_EVENT;
}

static int say(const wchar_t *text)
{
    MessageBoxW(NULL, text, L"ModTrap", MB_OK | MB_ICONERROR);
    return 2;
}

int wmain(void)
{
    DWORD n = GetModuleFileNameW(NULL, dir, LONGEST);
    wchar_t *slash;
    const wchar_t *rest;
    const wchar_t *first;
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    DWORD result = 1;

    if (n == 0 || n >= LONGEST) return say(L"ModTrap could not tell which folder it is in.");
    slash = wcsrchr(dir, L'\\');
    if (slash == NULL) return say(L"ModTrap could not tell which folder it is in.");
    *slash = 0;

    if (_snwprintf(app, LONGEST + 63, L"%ls\\app", dir) < 0 || _snwprintf(python, LONGEST + 63, L"%ls\\python\\python.exe", dir) < 0)
        return say(L"The folder ModTrap is in has too long a path.");
    if (GetFileAttributesW(app) == INVALID_FILE_ATTRIBUTES)
        return say(L"The \"app\" folder that belongs beside ModTrap.exe is not there.\n\nUnpack the whole ModTrap folder and start ModTrap.exe from inside it.");

    rest = rest_of_command_line();
    if (GetFileAttributesW(python) != INVALID_FILE_ATTRIBUTES) {
        /* The package's own Python. */
        first = L"";
    } else {
        /* The Python installed on this PC: it is told where ModTrap lies. */
        SetEnvironmentVariableW(L"PYTHONPATH", app);
        if (SearchPathW(NULL, L"py.exe", NULL, LONGEST, python, NULL) != 0) {
            first = L" -3";
        } else if (SearchPathW(NULL, L"python.exe", NULL, LONGEST, python, NULL) != 0) {
            first = L"";
        } else {
            return say(L"ModTrap needs Python 3.10 or newer, and found none on this PC.\n\nInstall Python from python.org (tick \"Add python.exe to PATH\"), then start ModTrap again.");
        }
    }
    if (wcslen(python) + wcslen(EXTRA_ARGS) + wcslen(rest) + 40 > LONGEST) return say(L"The command line is too long.");
    _snwprintf(command, LONGEST, L"\"%ls\"%ls -m modtrap%ls%ls%ls", python, first, EXTRA_ARGS, *rest ? L" " : L"", rest);
    command[LONGEST] = 0;

    SetConsoleCtrlHandler(on_console_event, TRUE);
    ZeroMemory(&si, sizeof si);
    si.cb = sizeof si;
    ZeroMemory(&pi, sizeof pi);
    if (!CreateProcessW(python, command, NULL, NULL, TRUE, 0, NULL, NULL, &si, &pi))
        return say(L"Python could not be started.");
    WaitForSingleObject(pi.hProcess, INFINITE);
    GetExitCodeProcess(pi.hProcess, &result);
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return (int)result;
}
