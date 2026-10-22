# Existing global native profile validation

The default native harness installs a disposable project runtime. Its 39-role
result proves that project installation, not global profile discovery.

After installing the exact reviewed 2.2 source and all ten optional packs globally,
run from a canonical source checkout whose bytes match the shipped archive:

```powershell
python -B tools/test_native_agents.py --global-existing --all --include-packs --run --out C:/new-empty-evidence-directory
```

`--run` authorizes account quota consumption. This mode installs nothing. It
checks `CODEX_HOME` (or the usual user `.codex`), enabled agents, exact version,
ownership receipts, all 39 profile bytes and all shipped runtime source bytes.
It rejects same-name Guardian profiles or agent configuration in project ancestor
directories because native global discovery would be ambiguous. The fixture
project has no locally installed `.codex` profiles or `.guardian` runtime. A00
uses the explicit global router. Children still execute the same real synthetic
fixture checks, under the unchanged workspace-write sandbox and default model.

Global `config.toml` must not contain explicit mappings for any of the 39 Guardian
names: those mappings could override profile discovery. Duplicate Guardian names
under alias filenames in global `agents/` are also rejected. Validation never
removes or rewrites such customizations and never follows a `config_file` target.
Unrelated custom agent profiles and settings are preserved and accepted. Explicit
profile/config TOML reads are bounded to 2 MB each.

Only explicit configuration/policy/receipts, Guardian profiles and runtime hashes
are recorded before and after; root credentials and auth files are never read.
The private hash manifest stays in the evidence directory. A successful summary
must say `runtime_scope: global-existing` and `global_unchanged: true`. It proves
controlled CLI global-role discovery and checks, not general professional
qualification, Desktop/resume behavior, remote attestation or malicious-host
resistance. Do not substitute this result into the release verifier's project
runtime acceptance path, which deliberately requires project-installed files.

Without `--run`, planning consumes no quota and makes no global validation claim.
With global mode, all 39 roles and packs are required; focused retries use the
ordinary isolated project mode and cannot prove a complete global rollout.
