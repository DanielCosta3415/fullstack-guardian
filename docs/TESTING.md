# Testes do Guardian 2.1.0

Execute `python -m unittest discover -s tests -v`, `python tools/guardian.py validate` e `python tools/guardian.py eval`. A suíte inclui instalador, preservação de configurações, ciclo de vida, proteção de caminhos, roteamento, relatório e empacotamento.

Os 29 papéis foram executados individualmente em casos controlados na preparação original Windows. A release 2.1.0 acrescenta smoke nativo em instalação de projeto nova (A00, IAM, G01, G02). Consulte [VALIDATION](VALIDATION.md) e [evidência sanitizada](evidence/windows-native.json).

`python tools/test_native_agents.py` não consome quota. Com `--run --out DIRETORIO_NOVO`, a suíte executa o smoke; `--run --all --out DIRETORIO_NOVO` exige todos os 29 agentes em sessões distintas. Esses comandos usam uma conta Codex já autenticada e consomem quota. Não fazem parte do CI sem credenciais.

Exit 0 de um script que apenas imprime uma fixture não valida comportamento de aplicação. Defeitos intencionais devem falhar nos casos AUDIT; correções BUILD precisam passar após as mudanças.

Cloud, produção, recuperação real, navegador e todas as 132 capacidades de projetos reais continuam dependentes de verificação apropriada. A matriz do GitHub testa código e instalação com Python em cada OS, não a execução do modelo em todos os clientes.
