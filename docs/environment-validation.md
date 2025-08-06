# Environment-Aware Validation (Phase 1)

CommandRex validates every command against your current OS and shell to prevent common cross-environment mistakes (e.g., using `ls` in CMD, wrong path separators, PowerShell syntax in Bash). This document explains how it works and how to control it.

What you get
- Safer defaults: incompatible commands are blocked before you see or run them.
- Clear guidance: when strict blocking is turned off, you get concise reasons and hints.
- Simple control: a single CLI flag lets you relax validation per call/session.

Core behavior
- Post-generation validation: the translator rejects incompatible commands before they are shown.
- Pre-execution validation: the executor blocks incompatible commands before they run.
- Validation checks include:
  - Shell-specific forbidden tokens (e.g., Unix tools in Windows shells).
  - Wrong path separators (e.g., "\" on Linux, "/" in CMD/PowerShell paths).
  - Shell syntax mismatches (e.g., `Get-ChildItem` outside PowerShell).
  - OS/shell coherence (e.g., Windows-only syntax on non-Windows).

Quick usage

Per-invocation override (recommended for occasional use):
- Translate without strict blocking:
  commandrex translate "list files" --no-strict-validation
- Run session without strict blocking:
  commandrex run --no-strict-validation

What the override does:
- translate: disables strict blocking only for this translation; guidance will be shown in the explanation.
- run: disables strict blocking for the entire interactive/non-interactive run session; guidance remains on.

Defaults
- Strict validation is enabled by default.
- Guidance (short “why” notes) is enabled when strict blocking is disabled.

Configuration (optional)

Environment variables
- PowerShell:
  - setx COMMANDREX_VALIDATION_STRICT_MODE false
  - setx COMMANDREX_VALIDATION_SUGGEST_ALTERNATIVES true
- Bash:
  - export COMMANDREX_VALIDATION_STRICT_MODE=false
  - export COMMANDREX_VALIDATION_SUGGEST_ALTERNATIVES=true
Accepted boolean values: 1/0, true/false, yes/no, on/off (case-insensitive).

Settings file
1) Run CommandRex once to create its config directory.
2) Edit settings.json at:
   - Windows: %APPDATA%/CommandRex/settings.json
   - macOS: ~/Library/Application Support/CommandRex/settings.json
   - Linux: ~/.config/commandrex/settings.json
3) Add or update:
{
  "validation": {
    "strict_mode": true,
    "auto_transform": false,
    "suggest_alternatives": true
  }
}

Common scenarios

1) Windows + CMD/PowerShell user copied a Linux tutorial
- Symptom: `ls`, `grep`, or `/path/like/this` are blocked.
- Fix now: rerun with --no-strict-validation to inspect guidance; or ask for Windows-friendly alternatives.
- Long-term: leave strict on; it prevents accidental misuse.

2) Linux + Bash user running a PowerShell snippet
- Symptom: `Get-ChildItem` or `$env:` variables flagged as shell mismatch.
- Fix now: use --no-strict-validation to see issues inline; or translate your intent to POSIX equivalents.

3) Git Bash on Windows
- Behavior: treated as a Unix shell; Windows-only commands like `dir` will be flagged.
- Tip: Use POSIX-compatible commands in Git Bash, or use PowerShell/CMD instead.

4) CI or shared environments
- Recommend keeping strict_mode=true globally.
- Allow developers to temporarily relax via --no-strict-validation for debugging.

What Phase 1 does not do
- No automatic rewriting/transforming of commands (e.g., `ls` → `dir`). That would be Phase 2 and is intentionally off to avoid surprises.

Troubleshooting

- “Incompatible command for environment …” during translate:
  Keep strict mode on to prevent bad commands. If you need to explore, re-run with:
  commandrex translate "..." --no-strict-validation

- “Incompatible command for environment …” during run:
  For an interactive session that allows exploration, start with:
  commandrex run --no-strict-validation

- I turned strict off but see messages:
  That’s guidance—strict blocking is off, but CommandRex still explains issues so you can choose a compatible approach.

- Make it permanent:
  Use env vars or the settings.json to set strict_mode=false (see Configuration above). For most users, keeping strict_mode=true is recommended.

FAQ

Q: Why block at both translation and execution?
A: Defense in depth—if anything slips through or a user manually edits a command, the executor still prevents incompatible runs.

Q: Will it break existing workflows?
A: Defaults are safe. If you intentionally want to run “foreign” commands, use the --no-strict-validation flag per call/session.

Q: What about automatic conversion?
A: That’s planned as an optional Phase 2 (“auto_transform”). It is not enabled now to keep behavior explicit and predictable.

Summary
- Leave strict on for safety; use --no-strict-validation when you need flexibility.
- You can also adjust behavior via env vars or settings.json.
- Phase 1 focuses on correctness and clarity, not auto-conversion.
