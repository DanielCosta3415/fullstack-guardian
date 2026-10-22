# Guardian development workspace

Use the installed Guardian coordination policy and the repository's checked-in tools. For sustained implementation, maintain `.guardian-state/current.json` with `tools/guardian_checkpoint.py` and keep that directory untracked. On “Continue”, inspect the checkpoint, Git state and referenced evidence before choosing the next bounded task. Reconcile changes; never overwrite another contributor's work or reuse stale acceptance results as current evidence.

Release verification supports explicit operator policy selection. Preserve strict compatibility for users who choose it; an explicitly chosen autonomous policy replaces human review and remote native testing with corroborated local native acceptance and distinct G01/G02 agent reviews. CI, signed artifact provenance, real recovery tests, truthfulness and effective permissions remain required. Policy records are operator decisions, not certificates of professional expertise.

Candidate outputs must not execute untrusted code on the host. Professional artifact evaluation should remain data-only unless a separately verified execution boundary supports the actual language and task. Public objective development checks do not establish private holdout validity, human certification or universal performance.
