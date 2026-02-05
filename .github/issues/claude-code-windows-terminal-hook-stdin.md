# Bug Report: SessionStart hooks break stdin on Windows Terminal

## Preflight Checklist
- [x] I have searched existing issues and this hasn't been reported yet
- [x] This is a single bug report (please file separate reports for different bugs)
- [x] I am using the latest version of Claude Code

## What's Wrong?

When using SessionStart hooks on Windows with Windows Terminal, stdin becomes completely unresponsive after the hook executes. The hook completes successfully (debug logs show "Successfully parsed and validated hook JSON output" and "[REPL:mount] REPL mounted, disabled=false"), but the user cannot type any input. The cursor appears but keystrokes are not registered.

This affects ANY hook command, even the most minimal `cmd /c echo {}`.

## What Should Happen?

After the hook completes successfully, stdin should work normally and the user should be able to type prompts in the REPL.

## Steps to Reproduce

1. Create a project directory with a `.claude/settings.json` file containing:
```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "cmd /c echo {}"
          }
        ]
      }
    ]
  }
}
```

2. Open **Windows Terminal** (not WezTerm or other terminals)
3. Navigate to the project directory
4. Run `claude --debug`
5. Observe that:
   - Claude Code starts normally
   - The hook executes successfully (visible in debug log)
   - The prompt appears with "Try 'fix typecheck errors'" suggestion
   - **You cannot type anything** - stdin is completely blocked

## Is this a regression?

I don't know

## Claude Code Version

2.1.31

## Platform

Anthropic API

## Operating System

Windows

## Terminal/Shell

Windows Terminal (PowerShell)

## Error Messages/Logs

Debug log shows everything completing successfully:
```
2026-02-04T14:35:02.486Z [DEBUG] Successfully parsed and validated hook JSON output
2026-02-04T14:35:02.487Z [DEBUG] Hook SessionStart:startup (SessionStart) success: {}
2026-02-04T14:35:03.433Z [DEBUG] [REPL:mount] REPL mounted, disabled=false
2026-02-04T14:35:03.627Z [DEBUG] [render] first ink render: 2264ms since process start
```

No errors in the log - everything appears successful, yet stdin is broken.

## Claude Model

Opus 4.5

## Additional Information

### Key findings from investigation:

1. **Affects ANY subprocess**: Even `cmd /c echo {}` causes the issue - not specific to Python or complex hooks
2. **Windows Terminal specific**: WezTerm works correctly with the exact same hooks
3. **Other projects work**: Windows Terminal works fine in projects without hooks configured
4. **Hook output is valid**: JSON is correctly parsed, no errors in processing

### Workaround

Use WezTerm instead of Windows Terminal when working with projects that have SessionStart hooks.

### Possibly related issues

- #12507 - stdin consumed by shell detection subprocesses (similar stdin inheritance pattern)
- #22172 - CPU hang with parallel instances and hooks (v2.1.23+ regression)

### Possible cause

The hook subprocess may be inheriting stdin handles in a way that doesn't get properly restored on Windows Terminal specifically. This could be related to how Windows Terminal handles ConPTY vs how other terminals (WezTerm) handle terminal I/O.
