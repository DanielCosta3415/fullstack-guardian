---
name: guardian-evaluation
description: Teste ou revise a configuração dos guardiões, roteamento e cobertura da taxonomia.
---

# guardian-evaluation

1. Rode `python <roteador> validate` e `python <roteador> eval`; execute `python -m unittest discover -s tests` quando o pacote estiver disponível.
2. Compare rota sugerida a cenários esperados e reporte falsos negativos, falsos positivos e lacunas.
3. Melhore roteamento somente mediante alteração versionada com regressões automatizadas.
4. Avaliações sintéticas não substituem E2E real do Codex; declare essa limitação.
