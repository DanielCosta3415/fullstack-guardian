# Generated catalog

Version: 2.2.1

Availability is not installation, native loading, or correctness. Model policy inherits by default.

Reviewed sources: `core/contracts-catalog-v1.json` owns identity/base instructions and metadata; `core/professional-contracts-v1.json` owns the professional methods, typed capabilities, routing terms, required/conditional/optional tool needs, handoffs and unmeasured qualification. The appended professional instruction must exactly match the renderer; neither generated TOMLs nor derived playbooks can rebaseline the canonical sources. `python -B tools/guardian_catalog.py --write` generates 39 TOMLs, core metadata, ten pack manifests and the compatibility playbook. It never writes user configuration or model/sandbox permissions.

| ID | Role | Kind | Reviewer | Profile SHA-256 |
|---|---|---|---|---|
| A00 | guardian_engineering_orchestrator | core | G01 | 921d2e09f0f9a6779df2fa65fc24c223f97ac7651def1f9a1f672f031a02f732 |
| S01 | guardian_product_discovery | core | G01 | 23fc07371774c144039fa5a6e1d53400bc4b0f2a6766c5fb681b93c0e27df9b9 |
| S02 | guardian_requirements_engineer | core | G01 | c4d229dc5fe2891d90f2a370f638743003d046c40d64b34d8276f72e0a4b93c9 |
| S03 | guardian_solutions_architect | core | G01 | c50bad9a6b76a5d171934790f9f1d55444d90407209da957363a5b1696a3b12d |
| S04 | guardian_frontend_architect | core | G01 | 6857f407d92f3249ac3298b71a3e907655e767730efd53de948323972d30ceb3 |
| S05 | guardian_frontend_engineer | core | G01 | b27195871e86fe1c9026fd051e001ace62c11b6b8144addc79c174b38ea5f6fd |
| S06 | guardian_ux_accessibility | core | G01 | de6202f85d39c0aeb455ce1903c3eb3a27cfd8aea19cb14bb305e6d27266d802 |
| S07 | guardian_web_performance | core | G01 | 672f4705ad8c2c7b6794481dc94cde25912995fa8328ece520e2d63118063328 |
| S08 | guardian_backend_domain | core | G01 | 2b31da4e41977b399d599499da6cb5e878825935103f9428552c662779babda7 |
| S09 | guardian_api_integration | core | G01 | 5c355baf5066b15971ca2453e46d6113cdc1188578affa59dcdabc1b38a7fff1 |
| S10 | guardian_distributed_concurrency | core | G01 | de4a233f7d3f92ba0c65557279e1907a6f85550e0d3c37813924cdeb7488d375 |
| S11 | guardian_database_transactions | core | G01 | bad111b486b78e4bac12d330128e80f27744f60fa0841127a1014ef13ddd8455 |
| S12 | guardian_data_governance | core | G01 | 57b0d0f68f22b561586f58edeccd5c9ae7daef3389ca6ce74756d5a2ada43319 |
| S13 | guardian_appsec | core | G01 | c0b9350d5c695044a460f47bb12f417b8167848a777da03a3682a9da71460b9d |
| S14 | guardian_iam_privacy | core | G01 | e96bd8d23094aa6324395915870d8c95e72fbab9c4c73f407a9ad52d9970d99c |
| S15 | guardian_cloud_supply_security | core | G01 | 9e2ba9fc2b0e223639812419951b535e3cee5d24cf8adb620a0f7062354f7a71 |
| S16 | guardian_quality_architect | core | G01 | 195ebc2bfff9c69ef6e1a40432ad8fc395f9a4d246eba2d04f48f704f4d5d297 |
| S17 | guardian_frontend_qa | core | G01 | 8277ac4f7f3033193f43560db015da6a5c7f37164e420532a563994112f1e090 |
| S18 | guardian_backend_qa | core | G01 | eeaa61de25603d0de7a2af121592f4e16f0ebb4030c55138884e229e6cb25015 |
| S19 | guardian_performance_capacity | core | G01 | b10c70a3a3d195ff7dd02d76eb4dbae4adcf43208714bb52a46c40fb68216dad |
| S20 | guardian_sre_resilience | core | G01 | cc24e50beabc4c64c6ed00cdd1f6167ecdbb1d8558b442e3f283627510700c08 |
| S21 | guardian_observability | core | G01 | 18b3e8f825a2899f61fa2eda56bbfa5df7e89ace7d1e77759fc5c2c389e10b19 |
| S22 | guardian_cloud_platform | core | G01 | 9685ae6780bf4a1eca7df84a0b42b05ff1a16dba633bf88a69c1d44956f70b06 |
| S23 | guardian_devsecops | core | G01 | 947e659b8e7440b924b0e8c85c9d4b4bd0c4bcff1963bfe092440a29fa9af993 |
| S24 | guardian_maintainability | core | G01 | 73760a66ca076e291c8e49cc6c7949a5759cbbbf6f0b82eaf06c9eecd493e402 |
| S25 | guardian_governance_finops | core | G01 | b49e62208a1fb6fa95b1eab043f5e81a05411ec12db640dbbfeb74d07c1b5455 |
| S26 | guardian_ai_assurance | core | G01 | 5a4918d19502cab9d3e3f4e9f08754c6866767ce803f008ee1bb352b41f32252 |
| G01 | guardian_independent_auditor | core | G02 | abdac11de0e5d8b1710a4c4dd7f34dcafd4b45e49e50b9a2437a4e2fcd2db1b1 |
| G02 | guardian_release_auditor | core | G01 | ded5b175186e1a3703dd89df3542e1a695bca19d94e02215a1a343e4a3907cdd |
| pack:ai-systems:guardian_rag_llm_specialist | guardian_rag_llm_specialist | optional | G01 | 419277779d05e25eb18c22d066514d391954e7788136a770ac7121197dd7b430 |
| pack:api-integration:guardian_api_contract_specialist | guardian_api_contract_specialist | optional | G01 | 6a015ca7e504cf9196fc31526f0544a864253931ac07518e84b1fdfe0c0b0027 |
| pack:cloud-platform:guardian_cloud_infrastructure_specialist | guardian_cloud_infrastructure_specialist | optional | G01 | b43c2a3f9003e77894d8c6b0bfd495ccd53cfa2a55a7a74c30988dea0ded5406 |
| pack:data-engineering:guardian_data_migration_specialist | guardian_data_migration_specialist | optional | G01 | 9196b70a17d3cd23afee5bb048a1bf24ef65bf4d279cc72b5e6713c8c46c036c |
| pack:dotnet:guardian_dotnet_runtime_specialist | guardian_dotnet_runtime_specialist | optional | G01 | 1978c4b36d97dfc21c5897b28cd606496c49c183f34cdbdcd470a9b849e70a6d |
| pack:financial-systems:guardian_payment_reliability_specialist | guardian_payment_reliability_specialist | optional | G01 | 48bda262d0ee1ef67cd58e57a3151b30130dc3e8d906b3d4595fcd6789c079a6 |
| pack:frontend-experience:guardian_browser_accessibility_specialist | guardian_browser_accessibility_specialist | optional | G01 | 5da0a7a89402be513c7cb43162f93dfbbdc3e69e68a688a3cfd31b39e3f43091 |
| pack:quality-automation:guardian_contract_test_specialist | guardian_contract_test_specialist | optional | G01 | b7a259399ccdf234e2eb207b8edb6e77b805081c488086bb12da2fb293eb9607 |
| pack:security-assurance:guardian_threat_model_specialist | guardian_threat_model_specialist | optional | G01 | bd987b7e68d152d7d9d1ba16a48d86295517f55270d9f939c239cbc0ff7776da |
| pack:windows-tooling:guardian_windows_powershell_specialist | guardian_windows_powershell_specialist | optional | G01 | 1beff331f76c405409f6945329e3d1345fbde27039b01cecfb9ecd11c8994cf9 |

## Nomes profissionais oficiais (39)

Os nomes abaixo são rótulos de apresentação em português. Identificadores `guardian_*`, responsabilidades, roteamento, modelos e permissões permanecem estáveis. Fonte dos nomes: `core/role-display-names-v1.json`; o gerador verifica sua correspondência com os títulos principais e os 39 perfis canônicos.

| Identificador técnico | Nome profissional |
|---|---|
| guardian_engineering_orchestrator | Orquestrador de Engenharia |
| guardian_product_discovery | Especialista em Descoberta de Produto |
| guardian_requirements_engineer | Engenheiro de Requisitos |
| guardian_solutions_architect | Arquiteto de Soluções |
| guardian_frontend_architect | Arquiteto Front-End |
| guardian_frontend_engineer | Engenheiro Front-End |
| guardian_ux_accessibility | Especialista em UX e Acessibilidade |
| guardian_web_performance | Especialista em Desempenho Web |
| guardian_backend_domain | Engenheiro Back-End e Especialista de Domínio |
| guardian_api_integration | Especialista em Integração de APIs |
| guardian_distributed_concurrency | Especialista em Concorrência e Sistemas Distribuídos |
| guardian_database_transactions | Especialista em Bancos de Dados e Transações |
| guardian_data_governance | Especialista em Governança de Dados |
| guardian_appsec | Especialista em Segurança de Aplicações |
| guardian_iam_privacy | Especialista em Identidade, Acesso e Privacidade |
| guardian_cloud_supply_security | Especialista em Segurança Cloud e Cadeia de Fornecimento de Software |
| guardian_quality_architect | Arquiteto de Qualidade |
| guardian_frontend_qa | Engenheiro de Qualidade Front-End |
| guardian_backend_qa | Engenheiro de Qualidade Back-End |
| guardian_performance_capacity | Especialista em Desempenho e Capacidade |
| guardian_sre_resilience | Engenheiro de Confiabilidade e Resiliência — SRE |
| guardian_observability | Especialista em Observabilidade |
| guardian_cloud_platform | Engenheiro de Plataforma e Infraestrutura Cloud |
| guardian_devsecops | Engenheiro DevSecOps |
| guardian_maintainability | Especialista em Manutenibilidade e Evolução de Software |
| guardian_governance_finops | Especialista em Governança e FinOps |
| guardian_ai_assurance | Especialista em Qualidade e Riscos de IA |
| guardian_independent_auditor | Auditor Independente |
| guardian_release_auditor | Auditor de Prontidão para Liberação |
| guardian_rag_llm_specialist | Especialista em RAG e LLM |
| guardian_api_contract_specialist | Especialista em Contratos de API |
| guardian_cloud_infrastructure_specialist | Especialista em Infraestrutura Cloud |
| guardian_data_migration_specialist | Especialista em Migração de Dados |
| guardian_dotnet_runtime_specialist | Especialista em Runtime .NET e ASP.NET Core |
| guardian_payment_reliability_specialist | Especialista em Confiabilidade de Pagamentos |
| guardian_browser_accessibility_specialist | Especialista em Navegador e Acessibilidade |
| guardian_contract_test_specialist | Especialista em Testes de Contratos |
| guardian_threat_model_specialist | Especialista em Modelagem de Ameaças |
| guardian_windows_powershell_specialist | Especialista em Windows e PowerShell |

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
