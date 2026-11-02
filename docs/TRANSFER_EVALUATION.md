# Repeated role-specific transfer evaluation

`guardian_transfer_cases.py` builds a seeded **PUBLIC_TRANSFER_DEVELOPMENT**
corpus for all 39 installed roles. Each role receives two to four explicitly
specified, typed data-analysis tasks. These are additional development exercises;
they do not replace the professional contracts or real-stack acceptance criteria.

The default two variants change supplied data and expected conclusions for every
role, not merely case names. Examples include transitive revocation, unique-user
denominators, unknown commit/idempotency, deployment requirements, stale UI
responses, IME suppression, exact threshold boundaries, atomic money transfers,
consumer wire types, duplicated events, ownership surfaces, tenant grants,
mutation-test causes, serial capacity, recovery objectives, cache boundaries and
PowerShell authorization. The host derives expectations before native execution.
The expectation objects are excluded from the public prompt.

The generator and specifications are public. A new seed is **not** a private
holdout, independent benchmark, SME qualification or external certification.
Knowledge of the generator cannot be ruled out, and procedural no-tools checks
are not OS-enforced oracle secrecy. Predetermined specifications also do not test
all professional judgment required to discover missing real-world requirements.

## Bounded execution

Preview only, no model calls:

```powershell
python -B tools/guardian_transfer_cases.py --seed 20261102 --variants 2
python -B tools/test_native_transfer.py --seed 20261102 --variants 2 --repetitions 2
```

After checking the preview, source revision and native tools, an authorized run:

```powershell
python -B tools/test_native_transfer.py --run --seed 20261102 --variants 2 --repetitions 2 --out C:/authorized-workspace/new-transfer-run
```

The output must be new and outside the source checkout. This command uses normal
Codex authentication in place; it neither copies credentials nor installs global
hooks or a global trust entry. The existing native helper supplies a transient
per-process trust setting only for the disposable test project. The effective
sandbox and ordinary permission review still apply. Inherited model and effort
are preserved; model/effort overrides in actual paired spawn calls are rejected
by the shared native corroborator.

Default budget: **78 fresh native children**, at most three concurrently, two
cases per child, **156 judgments**, timeout at most 7200 seconds, zero automatic
retries. Parameters permit 2–5 independent repetitions and 2–4 variants; maximum
195 children and 780 judgments. No timeout/quota recovery silently reruns failed
trials. New campaigns must preserve previous results rather than selecting the
best outcome. The parent must not read oracle/source files or use non-collaboration
tools; each child has no tools, extra delegation or access to previous answers.
Actual sessions are checked for those restrictions after the run. Where parent
model/effort turn-context metadata exists, children must match it; parent drift or
an observed child mismatch is rejected. Missing metadata remains explicitly unknown.
This validation
is local observational corroboration, not sandbox containment or remote attestation.

The disposable project installs core and all ten optional packs, and profile
bytes are checked. Session role, parent, unique task, paired spawn, completion,
actual model, pure JSON and absence of child tools are independently read by the
host collector. An effort change within a child or between observed trials is
rejected. Missing effort metadata remains unknown; an instruction to inherit is
not promoted to observed evidence. No generated candidate code is executed.

## Result interpretation

Every planned judgment stays in the denominator. Missing/invalid children,
unexpected children, duplicate tasks, malformed responses, unknown/duplicate case
IDs, wrong typed values, source/profile fixture drift and actual model/effort
drift cannot yield complete success. Each role has planned, observed, passed,
failed and missing counts. A wrong assertion and unavailable evidence remain
different states. Cost remains unknown unless independently measured; batch
elapsed time is recorded, not mislabeled per-child latency.

Descriptive Wilson 95% intervals are computed over observed judgment errors.
Missing judgments are separately counted and prevent complete success, rather
than being declared observed errors or silently removed. With four correct
judgments and no errors the upper bound remains approximately 49%; samples are
small. Judgments inside one child and repetitions of public inputs are correlated,
so the interval is **not a calibrated independent-trial reliability guarantee**.
False-positive/negative rates are not manufactured for mixed structured tasks
that lack a predefined binary class definition.

Private raw event logs and child artifacts are retained locally; the public
summary exposes session hashes, never raw session IDs or credentials. Bindings
include source revision, actual profile hashes, generator/harness hashes, corpus
and public inventory digests, seed, repetitions, observed model and platform.
Windows inherited private-log DACL and timeout descendant cleanup are not certified.

Passing means only **OBSERVED_TRANSFER_NOT_CERTIFIED**. It does not establish
browser/AT/provider/DB execution, professional certification, production readiness,
world-tier superiority, general safety, private-holdout validity, or acceptance of
the 63 remaining full professional criteria. Distinct independent review and the
principal's scope-specific acceptance remain necessary.

Directed checks:

```powershell
python -B -m unittest tests.test_transfer_cases -v
```

They exercise all 39 positive and changed-output controls, cross-variant answer
rejection, no-oracle delivery, seed/budget bounds, closed schemas, missing/duplicate
observations, model/effort drift, and native role/parent/completion/tool restrictions.
