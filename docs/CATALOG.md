# Generated catalog

Version: 2.2.1

Availability is not installation, native loading, or correctness. Model policy inherits by default.

Reviewed sources: `core/contracts-catalog-v1.json` owns identity/base instructions and metadata; `core/professional-contracts-v1.json` owns the professional methods, typed capabilities, routing terms, required/conditional/optional tool needs, handoffs and unmeasured qualification. The appended professional instruction must exactly match the renderer; neither generated TOMLs nor derived playbooks can rebaseline the canonical sources. `python -B tools/guardian_catalog.py --write` generates 39 TOMLs, core metadata, ten pack manifests and the compatibility playbook. It never writes user configuration or model/sandbox permissions.

| ID | Role | Kind | Reviewer | Profile SHA-256 |
|---|---|---|---|---|
| A00 | guardian_engineering_orchestrator | core | G01 | 2c05bd2f6fcf7a24eff286ec6f94f5ecf2372789c0c65eeca5a7c1a2d6b84924 |
| S01 | guardian_product_discovery | core | G01 | 5b387729e276934604111b2724129fb2a959fa2503d6493b8102fd0a7ded9f23 |
| S02 | guardian_requirements_engineer | core | G01 | 1473fe8254c9057b6ae53d7821d9cad5a94d7776e116124b20d5450962bb8d48 |
| S03 | guardian_solutions_architect | core | G01 | 25eafa8f9b750631639c07284f585e7ef813c3a21141277759edb8c46af0db0f |
| S04 | guardian_frontend_architect | core | G01 | 7487211a311b7aa51596487f9c2d84dbf4c0e4780917e1032368f9f2283bc990 |
| S05 | guardian_frontend_engineer | core | G01 | 267dae63e90ddac7240e7aff7c505caac6e2c7bb010aa7162cc8899807792796 |
| S06 | guardian_ux_accessibility | core | G01 | bc44c1ba60ad5511b7ccfd7aee8f8f72581819a1cbba54d00f5bf7bef9032bed |
| S07 | guardian_web_performance | core | G01 | 2ec90bc237771844bd38daeef4f7fd534e5d6b9af1d990f08fd242aba10ac044 |
| S08 | guardian_backend_domain | core | G01 | 984bf2b343e1fee008f13da2333364a53650166f4378d3a3afd060a55183224d |
| S09 | guardian_api_integration | core | G01 | e0f0b7dd63f4d481d4b983b4ad7535bad76b3364cc78465126478f1563cef3ec |
| S10 | guardian_distributed_concurrency | core | G01 | 6eb405db8d2f35aa64fbe667769da1508f105be6fcf78b32742147e37104ab9f |
| S11 | guardian_database_transactions | core | G01 | 9d954ab503ec14a2b83583078a56748a929e750ca47805097a00233e66e2a6aa |
| S12 | guardian_data_governance | core | G01 | 73c63bc804144fa2b5146b3bde8c527e5adada9e4e0d409098ec1a91c5d41abd |
| S13 | guardian_appsec | core | G01 | 626b6d16f0ae81cfca504c06ecf91b90e58f9bea32583b83a556dd5b7b580b5a |
| S14 | guardian_iam_privacy | core | G01 | ecf5f659f82f045a4a495bbb214c7d247b31a3ae9946270df2cc1c370ce36ae8 |
| S15 | guardian_cloud_supply_security | core | G01 | fd5e99a81446e10d6aec497cb445a994e40711c396a9e472a233b67a3e972427 |
| S16 | guardian_quality_architect | core | G01 | 818a0b5acc93298ec4a7f43b10076a80e87b0e6fbde62f6bbac84d4bbcbff75e |
| S17 | guardian_frontend_qa | core | G01 | 4172b5718fbc9a5d0e5d3fbe362de2e0fde7f3f32321acae46fef9c6e63bbe66 |
| S18 | guardian_backend_qa | core | G01 | b83843eda048b73bfe8157daf289a89af50116bdeab485fcef7d1f10225692b7 |
| S19 | guardian_performance_capacity | core | G01 | 948c2700c69b3c74f3edecaf05e82b87a046252b8281a9bebdb8d89a90ae15fe |
| S20 | guardian_sre_resilience | core | G01 | abeb9bf832dd996c282cb08207679b6df6abfec6cdebee7885e902e5498b07f2 |
| S21 | guardian_observability | core | G01 | b99c681bfbe54565e4f3df7655ff410f41958a369cfbdf479664efd41ece6047 |
| S22 | guardian_cloud_platform | core | G01 | bad1fa06fe0e4a8c765732c37b9ca81794ebd84225343d080d73698e83e82746 |
| S23 | guardian_devsecops | core | G01 | 54d42f5d0f1174c423236f60af71bbffc3856027c48ef3d4c0972836cb247916 |
| S24 | guardian_maintainability | core | G01 | 5f3cc505892c6411825bc617cd7f1f631a164ed2f0138f5e248d1cf3a2fbf722 |
| S25 | guardian_governance_finops | core | G01 | f4694fef36d84d7f5209566c4575fd6401c51b6a1203123c0b3b26251a8c53fa |
| S26 | guardian_ai_assurance | core | G01 | e208e20739e132cf1f05f5c70537474c71e8a6c26704e89091a7670da3177275 |
| G01 | guardian_independent_auditor | core | G02 | 073e9afdbc521740ca8161acb761176ea83d9a1a8ff1f22a0c773be27ca61c65 |
| G02 | guardian_release_auditor | core | G01 | 0fe9fde3ebb4b197b02771fd3fa09ab0d50e61279550c4c5a698d41ba3fb4718 |
| pack:ai-systems:guardian_rag_llm_specialist | guardian_rag_llm_specialist | optional | G01 | 2f37f0276aeeef6b7a4df1b594a474571baad27d47d0df8df97310b595c3c8b4 |
| pack:api-integration:guardian_api_contract_specialist | guardian_api_contract_specialist | optional | G01 | 9755e7e1ca8632ff50b8c1323f14c3e5ee3772755e05b5130ca8bac9b47a8d5d |
| pack:cloud-platform:guardian_cloud_infrastructure_specialist | guardian_cloud_infrastructure_specialist | optional | G01 | 7b341b923153e1d305a7f14db2cde05b893114641e11c6e058481dac1c223095 |
| pack:data-engineering:guardian_data_migration_specialist | guardian_data_migration_specialist | optional | G01 | 68624c6aff3bfa909015cd790a1bbfb00e65842258df6626dff5246c6326335b |
| pack:dotnet:guardian_dotnet_runtime_specialist | guardian_dotnet_runtime_specialist | optional | G01 | 79bcd7236433862ec9fe3c0610be3fea6ec3ca810976a7d966b2cff6166f6855 |
| pack:financial-systems:guardian_payment_reliability_specialist | guardian_payment_reliability_specialist | optional | G01 | 18f9b1a99bdc32b58c859ba02192cbbaf8cba6fe57fd4fe46649c6fe79b07eca |
| pack:frontend-experience:guardian_browser_accessibility_specialist | guardian_browser_accessibility_specialist | optional | G01 | 6bf559fa0ab32d90575cd4017a1345fb8e6d6aee32590c9999f8dd96d2ecc36b |
| pack:quality-automation:guardian_contract_test_specialist | guardian_contract_test_specialist | optional | G01 | 87a3af741bbca6c64d44b4aa97a2b478697b487eba447b06d6b7d3306eedfb6b |
| pack:security-assurance:guardian_threat_model_specialist | guardian_threat_model_specialist | optional | G01 | a0b14a94d686e428412efdb5033b3dd1fbe0ff16170288ab60c543d9355fb820 |
| pack:windows-tooling:guardian_windows_powershell_specialist | guardian_windows_powershell_specialist | optional | G01 | 958f28af5d8d60fd8f43b59a4e38f5097611ee438f87bca7d28db3e3d2c28973 |

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

## Operational skills (21)

- `architecture-assessment`
- `backend-assurance`
- `frontend-assurance`
- `fullstack-audit`
- `guardian-continuation`
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
