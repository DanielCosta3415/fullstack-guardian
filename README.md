# Full-Stack Engineering Guardian System v2.1.0

29 especialistas, oito skills e 132 capacidades para coordenar tarefas de engenharia no Codex com roteamento proporcional à complexidade e ao risco.

**Instalação global para a conta; prompts normais depois da configuração.** O agente principal interpreta o pedido e seleciona especialistas quando necessário. Tarefas simples podem ser resolvidas diretamente. Recomendações do roteador são verificadas pelo agente principal; permissões e instruções dos projetos continuam aplicáveis.

## Instalação mais simples: plugin + configuração guiada

1. No diretório de plugins do seu Codex, adicione o marketplace GitHub `DanielCosta3415/fullstack-guardian` (ou a URL deste repositório).
2. Instale **Full-Stack Guardian**, da fonte **Guardian Marketplace**.
3. Execute a configuração inicial do plugin. Se necessário, peça: **“Configure o Full-Stack Guardian globalmente para minha conta, preserve minhas personalizações e valide a instalação.”**
4. Abra um novo chat no projeto e peça uma tarefa normal.

O plugin contém uma única skill de configuração. Ela instala as oito skills operacionais e os 29 perfis no escopo da conta, evitando duplicação. A instalação do plugin, sozinha, ainda não conclui a integração. Os nomes dos controles podem variar conforme a versão do cliente. Se sua organização restringe marketplaces ou plugins, use o ZIP com autorização local.

Na CLI compatível, os dois primeiros passos também podem ser feitos assim:

```sh
codex plugin marketplace add DanielCosta3415/fullstack-guardian --ref v2.1.0
codex plugin add fullstack-guardian@guardian-marketplace
```

Depois abra o Codex e peça a configuração inicial do plugin. Esse fluxo foi separado da instalação global para permitir revisão e preservação das suas configurações.

## Alternativa sem Git: ZIP da release

Baixe o ZIP em [Releases](https://github.com/DanielCosta3415/fullstack-guardian/releases/latest), confira o SHA-256 publicado, extraia e abra um terminal na pasta extraída. Requer **Python 3.11+** já instalado e Codex com suporte a agentes personalizados e delegação.

```sh
python install.py --user
python install.py --user --apply
python install.py --user --doctor
```

O primeiro comando simula. Revise conflitos antes de aplicar. No Windows, se `python` não estiver disponível, use `py -3` ou:

```powershell
powershell -File installer/Install.ps1 --user
powershell -File installer/Install.ps1 --user --apply
```

No Linux/macOS: `bash install.sh --user`, seguido de `bash install.sh --user --apply`. Os lançadores procuram Python existente; não baixam runtimes, alteram PATH nem pedem privilégios administrativos.

## O que é instalado

| Componente | Escopo da conta |
|---|---|
| 29 perfis de agentes | `~/.codex/agents/` |
| Oito skills operacionais | `~/.agents/skills/` |
| Taxonomia, políticas e roteador | `~/.codex/guardian-system/` |
| Política de coordenação | bloco delimitado em `~/.codex/AGENTS.md` |
| Registro dos agentes e delegação | integração preservadora em `~/.codex/config.toml` |
| Recibo e backups | local informado pelo instalador |

`CODEX_HOME` e `--home` podem alterar a raiz Codex. O instalador preserva configurações, modelos e provedores existentes. Não instala credenciais, não concede permissões e usa apenas a biblioteca padrão do Python. O padrão de quatro subagentes simultâneos só é aplicado quando não existe configuração correspondente.

Para escopo de projeto: `python install.py --project CAMINHO` e depois o mesmo comando com `--apply`. Prefira um único escopo para evitar perfis duplicados.

## Validação e uso

```sh
python tools/guardian.py validate
python tools/guardian.py eval
python -m unittest discover -s tests -v
```

Esses comandos validam arquivos, roteamento e instalador; não executam o modelo. Em um **novo chat**, peça: “Faça uma revisão controlada de um pequeno módulo, selecione um especialista adequado e apresente evidências de execução e revisão.” A execução nativa depende das ferramentas, permissões e quota da sua conta.

Uma suíte nativa portátil está disponível, por adesão explícita:

```sh
python tools/test_native_agents.py
python tools/test_native_agents.py --run --out DIRETORIO_NOVO_DE_EVIDENCIAS
python tools/test_native_agents.py --run --all --out OUTRO_DIRETORIO_NOVO
```

O primeiro comando somente mostra o plano. `--run` usa sua conta autenticada e quota do Codex. O teste padrão executa A00, IAM, G01 e G02; `--all` exige os 29 tipos individualmente. Tudo ocorre em um projeto sintético isolado, com evidências locais. Essas evidências podem conter caminhos e IDs de sessão; revise antes de compartilhá-las.

O roteador usa heurísticas locais e não envia o prompt para uma API. Use resumos sem segredos. Tarefas de alto risco devem envolver revisão independente G01; avaliação de produção usa G02. O sistema não substitui autorização para produção, operações destrutivas ou ações privilegiadas.

## Atualização, remoção e recuperação

```sh
python install.py --user --update
python install.py --user --update --apply
python install.py --user --uninstall
python install.py --user --uninstall --apply
python install.py --user --rollback
python install.py --user --rollback --apply
```

Todas as operações simulam por padrão. Arquivos modificados posteriormente são tratados como conflitos; não use sobrescrita forçada. `--adopt` é somente para adoção explícita de arquivos legados idênticos, após revisão do dry-run. Remover o plugin não remove automaticamente a integração global: use a desinstalação acima.

## Estado de compatibilidade

Os 29 papéis foram executados individualmente em ambiente Windows com Codex desktop 26.1007.71326 e CLI 0.162 alpha. Isso valida casos controlados, não todas as capacidades nem todos os ambientes. A release adiciona testes de instalação isolada e CI para Windows, Linux e macOS com Python 3.11–3.13. Consulte os resultados reais no GitHub e [VALIDATION](docs/VALIDATION.md); não considere uma matriz configurada como uma matriz aprovada.

[Distribuição e manutenção](docs/DISTRIBUTION.md) · [Notas da release](RELEASE_NOTES.md) · [Documentação técnica](docs/) · [Issues](https://github.com/DanielCosta3415/fullstack-guardian/issues)

MIT © Daniel Lopes da Costa. Projeto independente; sem afiliação oficial com a OpenAI.

English: Local, customization-preserving Codex setup for 29 specialist roles, eight skills and 132 capabilities. Install the plugin and run onboarding, or use the release ZIP. Python 3.11+ required; native delegation depends on your Codex client, permissions and quota.
