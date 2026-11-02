# Generated catalog

Version: 2.3.0

Availability is not installation, native loading, or correctness. Model policy inherits by default.

Reviewed sources: `core/contracts-catalog-v1.json` owns identity/base instructions and metadata; `core/professional-contracts-v1.json` owns the professional methods, typed capabilities, routing terms, required/conditional/optional tool needs, handoffs and unmeasured qualification. The appended professional instruction must exactly match the renderer; neither generated TOMLs nor derived playbooks can rebaseline the canonical sources. `python -B tools/guardian_catalog.py --write` generates 39 TOMLs, core metadata, ten pack manifests and the compatibility playbook. It never writes user configuration or model/sandbox permissions.

| ID | Role | Kind | Reviewer | Profile SHA-256 |
|---|---|---|---|---|
| A00 | guardian_engineering_orchestrator | core | G01 | 9460b63b02288394a8d1cebefbe1a6428e7f1f165877c7be740a4748ce33a936 |
| S01 | guardian_product_discovery | core | G01 | 5e48459a6e8085088f8ae5349d0244e5ad5e3ffc2532d6864814270b8e97e25f |
| S02 | guardian_requirements_engineer | core | G01 | f341ed25cbcfa607687260cd28ad9811f9c6868ddab640a1b4cd3e23555293b2 |
| S03 | guardian_solutions_architect | core | G01 | 29b5d23d8542117b1d2e352ee0ca4fd73b6c5bb98812b0b838bf60d61dd5ed86 |
| S04 | guardian_frontend_architect | core | G01 | 787c027f1cbe9c8f7f4d0ec8c7e3662c10a207844b08c2f615a81406b414f383 |
| S05 | guardian_frontend_engineer | core | G01 | 5b82e8f9584230f8ec7b204c47dba3b369e176fff400c88e6bfc7a309621bbcf |
| S06 | guardian_ux_accessibility | core | G01 | 281c9a295f837412e81e71f26c045fd11890bb137a8364b54ca9398875550193 |
| S07 | guardian_web_performance | core | G01 | 4272b21ad83f4f7daf7ff6375f276018082c123a824e7e4e422bad4c348cd66d |
| S08 | guardian_backend_domain | core | G01 | 394c22f7d925e07218bf67301c9e6bcd6062e236c84586a072b799f9caa27e39 |
| S09 | guardian_api_integration | core | G01 | b00b590b9b583340d4d7a65cf40ca455b500636fc6629b84dbb6767f3214a54e |
| S10 | guardian_distributed_concurrency | core | G01 | 43e87e87c4a57f3af2e19c2518ce698875623440979e45198266512cf04b4d99 |
| S11 | guardian_database_transactions | core | G01 | 85f58edb1173343305dfab3fcbd4d1474b0da21961e805c482ce74025f0c0a65 |
| S12 | guardian_data_governance | core | G01 | 745f1ab8410e9983256f89ce10f120c09c077ba5f62cc055bab2360d260e61b9 |
| S13 | guardian_appsec | core | G01 | 0417134e4d6df11ca8e0a7ef4449dd1dee8cabb19233565a52450d5e1ec9fbb1 |
| S14 | guardian_iam_privacy | core | G01 | 9ad2972dc74015971232e27804a53489c1d5f3bb71fc288b47185abc474fceb8 |
| S15 | guardian_cloud_supply_security | core | G01 | 7676a8458f1a9405d95e81343185a493d41281503e7c4a5f624c4fe2b41882d4 |
| S16 | guardian_quality_architect | core | G01 | 0bff7d7b1654d078eceb1d38f276acab92216345ce6a13329b9e2051b8fa13b0 |
| S17 | guardian_frontend_qa | core | G01 | f230ced64265c3c32fdc11e3eb3d5b3f9123d1e1b372ab11a89504bc606209a7 |
| S18 | guardian_backend_qa | core | G01 | bd2c1cd377b051bfd1cdee5806875292d531f543617831144892cac39ee9ad3d |
| S19 | guardian_performance_capacity | core | G01 | 40def0a961dcb71e820c95e40d0e64635c3679a15ef408716a730617f5aed0ce |
| S20 | guardian_sre_resilience | core | G01 | 5f154f17a04857d18dd0809e59211413404c6ac9370a98b2b1cc73fa87e54de6 |
| S21 | guardian_observability | core | G01 | 69e2a03953dd2e047f0e7e8bbf20b7b5677c928855eb65b0a3fb99ab8674b950 |
| S22 | guardian_cloud_platform | core | G01 | db26aa2bd96fb618f8955c36f3012069b1a05c9aae82f3079ef245b823e0e37e |
| S23 | guardian_devsecops | core | G01 | 21ecd26d6e86a5021bc271fe8db71491d7b9ee95f4a5a786c6cbd0e9f9db7097 |
| S24 | guardian_maintainability | core | G01 | 94b21a55f75514616dccd98c05db7c072961090d38e2eb8101cf6b22fc59cb08 |
| S25 | guardian_governance_finops | core | G01 | df57d0c6e57b98f7d8255474e06e8815239a3e10bef51854eb125749303c80f8 |
| S26 | guardian_ai_assurance | core | G01 | dca06a3b340c8010697fb3fddde39b07109ef6d70a82d1bfc1a1b14c33df6f7a |
| G01 | guardian_independent_auditor | core | G02 | 9050b90db7702584a864a4f06b61643972056dde94f31f35ca0a8cbc400fc414 |
| G02 | guardian_release_auditor | core | G01 | 45f20a967f2d3a8c277504ba87f08c2b34cb8026dfb5aa2245f4a59bd731d21e |
| pack:ai-systems:guardian_rag_llm_specialist | guardian_rag_llm_specialist | optional | G01 | 842bd72912b35f948121770ac0923bcd2fbe4f3fc781a4181d5989f3e5104e21 |
| pack:api-integration:guardian_api_contract_specialist | guardian_api_contract_specialist | optional | G01 | c3947d4681f82248f0afaa8e54debd36871581f6f50428916641484a369a9b60 |
| pack:cloud-platform:guardian_cloud_infrastructure_specialist | guardian_cloud_infrastructure_specialist | optional | G01 | 5622acdd7c193e15b2d7b0af99e126e754e0df5d24b283e7fdd8cd661d697825 |
| pack:data-engineering:guardian_data_migration_specialist | guardian_data_migration_specialist | optional | G01 | 8674ff639c076e2cbca9dc9dc315f3411d50cd5fc02ea7029ee305dfb78e1ad5 |
| pack:dotnet:guardian_dotnet_runtime_specialist | guardian_dotnet_runtime_specialist | optional | G01 | 96e02e99d6dfd8055a49753f81b0608198d60b90d42d5f1ac68a51f04e79123c |
| pack:financial-systems:guardian_payment_reliability_specialist | guardian_payment_reliability_specialist | optional | G01 | 37b75ab69f209bfff73b98c61d59a09b2f1096f8013dfa6427532e47e81d2263 |
| pack:frontend-experience:guardian_browser_accessibility_specialist | guardian_browser_accessibility_specialist | optional | G01 | 293d02565c2dccf25e59c2c62f4ea872aef66966442b58b62935ecf4ba324754 |
| pack:quality-automation:guardian_contract_test_specialist | guardian_contract_test_specialist | optional | G01 | 779443cbb36a6f301e91399e72c817f16260bd0cf671dbba5b527982fea6a5c8 |
| pack:security-assurance:guardian_threat_model_specialist | guardian_threat_model_specialist | optional | G01 | 2ab6289489c155bd0defe522b93213b33913d334ed446a9e44c554e61a4b9471 |
| pack:windows-tooling:guardian_windows_powershell_specialist | guardian_windows_powershell_specialist | optional | G01 | 2402175e580492d8b9642a05082f9c8c74b9571e88de9c6fe372b56bfb777977 |

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
| A00 | audit, build, remediate, explore | 0 | project_artifact_reader | 1.1.0 |
| S01 | audit, build, remediate, explore | 8 | project_artifact_reader | 1.1.0 |
| S02 | audit, build, remediate, explore | 17 | project_artifact_reader | 1.1.0 |
| S03 | audit, build, remediate, explore | 29 | project_artifact_reader | 1.1.0 |
| S04 | audit, build, remediate, explore | 33 | project_artifact_reader | 1.1.0 |
| S05 | audit, build, remediate, explore | 13 | project_artifact_reader | 1.1.0 |
| S06 | audit, build, remediate, explore | 6 | project_artifact_reader | 1.1.0 |
| S07 | audit, build, remediate, explore | 2 | project_artifact_reader | 1.1.0 |
| S08 | audit, build, remediate, explore | 3 | project_artifact_reader | 1.1.0 |
| S09 | audit, build, remediate, explore | 2 | project_artifact_reader | 1.1.0 |
| S10 | audit, build, remediate, explore | 26 | project_artifact_reader | 1.1.0 |
| S11 | audit, build, remediate, explore | 9 | project_artifact_reader | 1.1.0 |
| S12 | audit, build, remediate, explore | 13 | project_artifact_reader | 1.1.0 |
| S13 | audit, build, remediate, explore | 12 | project_artifact_reader | 1.1.0 |
| S14 | audit, build, remediate, explore | 11 | project_artifact_reader | 1.1.0 |
| S15 | audit, build, remediate, explore | 13 | project_artifact_reader | 1.1.0 |
| S16 | audit, build, remediate, explore | 20 | project_artifact_reader | 1.1.0 |
| S17 | audit, build, remediate, explore | 5 | project_artifact_reader | 1.1.0 |
| S18 | audit, build, remediate, explore | 5 | project_artifact_reader | 1.1.0 |
| S19 | audit, build, remediate, explore | 5 | project_artifact_reader | 1.1.0 |
| S20 | audit, build, remediate, explore | 8 | project_artifact_reader | 1.1.0 |
| S21 | audit, build, remediate, explore | 3 | project_artifact_reader | 1.1.0 |
| S22 | audit, build, remediate, explore | 3 | project_artifact_reader | 1.1.0 |
| S23 | audit, build, remediate, explore | 3 | project_artifact_reader | 1.1.0 |
| S24 | audit, build, remediate, explore | 8 | project_artifact_reader | 1.1.0 |
| S25 | audit, build, remediate, explore | 6 | project_artifact_reader | 1.1.0 |
| S26 | audit, build, remediate, explore | 1 | project_artifact_reader | 1.1.0 |
| G01 | audit, explore | 132 | project_artifact_reader | 1.1.0 |
| G02 | audit, explore | 0 | project_artifact_reader | 1.1.0 |
| pack:ai-systems:guardian_rag_llm_specialist | audit, build, remediate, explore | 12 | project_artifact_reader | 1.1.0 |
| pack:api-integration:guardian_api_contract_specialist | audit, build, remediate, explore | 11 | project_artifact_reader | 1.1.0 |
| pack:cloud-platform:guardian_cloud_infrastructure_specialist | audit, build, remediate, explore | 9 | project_artifact_reader | 1.1.0 |
| pack:data-engineering:guardian_data_migration_specialist | audit, build, remediate, explore | 15 | project_artifact_reader | 1.1.0 |
| pack:dotnet:guardian_dotnet_runtime_specialist | audit, build, remediate, explore | 15 | project_artifact_reader | 1.1.0 |
| pack:financial-systems:guardian_payment_reliability_specialist | audit, build, remediate, explore | 18 | project_artifact_reader | 1.1.0 |
| pack:frontend-experience:guardian_browser_accessibility_specialist | audit, build, remediate, explore | 18 | project_artifact_reader | 1.1.0 |
| pack:quality-automation:guardian_contract_test_specialist | audit, build, remediate, explore | 8 | project_artifact_reader | 1.1.0 |
| pack:security-assurance:guardian_threat_model_specialist | audit, build, remediate, explore | 14 | project_artifact_reader | 1.1.0 |
| pack:windows-tooling:guardian_windows_powershell_specialist | audit, build, remediate, explore | 9 | project_artifact_reader | 1.1.0 |

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
