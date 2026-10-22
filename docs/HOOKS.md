# Optional Codex lifecycle adapter

Guardian hooks are opt-in advisory coordination, not a permission system or universal interceptor. They read bounded JSON on stdin, make no model call, never read transcripts and do not persist prompts. Output contains fixed instructions and filtered role/risk hints, not raw user/repository content.

Events: SessionStart, UserPromptSubmit, SubagentStart and SubagentStop. The last does not endlessly retry or self-certify a child. The principal remains responsible for semantics, current roles and verification.

```sh
python tools/guardian_hooks.py install --project PATH
python tools/guardian_hooks.py install --project PATH --apply
python tools/guardian_hooks.py doctor --project PATH
python tools/guardian_hooks.py uninstall --project PATH
python tools/guardian_hooks.py uninstall --project PATH --apply
```

Use `--codex-home EXACT_DIRECTORY` instead for a deliberately chosen personal Codex directory. No global location is inferred. Changes are limited to hooks.json and a namespaced receipt under the selected directory, coordinated by the shared maintenance lock. Foreign groups and values are preserved; JSON formatting may normalize. Receipts contain owned definitions/hashes, not backups of potentially secret foreign commands.

Interrupted atomic operations remain visible. Explicit uninstall can remove only the validated receipt if none of its handlers exists, or the exact groups if all exist. Partial/changed ownership blocks. Updated source needs removal/re-registration and review, never silent trust promotion.

**Codex hook trust is separate.** Non-managed hooks must be reviewed/trusted through the supported Codex interface (`/hooks` in the CLI). Guardian never writes trust records or passes a trust-bypass flag. Registered does not mean trusted/executed; project trust, managed policy and active host matter. A CLI feature listing is not a Desktop callback test.

Windows commands explicitly invoke PowerShell with quoted paths; shell metacharacters in Windows paths are conservatively rejected. Event data is never shell interpolation. Hook errors are surfaced but may not block tools, so effective OS/sandbox permissions and external authorization remain authoritative.

Direct-process tests cover input bounds, duplicate keys, canaries and safe output; registration tests cover dry-run, foreign preservation, interruption and conflicts. Real Codex testing additionally needs fresh chat, resume, compaction and callback evidence; unexercised events remain NOT VERIFIED. [Official hooks documentation](https://learn.chatgpt.com/docs/hooks).
