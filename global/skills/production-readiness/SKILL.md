---
name: production-readiness
description: Avalie readiness de produção quando uma mudança exige implantação ou passagem por release gate.
---

# production-readiness

1. Verifique testes, segurança, compliance, contratos, capacidade, métricas, alertas, rollback e recuperação.
2. Confirme dados e migrações; exija ensaios de recuperação quando aplicável.
3. G02 emite READY/CONDITIONAL/BLOCKED/UNKNOWN com justificativas e pendências.
4. A emissão não executa deployment e não substitui aprovações humanas.
