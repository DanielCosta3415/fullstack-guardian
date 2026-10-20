# Generated catalog

Version: 2.2.0-dev.4

Availability is not installation, native loading, or correctness. Model policy inherits by default.

Reviewed sources: `core/contracts-catalog-v1.json` owns identity/base instructions and metadata; `core/professional-contracts-v1.json` owns the professional methods, typed capabilities, routing terms, required/conditional/optional tool needs, handoffs and unmeasured qualification. The appended professional instruction must exactly match the renderer; neither generated TOMLs nor derived playbooks can rebaseline the canonical sources. `python -B tools/guardian_catalog.py --write` generates 39 TOMLs, core metadata, ten pack manifests and the compatibility playbook. It never writes user configuration or model/sandbox permissions.

| ID | Role | Kind | Reviewer | Profile SHA-256 |
|---|---|---|---|---|
| A00 | guardian_engineering_orchestrator | core | G01 | 13a73b22a4ccf0bff3e33d2c826bb9e4dfca0f4057535acc002a557717ae52a7 |
| S01 | guardian_product_discovery | core | G01 | d0f9e63d2ab9cee2bb2d8246b85bd2284e347d35923b1cf41a783f8212e16476 |
| S02 | guardian_requirements_engineer | core | G01 | f5ed32ff70260a415e093544a372902e061bc0878c83bc7d449f0c3e3ef55ce2 |
| S03 | guardian_solutions_architect | core | G01 | 40a5aa68b0f6f7c373b9c290b1192ff683ee7413929408d28c08c6e467a106bb |
| S04 | guardian_frontend_architect | core | G01 | 3e6aa9168e9083cc8299ca4784decf51ca4343fb5029faec64affed96ea4ae7a |
| S05 | guardian_frontend_engineer | core | G01 | 7a2079d961eea656fa38ecbacc3781e18825b9197cc7be0a5c85c976348e4cd9 |
| S06 | guardian_ux_accessibility | core | G01 | c153dc71108f9b5d6e6bccd971ae5be45986bbde621e7f91cad117a49f2fa8c4 |
| S07 | guardian_web_performance | core | G01 | bd179009742e73c70f543158b84e9b16851d794d38fa3dcd5c56faca38c40621 |
| S08 | guardian_backend_domain | core | G01 | 25c1815a0adeee3bb83990cb6a17136408eda0a7018018d9620ccd17ef40add4 |
| S09 | guardian_api_integration | core | G01 | a994e51d6746b04339e48e5f7653ba8d3486eb26ec5e7d151abcc10a9fd52321 |
| S10 | guardian_distributed_concurrency | core | G01 | 10e6ad7c080e7f96c0a524f04de44305beaae8d32ed6e350a3c3866ad624dfe6 |
| S11 | guardian_database_transactions | core | G01 | 21a4f80805455ad1c07bb8a933d2f028d2adff20712913c1dae84002c28a5c24 |
| S12 | guardian_data_governance | core | G01 | 2e5709e9ba3023ad54c6fb0a16fa8c9f1f783328889edb760b11ee38ae208186 |
| S13 | guardian_appsec | core | G01 | 095e2dae0afa6c6da7ce2f5bb522a33163dc1dace0432ab082a8ff705d46aced |
| S14 | guardian_iam_privacy | core | G01 | 28b8dfc41aa8e5bf4e77e05be87488e6b0a5b3602c6c296bee44e314926dbf68 |
| S15 | guardian_cloud_supply_security | core | G01 | 430117e7d94a5b48f859c31051e6bdbd044e813ee8d5b7515f548183fedfe488 |
| S16 | guardian_quality_architect | core | G01 | 6c762a0c83e3f352d504aa19baa9f414c37ab121ad92d5bd774ec0b18473d201 |
| S17 | guardian_frontend_qa | core | G01 | a518eada701ddbb44cb1f35b99e30ffee26b1843809dfc3db0d214ea8a39530c |
| S18 | guardian_backend_qa | core | G01 | 00024a2d31d5d5774ce31b73d0797d478b89571b73824440fdc304dc68da2c9a |
| S19 | guardian_performance_capacity | core | G01 | adb699d308a0c8dccd9a9878829085ca112acbdb4564ae1c22c9188456c670a8 |
| S20 | guardian_sre_resilience | core | G01 | 83780629d950b9b6d2e35073563eabe8a225d7149881be22c190e8276886f8f8 |
| S21 | guardian_observability | core | G01 | 842af924791736fcc529d87c5dba06d9b10f2398e2214f81bfc8371c84b63405 |
| S22 | guardian_cloud_platform | core | G01 | f86b7ca14de85514768143f0eca4659195ef68a27cdccc90d93df2ab827abcf1 |
| S23 | guardian_devsecops | core | G01 | cbe7b9e87fbbaae7716b9cff8f943c8d517232c064697ae3545d0708969e0a9d |
| S24 | guardian_maintainability | core | G01 | eb66b074a4e8ba2888b405aa5ac4b54b5c9c5f928bfaa08eb37d99c80e309b6a |
| S25 | guardian_governance_finops | core | G01 | d215bac85f3a2f4ef7b9df7519d66fa916bd0d517743fa47130923a81e564a9d |
| S26 | guardian_ai_assurance | core | G01 | 546b70ca68f93c19e575892408c0b4a6a4aa69b2e8ae79f1dd918c732663ff6e |
| G01 | guardian_independent_auditor | core | G02 | 35da8856e4df43ece8d846066963c3a85ea227ee5a23a07771003680aa3dff92 |
| G02 | guardian_release_auditor | core | G01 | f8455c0312b5e1629990c8502baacc92e2d8975147212ced29efac65e2d51e81 |
| pack:ai-systems:guardian_rag_llm_specialist | guardian_rag_llm_specialist | optional | G01 | 23048ee3c7102f5b24ef17dd6dcaa9501bcf51c66b09acfb183af316bc625248 |
| pack:api-integration:guardian_api_contract_specialist | guardian_api_contract_specialist | optional | G01 | 2be93a14bf55338418448ae1f817f88ca360856ae7bb52b75015500a12d65a83 |
| pack:cloud-platform:guardian_cloud_infrastructure_specialist | guardian_cloud_infrastructure_specialist | optional | G01 | fa18f994f0fb2e0f96141599ca78a79a288911ddfa15e49fd6405eebb7e05b61 |
| pack:data-engineering:guardian_data_migration_specialist | guardian_data_migration_specialist | optional | G01 | 8783f8126bdd3706dba2cacb47d7886942c0bb89de0db33028b64034647ccdfb |
| pack:dotnet:guardian_dotnet_runtime_specialist | guardian_dotnet_runtime_specialist | optional | G01 | 930ede4bb0dfbdc8b73b3e0f075610b599ab4159a868da204874b058ba08763c |
| pack:financial-systems:guardian_payment_reliability_specialist | guardian_payment_reliability_specialist | optional | G01 | c8b6d6bf0377d703dab463429d6e22c9f5b58874db7e7853a780511800df8d96 |
| pack:frontend-experience:guardian_browser_accessibility_specialist | guardian_browser_accessibility_specialist | optional | G01 | f9eb524f530cdac033f511e18cd84a3b39bafcd0a2613432d74756856d037e59 |
| pack:quality-automation:guardian_contract_test_specialist | guardian_contract_test_specialist | optional | G01 | f0a9da7ea1e54fba882851c9c0fceb86873001b66033f806002c50408bfa7d37 |
| pack:security-assurance:guardian_threat_model_specialist | guardian_threat_model_specialist | optional | G01 | 0952bc9837ee8eb40de6857e94817d0153a4ec21be1baf90d5604d2591332994 |
| pack:windows-tooling:guardian_windows_powershell_specialist | guardian_windows_powershell_specialist | optional | G01 | e14cb35597f383073e0e0644f5c88e4a5654fc0783afe9ad25938e21776b8cf6 |

## Professional contracts (39)

Contracts are declarations, not certificates. All professional qualification remains `NOT_EVALUATED` until separate measured evidence exists. Core `competencies` now holds taxonomy IDs; routing words remain separately in `routing_terms` and legacy `core/agents.json` keywords.

| ID | Modes | Typed capabilities | Required tool needs | Contract |
|---|---|---|---|---|
| A00 | audit, build, remediate, explore | 0 | project_artifact_reader | 1.0.0 |
| S01 | audit, build, remediate, explore | 8 | project_artifact_reader | 1.0.0 |
| S02 | audit, build, remediate, explore | 17 | project_artifact_reader | 1.0.0 |
| S03 | audit, build, remediate, explore | 29 | project_artifact_reader | 1.0.0 |
| S04 | audit, build, remediate, explore | 33 | project_artifact_reader | 1.0.0 |
| S05 | audit, build, remediate, explore | 13 | project_artifact_reader | 1.0.0 |
| S06 | audit, build, remediate, explore | 6 | project_artifact_reader | 1.0.0 |
| S07 | audit, build, remediate, explore | 2 | project_artifact_reader | 1.0.0 |
| S08 | audit, build, remediate, explore | 3 | project_artifact_reader | 1.0.0 |
| S09 | audit, build, remediate, explore | 2 | project_artifact_reader | 1.0.0 |
| S10 | audit, build, remediate, explore | 26 | project_artifact_reader | 1.0.0 |
| S11 | audit, build, remediate, explore | 9 | project_artifact_reader | 1.0.0 |
| S12 | audit, build, remediate, explore | 13 | project_artifact_reader | 1.0.0 |
| S13 | audit, build, remediate, explore | 12 | project_artifact_reader | 1.0.0 |
| S14 | audit, build, remediate, explore | 11 | project_artifact_reader | 1.0.0 |
| S15 | audit, build, remediate, explore | 13 | project_artifact_reader | 1.0.0 |
| S16 | audit, build, remediate, explore | 20 | project_artifact_reader | 1.0.0 |
| S17 | audit, build, remediate, explore | 5 | project_artifact_reader | 1.0.0 |
| S18 | audit, build, remediate, explore | 5 | project_artifact_reader | 1.0.0 |
| S19 | audit, build, remediate, explore | 5 | project_artifact_reader | 1.0.0 |
| S20 | audit, build, remediate, explore | 8 | project_artifact_reader | 1.0.0 |
| S21 | audit, build, remediate, explore | 3 | project_artifact_reader | 1.0.0 |
| S22 | audit, build, remediate, explore | 3 | project_artifact_reader | 1.0.0 |
| S23 | audit, build, remediate, explore | 3 | project_artifact_reader | 1.0.0 |
| S24 | audit, build, remediate, explore | 8 | project_artifact_reader | 1.0.0 |
| S25 | audit, build, remediate, explore | 6 | project_artifact_reader | 1.0.0 |
| S26 | audit, build, remediate, explore | 1 | project_artifact_reader | 1.0.0 |
| G01 | audit, explore | 132 | project_artifact_reader | 1.0.0 |
| G02 | audit, explore | 0 | project_artifact_reader | 1.0.0 |
| pack:ai-systems:guardian_rag_llm_specialist | audit, build, remediate, explore | 12 | project_artifact_reader | 1.0.0 |
| pack:api-integration:guardian_api_contract_specialist | audit, build, remediate, explore | 11 | project_artifact_reader | 1.0.0 |
| pack:cloud-platform:guardian_cloud_infrastructure_specialist | audit, build, remediate, explore | 9 | project_artifact_reader | 1.0.0 |
| pack:data-engineering:guardian_data_migration_specialist | audit, build, remediate, explore | 15 | project_artifact_reader | 1.0.0 |
| pack:dotnet:guardian_dotnet_runtime_specialist | audit, build, remediate, explore | 15 | project_artifact_reader | 1.0.0 |
| pack:financial-systems:guardian_payment_reliability_specialist | audit, build, remediate, explore | 18 | project_artifact_reader | 1.0.0 |
| pack:frontend-experience:guardian_browser_accessibility_specialist | audit, build, remediate, explore | 18 | project_artifact_reader | 1.0.0 |
| pack:quality-automation:guardian_contract_test_specialist | audit, build, remediate, explore | 8 | project_artifact_reader | 1.0.0 |
| pack:security-assurance:guardian_threat_model_specialist | audit, build, remediate, explore | 14 | project_artifact_reader | 1.0.0 |
| pack:windows-tooling:guardian_windows_powershell_specialist | audit, build, remediate, explore | 9 | project_artifact_reader | 1.0.0 |

Required tool needs are abstract capabilities, not native tool names, permission grants or observations. Dynamic runners are conditional on the task. Missing essential capability blocks only the dependent check; static review must label its limits.

`python -B tools/guardian_professional.py S07` loads the full i18n/performance contract. Python callers use `load_contracts(root)`, `get_contract(agent_id, root)`, and `checkpoints_for(agent_id, root)` for all 29 core and ten optional roles. Unknown roles fail closed; optional roles still require installation and actual eligibility.

G01/G02 allow only audit/explore. Reviewer ownership is a review responsibility, not an executable dependency edge; it does not create a reciprocal execution cycle. S07 owns a conditional i18n overlay for Unicode/RTL, pluralization, fallback, pseudo-localization, dates/time zones and currency with S06 handoff.

Schema: `core/professional-contracts-v1.schema.json`; stdlib runtime additionally checks exact identity coverage, taxonomy ownership, independence, and generated method/playbook drift.

## Untrusted specialist result proposals

`core/professional-result-v1.schema.json` documents the closed result shape. `validate_result(result, agent_id, task_id=..., obligation_ids=[...], root=...)` binds the producer identity, version, task and every obligation; rejects traversal, malformed hashes, unknown evidence references, inconsistent check outcomes and self-approved statuses. `produced` remains an untrusted claim. The supervisor must separately bind paths to the allowed scope, read actual bytes, corroborate executed tool calls and obtain independent consumer/reviewer acceptance.

A result contains the twelve fields: task_id, agent_id, contract_version, obligations, artifacts, facts, assumptions, decisions, checks, not_verified, residual_risks and handoff. Facts reference declared `artifact:<relative-path>` or `check:<id>` evidence. A producer can only declare an obligation produced/blocked/not_verified and a handoff pending_consumer_acceptance/blocked, never verified/integrated/accepted.

```python
from tools.guardian_professional import result_template, validate_result
proposal = result_template("S08", task_id="task-1", obligation_ids=["O1"])
# Initial template honestly reports O1 not_verified and handoff blocked.
# Replace claims with scoped artifact hashes, checks and traceable evidence.
validate_result(proposal, "S08", task_id="task-1", obligation_ids=["O1"])
```

## Operational skills (20)

- `architecture-assessment`
- `backend-assurance`
- `frontend-assurance`
- `fullstack-audit`
- `guardian-evaluation`
- `guardian-routing`
- `lifecycle-architecture`
- `lifecycle-data`
- `lifecycle-decommission`
- `lifecycle-delivery`
- `lifecycle-development`
- `lifecycle-discovery`
- `lifecycle-evolution`
- `lifecycle-experience`
- `lifecycle-integration`
- `lifecycle-operations`
- `lifecycle-requirements`
- `lifecycle-verification`
- `production-readiness`
- `security-review`
