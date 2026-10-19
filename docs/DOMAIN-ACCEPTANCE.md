# Functional domain acceptance

`tools/guardian_domain_native.py` executes reviewed, bounded synthetic fixtures in
eight domains. It does not accept supplied code or an observation containing a
claimed success. A real runtime must produce each observed result. A missing
runtime or denied OS boundary yields `BLOCKED` and a nonzero command exit status.
An application assertion failure yields `FAILED`.

Run from the repository root with Python 3.11 or newer:

```sh
python -B tools/guardian_domain_native.py --temp-dir /short/disposable/path --out domain-acceptance.json
python -B -m unittest discover -s tests -p test_domain_native.py -v
```

The temporary directory must be writable. Prefer a short path on Windows. All
databases, build outputs and browser profiles are disposable children of that
directory. The runner deletes them after the run. The report contains source
hashes, per-check outcomes, scope and explicit limitations. It contains no user
documents, credentials or session data. It is local evidence, not a signature or
an authenticated certification of another environment.

| Domain | Executed boundary and checks | Prerequisite and limits |
| --- | --- | --- |
| .NET | Compiles a local C# project, executes exact `long` arithmetic, catches an actual checked overflow and observes actual cancellation-token propagation. Three checks. | .NET SDK and installed `net8.0` reference pack. NuGet sources are cleared, audit disabled and no packages downloaded. These checks do not validate an ASP.NET application. |
| API | Starts an HTTP server bound only to `127.0.0.1` on an OS-assigned port; sends real requests for trimmed valid input, blank name, wrong type, unknown field and malformed JSON. Five checks. | Permission to bind loopback. No external HTTP endpoint or production deployment. Authentication, load and TLS are outside this fixture. |
| Financial | Executes SQLite transactions for a transfer, exact minor units, idempotent replay, conflicting replay, fraction/boolean rejection, overdraft and injected failed-credit rollback. Seven checks. | Python SQLite. Synthetic balances only. This does not establish distributed idempotency, concurrent service correctness or regulatory suitability. |
| Data | Executes SQLite migration, compares actual rows, injects duplicate keys, confirms schema/row rollback and unchanged source. Three checks. | Python SQLite. Other database engines, large datasets and production migration recovery remain outside this fixture. |
| UI | Starts Chromium with a new disposable profile and its sandbox enabled. CDP uses anonymous pipes. Checks the actual accessibility tree for the Email textbox and Save button; inserts invalid email and presses Enter; then inserts valid input and presses Enter and observes the live output. Four checks. | Node and installed Chrome/Edge/Chromium. No downloads, extensions, existing profiles or `--no-sandbox`. Page network requests are blocked; a dead loopback proxy and DNS mapping prevent normal external browser requests. These are browser controls, not an OS network sandbox certification. Screen-reader behavior and complete WCAG conformance are not claimed. |
| PowerShell | Executes a reviewed `SupportsShouldProcess` function: WhatIf creates no file, explicit apply writes expected bytes, and WhatIf preserves a pre-existing file. Three checks. | `pwsh` or Windows PowerShell. A noninteractive WhatIf test does not establish interactive confirmation UX or elevated-script safety. |
| Cloud plan | Parses actual local JSON plans and executes an allowlist policy: bounded read accepted; wildcard action, public principal, destructive action and unknown fields denied. Five checks. | Offline policy evaluation only. No cloud credentials, provider, infrastructure changes or claims about Terraform/provider semantics. |
| AI assurance | Executes a deterministic typed extractive retrieval pipeline, accepts a reviewed fact with a known citation, resists a retrieved instruction, excludes a synthetic private canary and abstains without trusted evidence. Four checks. | No model call. This verifies a deterministic boundary, not an LLM's resistance to prompt injection or a deployed RAG system. Source labels in this fixture are not cryptographic provenance. |

The initial Windows acceptance executed all eight adapters: **34 checks passed,
zero blocked and zero failed**. This is scoped to the reviewed fixtures and the
available runtimes. Portable unittest has 15 regression tests; sandboxed runs
can skip unavailable loopback/browser boundaries, while the acceptance CLI
always exits nonzero if any requested adapter is blocked. The separately
authorized native run passed all 15 tests with zero skips.

Existing `TASK.md`, sample application files and `oracle.json` describe separate
model-edit tasks. Their `NOT VERIFIED` status is retained deliberately: executing
the new reviewed functional fixtures does not mean a model has edited and passed
those tasks. `guardian_domain_checks.py` continues to validate supplied static
observations; it is not a replacement for these functional adapters. Native
Guardian agent execution and model A/B evaluation are separate acceptance gates.

No adapter is a general-purpose sandbox. Do not substitute model-generated
source into these fixtures and execute it on the host. The acceptance runner
has no input-code option, never installs runtimes and never weakens an existing
sandbox. Provision missing dependencies through the environment's approved
process, then rerun the same command and retain its report.

## Windows CLI restriction probe

`python -B tools/guardian_client_probe.py --out NEW_EMPTY_DIRECTORY` is a
separate, quota-free probe. It invokes `codex sandbox` with a named synthetic
permission profile passed solely through `-P` and a `-c` TOML override. It keeps
managed requirements active, denies external synthetic-file reads/writes and
disables command network access. It grants read access only to the minimal
runtime and the installed Python directory, plus writes in its synthetic
workspace. The profile format follows the official
[permissions guide](https://learn.chatgpt.com/docs/permissions) and
[configuration schema](https://learn.chatgpt.com/docs/config-schema.json).

The observed Windows CLI **0.163.0-alpha.10.2** accepted the profile syntax but
rejected startup with `Restricted read-only access requires the elevated Windows
sandbox backend`. The probe therefore reports `UNSUPPORTED` for strict filesystem
isolation in this active backend. The synthetic child did not execute, and all
other capability statuses remain `unknown`. A denied point observation would
still not certify a complete sandbox.

The command exits nonzero on blocked/unsupported startup. Public `report.json`
contains only sanitized diagnostics and hashes. Raw stdout, stderr and the
path-bearing command are kept under the caller's disposable `private/` folder;
review those locally and exclude them from public artifacts. No global profile,
host accounts, firewall rules or backend settings are changed by the probe.
Enabling/provisioning another Windows backend requires a separate authorized
environment operation; this runner has no fallback that enables it automatically.
