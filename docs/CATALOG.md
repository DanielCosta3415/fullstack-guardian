# Generated catalog

Version: 2.2.0-dev.3

Availability is not installation, native loading, or correctness. Model policy inherits by default.

Reviewed source of truth: `core/contracts-catalog-v1.json` contains typed instructions and metadata. `python -B tools/guardian_catalog.py --write` generates the 39 TOMLs, core metadata and pack manifests; it never imports profile edits or writes user configuration. Review canonical changes and expected SHA-256 values before generation.

| ID | Role | Kind | Reviewer | Profile SHA-256 |
|---|---|---|---|---|
| A00 | guardian_engineering_orchestrator | core | G01 | 754925fdbc81e2941b99905d6c4f0bd9c2c735e5f45b0adbf55b3e0ed85a5879 |
| S01 | guardian_product_discovery | core | G01 | 2c0a7068a78ed1ff1c5ef098f40bbba6ff0ca0c9777d44c7dad12a482214ca81 |
| S02 | guardian_requirements_engineer | core | G01 | ee0b0c8c0dc153a2da06a1d80af6bdbd53c9ba9d8793f7c885877e25904c7369 |
| S03 | guardian_solutions_architect | core | G01 | 9135728afdc668c879caaed953a98b1d089bc32ee7795675b48aa5bf987732d1 |
| S04 | guardian_frontend_architect | core | G01 | 32e15ba62836822bd4145135e2aec25b06edfbc338e2ca089ad121bacef3d99e |
| S05 | guardian_frontend_engineer | core | G01 | 3ac23a39cb6b9a3f13690d57f2fb1a4af50eb9179f4eff268edc8bb60ef4a7f7 |
| S06 | guardian_ux_accessibility | core | G01 | 3587c742490c7d987f3a2a37cb0a4c116670568b18dc1bffadca92f18ebc524f |
| S07 | guardian_web_performance | core | G01 | b4c3f015491797c2ecff34d768eb34cfba6ebd93afec31e2d91032f2efa89098 |
| S08 | guardian_backend_domain | core | G01 | e99ca1972ccd0ba44f641f5eedb96204bf438019dc33d5426c4f3560ccafd75d |
| S09 | guardian_api_integration | core | G01 | 8d0b429d72401fa611553e1402989549acf45e0725f9e9f863c0c03ceca16057 |
| S10 | guardian_distributed_concurrency | core | G01 | 28f18959a6a1ee3afad3672826d40b3cdb34757bdd954a55eeac2d88a0a08d3f |
| S11 | guardian_database_transactions | core | G01 | 12ce9cecc9988fe3af4e390adacc34b8e5e1c9909396647f95e62fc2bfb5ce73 |
| S12 | guardian_data_governance | core | G01 | e34d4fac522ea36a0caed207c47fca99f7bd5b8319c9257ae6568465f30ef6f5 |
| S13 | guardian_appsec | core | G01 | 720e51f71efadbf289fa3a4a58d95406a233edbe861a3c320802e105689e419f |
| S14 | guardian_iam_privacy | core | G01 | f580032b57314bf5beffb5fc11d3b3d467b16d60898b2d57a0cf23c37953a57f |
| S15 | guardian_cloud_supply_security | core | G01 | 62002089ae1650f6c2f316d66007dee6394c31186a988e7082dd982e32bedb6e |
| S16 | guardian_quality_architect | core | G01 | ae8cf90914fc82f68aab5233588541d56a29f59a49ae58a829b33c1a2bd15d04 |
| S17 | guardian_frontend_qa | core | G01 | 38e10d2230795de97b85bb97b9e83224be66a8d2b5eaeb0d516f564da7b3cad8 |
| S18 | guardian_backend_qa | core | G01 | 210d79859061983d77a75655694368fd595db523c0b4553f6752098175390c17 |
| S19 | guardian_performance_capacity | core | G01 | 92f2c8ac811dc67221bf82da235d3d2dc62dd7a3b6894c8bba7c7b23d3a980c3 |
| S20 | guardian_sre_resilience | core | G01 | 6e5842e36d69113c55dab72b872ab4a80063fab6a4d665149495a1bd2313b572 |
| S21 | guardian_observability | core | G01 | 8d156b95f315fe7657793c821958ab506fa5b29e71270fda86c89638bac1c39b |
| S22 | guardian_cloud_platform | core | G01 | f613b7c26306b93fbd8d74e2aba57baea6e9f316d2ac05eccdafb7cdd730f7b6 |
| S23 | guardian_devsecops | core | G01 | d3b6ed69efe3dfd435a7cb20307fe4fa39290de70dc14e07f12d0ce317d4f812 |
| S24 | guardian_maintainability | core | G01 | 5ca7c5a1f0a6db40448260c2f6f248b1dce135a0f310eb338381a479968feb70 |
| S25 | guardian_governance_finops | core | G01 | e570b5f3c596144cde6178ba3dfd7c2aff36e8cfe4365feb1b76ddb2c62706a0 |
| S26 | guardian_ai_assurance | core | G01 | 02ee03b9a5e17e413e783bcc89f4e4f58b3ccf023a0d0851918777cbf8b2d29a |
| G01 | guardian_independent_auditor | core | G02 | ac15b1ccc1e532f49135fcc110305bea24bcf35895b7be7403870d40a4e4a541 |
| G02 | guardian_release_auditor | core | G01 | 2c9dad89fbed5a6fd8d907e694addc5cce6fba8879f664b172fe5aca4bff6a5e |
| pack:ai-systems:guardian_rag_llm_specialist | guardian_rag_llm_specialist | optional | G01 | 648862c6d6a1db59de6b65ae2716e107197a38b88fcb2c6567693e52cced405a |
| pack:api-integration:guardian_api_contract_specialist | guardian_api_contract_specialist | optional | G01 | 126df64914054c53333f9a4fde8b21f761cc72ceac124c18d84de45bbf9153d1 |
| pack:cloud-platform:guardian_cloud_infrastructure_specialist | guardian_cloud_infrastructure_specialist | optional | G01 | 00033c0d7620c1b466f290c2f1eec6c00576fe29ba838d0c39ad1ef1cbb5dea4 |
| pack:data-engineering:guardian_data_migration_specialist | guardian_data_migration_specialist | optional | G01 | 091da3e6882d70ed92985204bf59fc0e2071d16d3f989f5b625d81176b044284 |
| pack:dotnet:guardian_dotnet_runtime_specialist | guardian_dotnet_runtime_specialist | optional | G01 | bd84e8c5a72818ed90fd0c42d36758fa5541d7f8394cff62492de411c808a75e |
| pack:financial-systems:guardian_payment_reliability_specialist | guardian_payment_reliability_specialist | optional | G01 | 35ba4e82b878a019787157952ac159f90bd6a791da93350413c48e9c7ce55cde |
| pack:frontend-experience:guardian_browser_accessibility_specialist | guardian_browser_accessibility_specialist | optional | G01 | fb92c8895aba4cfff85b138497bf1b7df1b75cc59e65f68a7c5ac9638ac9dab8 |
| pack:quality-automation:guardian_contract_test_specialist | guardian_contract_test_specialist | optional | G01 | 99cd8bfa2ca6e25b44e0a55b6a6b4d0555cc85ecbe71ad69400a0d087a2a5e84 |
| pack:security-assurance:guardian_threat_model_specialist | guardian_threat_model_specialist | optional | G01 | e210d30539c716ac4fa15d7bdf4f1f340813a9238b94b1b9a9c8453f1c679807 |
| pack:windows-tooling:guardian_windows_powershell_specialist | guardian_windows_powershell_specialist | optional | G01 | a58c080a8d84ebe8e42a6bdbc2fd854cf8ee1d2c70ba1586eb710754a66c6419 |

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
