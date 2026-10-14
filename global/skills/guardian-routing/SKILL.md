---
name: guardian-routing
description: Classifique um pedido de desenvolvimento ou auditoria e selecione especialistas guardiões quando a tarefa envolver mais de um domínio.
---

# guardian-routing

1. Leia `AGENTS.md` e escolha o caminho de execução do roteador (local `.guardian/tools/guardian.py` ou global no diretório Codex).
2. Execute `python <roteador> route --project . --prompt "<resumo do pedido>"` sem incluir segredos no argumento. Se necessário use `--prompt-file` com arquivo controlado.
3. Trate resultado como triagem baseada em regras: confirme com código, requisitos e criticidade antes de delegar.
4. Acione somente os agentes justificados; declare especialidades não convocadas e razão quando pertinente.
5. Separe implementação de auditoria; escalone G01 nos casos relevantes e G02 quando houver liberação.
6. Registre selecionados, motivos e evidências em `guardian-run.json` apenas quando autorizado.
