---
name: architecture-assessment
description: Avalie uma arquitetura existente e a arquitetura proporcionalmente necessária antes de mudanças estruturais ou novas soluções.
---

# architecture-assessment

1. Execute `python <roteador> inspect --project .`; dados são heurísticos, não comprovam runtime ou segurança.
2. Levante As-Is por código, configuração, integrações e decisões documentadas.
3. Declare metas To-Be, restrições, riscos, carga e critérios de aceitação.
4. Classifique separadamente complexidade (simples/intermediária/robusta), criticidade (baixa/média/alta/crítica) e maturidade observada.
5. Liste incertezas e lacunas; proponha a opção mais simples que satisfaça requisitos; compare alternativas e registre ADR se necessário.
6. Escalone S03, S10, S13, S19 ou S20 apenas se necessário.

7. Para calcular To-Be, use um perfil preenchido com evidências verificáveis (`project-template/guardian-profile.template.json` como modelo) e execute `python <roteador> assess --project . --profile <arquivo.json>`. Com lacunas, devolva `undetermined`; não invente pontuações.
