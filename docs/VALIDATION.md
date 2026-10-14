# Validação e alcance das evidências

## Evidência histórica da linha v2.0

Em Windows com Codex desktop 26.1007.71326 e CLI 0.162 alpha, os 29 papéis foram executados individualmente em casos controlados. Os 23 testes unitários da preparação local e 20 cenários de roteamento passaram. Houve verificação independente de três implementações.

Essas evidências não demonstram todas as 132 capacidades, compatibilidade universal, segurança absoluta nem prontidão de produção. Logs privados e identificadores de sessão não são distribuídos.

## Release v2.1.0

Os checks públicos associados à tag e ao commit são a referência para a distribuição. A matriz CI cobre Windows/Linux/macOS e Python 3.11/3.12/3.13: somente jobs concluídos com sucesso contam como aprovados. Execução nativa em outros sistemas deve ser classificada como NÃO VERIFICADA até existir teste real.

```sh
python -m unittest discover -s tests -v
python tools/guardian.py validate
python tools/guardian.py eval
python install.py --user --doctor
```

Os testes automatizados devem cobrir instalação isolada, idempotência, configurações existentes, conflitos, atualização, desinstalação e rollback. O doctor confere integridade e registro; não chama o modelo.

## Verificação nativa pelo usuário

Após a instalação, abra um novo chat. Peça uma tarefa pequena e controlada com um especialista e revisão independente. Confira o papel escolhido, execução efetiva, arquivos ou saída produzida, testes e limites. Não aceite apenas uma lista de nomes como evidência.

O smoke nativo v2.1.0 executou A00, IAM, G01 e G02 em instalação de projeto nova. A instalação do marketplace/plugin também foi testada em CODEX_HOME isolado. Consulte [evidência sanitizada](evidence/windows-native.json).

Para validar todos os papéis, use `python tools/test_native_agents.py --run --all --out DIRETORIO_NOVO`, após consultar sua ajuda e confirmar o consumo de quota. Exija 29 resultados individuais e marque falhas ou indisponibilidades. Sem credenciais e ferramentas correspondentes, browser, cloud, infraestrutura e produção continuam NÃO VERIFICADOS.

Sessões efêmeras tiveram limitação de delegação no cliente validado; prefira sessões normais para testes nativos. A escolha de especialistas é adaptativa e revisável pelo agente principal.
