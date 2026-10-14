# Distribuição, instalação e manutenção

O repositório público e as releases são os canais de distribuição. O marketplace local aponta para o pacote na raiz do repositório. Isso não significa publicação na loja pública universal de plugins.

## Fluxo do usuário

Adicione `DanielCosta3415/fullstack-guardian` como marketplace GitHub, instale `fullstack-guardian` e execute setup. A skill deve encontrar o instalador dentro do plugin, diagnosticar o ambiente, simular, resolver conflitos preservando personalizações, aplicar e executar doctor. Não precisa clonar um segundo repositório. Como alternativa, extraia o ZIP da release e execute o instalador.

A disponibilidade do controle de marketplace depende do cliente e das políticas da organização. Consulte a [documentação oficial de plugins](https://developers.openai.com/plugins/build/plugins). A [documentação de subagentes](https://learn.chatgpt.com/docs/agent-configuration/subagents) descreve a execução nativa. O instalador não habilita ferramentas ausentes nem contorna políticas.

## Contrato do instalador

- `--user`: integração para a conta; `--project CAMINHO`: integração em um projeto.
- `--home CAMINHO`: diretório home alternativo (Codex em CAMINHO/.codex e skills em CAMINHO/.agents/skills) para diagnóstico ou instalação isolada.
- Sem `--apply`, apenas plano e diagnóstico.
- `--update`, `--uninstall` e `--rollback`: manutenção baseada no recibo existente.
- `--adopt`: adoção explícita de legado idêntico; divergências continuam protegidas.
- `--doctor`: confere integridade e configuração; não comprova execução do modelo.
- Recibo: `guardian-install.json` na raiz Codex escolhida. Preserve os backups informados.

Revise o plano antes de aplicar. Alterações locais posteriores são protegidas por verificações de integridade. Não remova backups para resolver conflitos; compare arquivos e preserve as personalizações deliberadamente.

## Requisitos

Python 3.11+; Codex compatível com agentes personalizados, skills e delegação; execução local; permissões para gravar na raiz escolhida. Ferramentas das stacks dos projetos são instaladas separadamente. Sem runtime embutido, bibliotecas externas obrigatórias, modelo fixo ou credenciais compartilhadas.

Os lançadores apenas localizam Python e repassam argumentos ao instalador. Windows: `powershell -File installer/Install.ps1 --user`. Linux/macOS: `bash install.sh --user`. Se a política de execução do Windows bloquear scripts, use `py -3 install.py --user`; não é necessário relaxar a política global.

## Processo de release

Execute unitários, validate, eval, testes isolados de instalação e empacotamento. Inspecione a lista e o scanner do pacote; confirme que não há credenciais, caminhos pessoais, sessões ou logs brutos. Publique o ZIP e SHA-256 da mesma revisão Git. A CI roda em três sistemas e três versões de Python. Os workflows de release preparam artefatos; publicação é uma ação explícita do mantenedor.

As ações oficiais do GitHub estão fixadas pelos SHAs resolvidos dos respectivos tags em 2026-10-14. Atualizações devem rever upstream e executar novamente os checks.

## Privacidade

O instalador e roteador são locais; não fazem telemetria. O uso normal do Codex segue as configurações e políticas da conta. Testes nativos opt-in usam o Codex autenticado do usuário e consomem quota. Não publique resultados com informações de projetos privados.
