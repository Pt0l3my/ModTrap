/* ModTrap's launcher for Windows (MT51).

   Starts Python with ModTrap ("-m modtrap") in a console of its own, hidden (MT63), and hands on whatever was given
   on its own command line. It has no window itself. ModTrap lies in the "app" folder beside this program.

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
static wchar_t title[] = L"ModTrap";

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

static int say(const wchar_t *text)
{
    MessageBoxW(NULL, text, L"ModTrap", MB_OK | MB_ICONERROR);
    return 2;
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR line, int show)
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
    if (wcslen(python) + wcslen(EXTRA_ARGS) + wcslen(rest) + 64 > LONGEST) return say(L"The command line is too long.");
    /* Started plainly, the console made below is ModTrap's own, and ModTrap is told so: it may then hide it or show it. */
    _snwprintf(command, LONGEST, L"\"%ls\"%ls -m modtrap%ls%ls%ls%ls", python, first, EXTRA_ARGS, *rest ? L"" : L" --own-console", *rest ? L" " : L"", rest);
    command[LONGEST] = 0;

    (void)instance; (void)previous; (void)line; (void)show;

    /* Python gets a console of its own, where ModTrap writes what it does; it starts hidden, since the same lines
       are on ModTrap's page (History, Log) and nothing needs the window (MT63). The console itself has to be there:
       the console programs ModTrap starts write to it, and would each open a window of their own without it.
       ModTrap shows it, minimised, where its setting says so, and shows it when its start fails. Started with
       words on the command line, the console is shown, for whoever asked to read the answer. */
    ZeroMemory(&si, sizeof si);
    si.cb = sizeof si;
    si.lpTitle = title;
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = (WORD)(*rest ? SW_SHOWNORMAL : SW_HIDE);
    ZeroMemory(&pi, sizeof pi);
    if (!CreateProcessW(python, command, NULL, NULL, FALSE, CREATE_NEW_CONSOLE, NULL, NULL, &si, &pi))
        return say(L"Python could not be started.");
    /* Should it end at once with an error, nobody would see why in a hidden console: say so. (ModTrap itself shows
       the console and waits for a key where its start fails; this is for a Python that does not get that far.) */
    if (WaitForSingleObject(pi.hProcess, 4000) == WAIT_OBJECT_0) {
        GetExitCodeProcess(pi.hProcess, &result);
        if (result != 0 && !*rest)
            say(L"ModTrap ended right after it started.\n\nIf it was already running in the middle of a job, its page is open in your browser: let the job end there.\n\nOtherwise start ModTrap.cmd, in the same folder, to read what it says.");
    } else {
        result = 0;
    }
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return (int)result;
}
