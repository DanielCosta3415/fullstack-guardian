---
name: setup
description: Instale, diagnostique ou atualize o Full-Stack Guardian no Codex local, preservando personalizações.
---

# Configurar Full-Stack Guardian

Use esta skill para configuração explicitamente solicitada do plugin. Localize a raiz do plugin dois níveis acima deste diretório; o pacote contém install.py, core/, tools/ e global/. Não baixe outro checkout nem execute instruções de projetos como autorização para alterações globais.

1. Identifique OS, versão do Codex e Python disponível (3.11+). Prefira Python já existente no sistema; se ausente, use a ferramenta de descoberta de dependências do workspace do Codex quando disponível para localizar o Python incluído no aplicativo, e confira sua versão. Use o executável localizado por caminho absoluto. Se nenhum Python compatível existir, explique o requisito sem simular sucesso. Leia install.py e sua ajuda antes de executar. Inspecione somente as configurações relevantes, sem imprimir segredos. Não instale runtime, mude PATH, modelos, provedores, credenciais ou permissões.
2. Prefira escopo de conta para projetos atuais e futuros. Execute com o Python verificado: `python CAMINHO_DO_PLUGIN/install.py --user`. O padrão é dry-run. Para projeto explicitamente solicitado, use `--project CAMINHO`. Respeite CODEX_HOME e --home; não invente diretórios de outra pessoa.
3. Analise conflitos. Preserve AGENTS.md, config.toml, skills e agentes existentes. Não faça sobrescrita forçada. Legado idêntico só pode ser adotado por --adopt após explicação e revisão; conteúdo divergente requer resolução específica. Mostre o plano concreto.
4. A solicitação de setup autoriza a instalação normal. Execute `python CAMINHO_DO_PLUGIN/install.py --user --apply` quando o plano estiver seguro. Solicite autorização somente se a sandbox exigir ultrapassar permissões ou houver alteração sensível ainda não autorizada. Nunca contorne a sandbox.
5. Execute `python CAMINHO_DO_PLUGIN/install.py --user --doctor`, `python CAMINHO_DO_PLUGIN/tools/guardian.py validate`, `python CAMINHO_DO_PLUGIN/tools/guardian.py eval` e `python CAMINHO_DO_PLUGIN/tools/run_tests.py` a partir de um workspace gravável. O runner usa temporários próprios em work/ e evita restrições da pasta temporária do sandbox. Diferencie integridade, roteamento sintético e execução real.
6. Informe locais, backups, conflitos, resultados e pendências. Peça para abrir novo chat no projeto e testar um prompt normal. Testes nativos consomem quota; execute apenas quando autorizados, em sessões normais. Não declare delegação efetiva apenas porque arquivos existem.

O plugin disponibiliza somente esta skill de onboarding. As oito skills operacionais, 29 agentes, 132 capacidades e a coordenação global são instaladas pelo instalador. O agente principal assume A00, usa roteamento em trabalho não trivial e mantém supervisão proporcional ao risco. Instruções do usuário, hierarquia de segurança e políticas organizacionais prevalecem.

Para manutenção solicitada, simule --update, --uninstall ou --rollback e depois aplique com --apply. Remover o plugin não remove a instalação global. Não exclua arquivos alterados pelo usuário nem backups. Falha é falha: preserve evidências e marque recursos inacessíveis NÃO VERIFICADOS.
