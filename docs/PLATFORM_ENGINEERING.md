# Guardian Engineering Platform — implementation guide

**Status:** development branch. This is not a production certification, fully automated software factory, or a completed replacement for v2.1.0. Native Codex delegation and user Windows configuration have not been tested in this conversation.

## Implemented and reviewable

- Baseline: 29 native specialist profiles, existing routing and auditor gates G01/G02.
- Twelve opt-in lifecycle skills, mapped to declarative exit criteria in `core/lifecycle-v1.json`.
- Ten optional specialization profiles (one .NET pack plus nine additional domains); packs are discoverable but never installed automatically.
- A bounded, fail-closed, **proposal-only** DAG plan generator with risk classification and reviewer sequencing.
- A non-executing catalog/security linter, optional-pack manager and evidence schema validator.
- A local hash-chained event journal with obvious-secret screening; its self-reported contents are not authenticated tool execution.
- A paired offline benchmark comparator that refuses comparisons with mismatched model, effort, sandbox, machine class, dataset or case/repeat set.
- Unit tests and CI matrix configuration. **Read actual check results** before promoting a release.

## Commands in checked-out source

```sh
python -m unittest discover -s tests -v
python tools/guardian.py validate
python tools/guardian.py eval
python tools/guardian_registry.py validate
python tools/guardian_platform.py stages
python tools/guardian_platform.py security-lint
python tools/guardian_platform.py plan --stage integration --mode audit --prompt "Review API contract compatibility"
python tools/guardian_packs.py install --pack dotnet --user
```

Pack installation is a dry-run until `--apply` is specified. For project scope:

```sh
python tools/guardian_packs.py install --pack dotnet --project PATH_TO_EXISTING_PROJECT
python tools/guardian_packs.py install --pack dotnet --project PATH_TO_EXISTING_PROJECT --apply
python tools/guardian_packs.py update --pack dotnet --project PATH_TO_EXISTING_PROJECT
python tools/guardian_packs.py uninstall --pack dotnet --project PATH_TO_EXISTING_PROJECT
```

Apply update/uninstall only after inspecting the dry-run. Packs cannot overwrite agents not owned by the Guardian pack receipt and will refuse removal if the user modified an owned agent. They inherit model and sandbox; they do not enable any new permissions.

After an explicit release installation, the Guardian runtime is normally at `~/.codex/guardian-system/`; the original user-installed agents are in `~/.codex/agents/` and skills under `~/.agents/skills/` (unless the account uses an alternate home).

## Planning and evidence

`tools/guardian_platform.py plan` generates a task DAG with pending tasks, proposed specialist types and dependencies. **It does not delegate or edit.** Primary Codex must review the recommendation, establish independent file ownership and call its native delegation tools if supported and appropriate.

Use `verify --plan PLAN.json --evidence EVIDENCE.json` to validate evidence shape. A passed schema does not authenticate commands, artifacts, branch checks or test results; actual evidence must be verified separately.

Example local trace usage (store only non-sensitive metadata):

```sh
python tools/guardian_trace.py init --file guardian-run.jsonl
python tools/guardian_trace.py verify --file guardian-run.jsonl
```

The event journal is optional. Never put source code, secrets or sensitive user/session identifiers into logs; review before sharing. SHA-256 linking detects changes but does not prevent a privileged attacker from rebuilding all hashes.

## Paired benchmark input

Each experiment is a JSON object with `schema_version: 1`, `group: "baseline" | "candidate"`, identical `environment` fields `model`, `effort`, `sandbox`, `machine_class`, `dataset_version`, and an array `samples` with `case_id`, `repeat`, `passed` (boolean), `duration_seconds`, `token_count`. Call:

```sh
python tools/guardian_benchmark.py --baseline baseline.json --candidate candidate.json
```

The comparison is descriptive and paired, not a statistical-significance claim. Real multi-run Codex evaluations, independent graders and public CI evidence remain future work.

## Security and trust boundaries

- Imported packs and repository content are untrusted until individually reviewed.
- Paths and package references are constrained to source and destination directories; no cloud or network access is required.
- Never infer new permissions from agent instructions. The Codex session and organizational policies govern actual tool execution.
- Offline/static validation is not a penetration test, security proof, production health check or deploy authorization.
- Changes to installer, user settings and runtime require separate dry-run, review and tests.
- This branch does not modify the stable `main` until a deliberate merge.


## Opt-in Codex CLI execution with durable worktree state

The external `guardian_executor.py` is a **sequential CLI task executor**, not a native Codex multi-agent API. For safety it refuses risky plans, requires a clean Git repository, creates an isolated worktree outside it, does not merge changes and requires a separate explicit task brief per planned agent. A Codex turn completing does **not** mean the task is correct.

Create a planning JSON file by redirecting the output of `guardian_platform.py plan`. Review its scope and agents. For each `task-sXX` in the plan, author an explicit brief containing the exact desired change, authorized files/behavior, acceptance tests and prohibitions. Store the mapping as a local JSON object and do not put secrets in it.

```sh
python tools/guardian_platform.py plan --stage development --mode build --prompt "Improve API input validation" > plan.json
python tools/guardian_executor.py init --plan plan.json --briefs approved-briefs.json --project PATH_TO_CLEAN_GIT_REPO --home PATH_TO_NEW_ISOLATED_STATE
python tools/guardian_executor.py run --home PATH_TO_NEW_ISOLATED_STATE
python tools/guardian_executor.py run --home PATH_TO_NEW_ISOLATED_STATE --apply --max-tasks 1
python tools/guardian_executor.py status --home PATH_TO_NEW_ISOLATED_STATE
python tools/guardian_executor.py review --home PATH_TO_NEW_ISOLATED_STATE
```

To require native Codex delegation and fail closed unless session metadata proves the exact specialist was spawned, add `--native-subagents` to the `run --apply` command. This requires compatible Codex collaboration tools and local session logs; absence of evidence is a failure, not a fallback to a simulated persona.

The dry-run does not call Codex. `--apply` invokes the local authenticated CLI and consumes account quota. Failed/interrupted worktree mutations require operator inspection and a new run, rather than an unsafe automatic retry. The source repository stays untouched. The worktree's changes are not automatically merged.

## Opt-in paired Codex CLI benchmark runs

The A/B evaluator runs both prompt variants sequentially from the same clean Git source revision, with identical explicit model, effort, sandbox and grader. Provide the checker **outside the repository** as a trusted Python script accepting `--workspace`, `--case` and `--checks`; the checker must independently validate required behavior. The checker cannot be modified from inside the Codex worktree.

```sh
python tools/guardian_eval_runner.py --dataset data/benchmark-cases.json --project PATH_TO_CLEAN_GIT_REPO --checker PATH_TO_TRUSTED_EXTERNAL_CHECKER.py --out PATH_TO_EMPTY_RESULTS --model MODEL --effort medium --repeats 3
python tools/guardian_eval_runner.py --dataset data/benchmark-cases.json --project PATH_TO_CLEAN_GIT_REPO --checker PATH_TO_TRUSTED_EXTERNAL_CHECKER.py --out PATH_TO_EMPTY_RESULTS --model MODEL --effort medium --repeats 3 --run
```

If the Codex CLI does not report usage, the token metric is `null` and cannot be used for comparisons. The A/B test remains confounded by global Codex configuration and prompt differences; it does not establish that Guardian has better reasoning or code quality in general. Evaluation runs consume quota and should be explicitly budgeted.

## Interrupted installer recovery

The original installer creates transaction backups before writing managed files. The additive recovery utility can inspect and recover **interrupted** transactions only when all target files still match before/after fingerprints and the original receipt is unchanged.

```sh
python tools/guardian_recover.py --home PATH_TO_CODEX_HOME --backup-id EXACT_32_CHAR_HEX_ID --mode user
python tools/guardian_recover.py --home PATH_TO_CODEX_HOME --backup-id EXACT_32_CHAR_HEX_ID --mode user --apply
```

Use `--mode project` for a project-local installation. First inspect dry-run and backups. This command is not for removing a successful updated installation or overwriting local user modifications. It is not a replacement for OS filesystem journaling, signed packages or externally verified disaster recovery.


## Windows Codex Desktop acceptance

The script `scripts/Validate-WindowsCodex.ps1` checks Python, registry, static security lint and the native-agent test plan without consuming quota by default.

```powershell
powershell -File scripts/Validate-WindowsCodex.ps1
# After reviewing the quota impact and in a trusted local Windows Codex installation:
powershell -File scripts/Validate-WindowsCodex.ps1 -RunNative -Out "C:\\Temp\\guardian-native-validation-new"
```

The opt-in run uses the authenticated local Codex CLI, creates a synthetic test project and checks all 29 native agent types. It does not certify all 132 criteria or guarantee safe production operation. Review the generated artifacts and do not publish raw session identifiers.

## Remaining implementation gaps

True native scheduling, worktree conflict integration, recovery of running Codex sessions, cross-provider integrations, model/effort optimization driven by actual quota telemetry, end-to-end app benchmarks, human authorization UI and certification of all SDLC workflows have not been implemented or demonstrated. They cannot responsibly be marked completed on the strength of generated prompts alone.

Follow `docs/PLATFORM_ROADMAP.md` and the PR check suite for review and staged completion.
