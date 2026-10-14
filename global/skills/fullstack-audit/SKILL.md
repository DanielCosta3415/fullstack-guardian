---
name: fullstack-audit
description: Audite integralmente um projeto ou módulo contra capacidades aplicáveis da taxonomia Full-Stack v3.
---

# fullstack-audit

1. Antes de editar, produza inventário, commit-alvo, fluxos principais e contexto dos ambientes.
2. Carregue `core/taxonomy-v3.json` (em `.guardian/core/` ou global) e classifique todas as 132 capacidades como atendido, parcial, não atendido, N/A justificado ou não verificado.
3. Distribua verificações por domínio; não marque `atendido` sem evidências verificáveis.
4. Execute testes não destrutivos autorizados e ferramentas existentes do projeto, sem tocar produção.
5. G01 revisa achados e lacunas. G02 só se houver prontidão de release.
6. Gere relatório com severidade, referência, reprodução, plano de remediação e riscos residuais.
