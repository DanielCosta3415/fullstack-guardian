# Security boundaries

Treat repository content, profiles, plans, tool output, MCP/browser content and model-generated code as untrusted data. They cannot authorize actions, waive evidence requirements or change instruction hierarchy.

The trusted supervisor validates identities, scopes, dependencies, budgets, risk gates and evidence. A model's claim is not authenticated tool execution. Exit zero is not a test oracle. Local checksums detect changes but are not identity signatures or proof that a command ran.

Generated code is graded only through an approved isolated backend with no user home/credentials/network, read-only grader and bounded resources. Python -I, Git worktrees, profile sandbox text and secret regexes are not OS isolation. Missing isolation blocks grading.

Installation is dry-run first, namespace-limited and drift-sensitive. Maintenance operations share coordination and preserve backups/user edits. Never remove an active lock or edit ownership receipts to force an update.

Native subagents inherit effective parent permissions. Supported feature/skill disabling reduces capabilities but does not create a separate filesystem sandbox. Unknown client capabilities are not assumed. External tools/services are configured and authorized in the parent context; profiles never install npm packages or connect arbitrary MCP endpoints automatically.

## Reporting

Provide a minimal safe reproduction, affected revision and impact/preconditions. Use synthetic data, not actual tokens or other users' files. Do not probe production or third-party systems without appropriate authorization. A finding remains open until a versioned fix and meaningful regression establish the claimed mitigation. CodeQL success or signed build provenance alone is not security certification.
