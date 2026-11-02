# Especialização e avaliação discriminante — contratos 1.1.0

Os 39 contratos profissionais foram aprofundados a partir dos 67 itens da auditoria
da revisão `f20bb5a`. Cada item conserva seu identificador em `procedure` e
`definition_of_done`; os gatilhos de ferramenta e as condições de consumo agora
identificam o comportamento e o cenário da especialidade. São instruções e
critérios de trabalho, não credenciais profissionais nem concessões de ferramentas.

`docs/audit-role-remediation.json` relaciona todos os itens com mudanças, checks
específicos, teste local, protocolo nativo, resultado de aceitação e o restante
não verificado. **Não interpretar 67 registros como 67 aceitações completas.**
As quatro correções locais de oráculo, listas de capacidades e política de gate
possuem regressões próprias; os outros itens têm aprofundamento contratual,
subescopo local e protocolo para sua stack real. A revisão independente e a
execução real continuam necessárias para as alegações que dependem delas.

## Três camadas distintas

1. Os 103 casos públicos existentes continuam sendo projeções data-only de
   desenvolvimento. O protocolo passa de 2 para **3**: uma tarefa pronta requer
   evidência não vazia, conhecida e não contraditória. Os resultados dos fixtures
   antigos foram preservados; resultados históricos não são reclassificados.
2. `eval/professional-depth/catalog.json` define **39 exercícios de desenvolvimento**,
   um por papel, com tarefa, stack real necessária, implementação defeituosa
   plausível, expectativa independente, critérios, consumidor e limites. O harness
   executa somente implementações confiáveis allowlisted. Há transações SQLite
   reais com rollback/reabertura/lock, watermark com tie-breaker, assinatura HMAC
   sobre bytes, rotação limitada, transporte/resolver inteiramente em memória,
   cache, consumidores wire e máquinas de estado. Os modelos de foco/SSR/DI não
   são execução de browser, AT, framework frontend ou .NET. A assinatura HMAC de
   fixture não certifica JWT/OIDC nem uma cadeia de assinatura de fornecedor.
3. O **protocolo nativo por papel** permite preparar e conferir recibos da stack
   observada: versão, revisão exata, controle positivo/negativo, argv/exit/motivo,
   artefato/digest e cobertura de cada critério, ou justificativa explícita de não
   verificado. O produtor e o consumidor precisam coincidir com a atribuição do
   caso e ser distintos. O checker é data-only: sua saída permanece
   `produced_pending_independent_corroboration`; não autentica execução, identidade
   de sessão, semântica da conclusão ou aceite do consumidor.

Nenhum código, shell, comando, URL ou modelo fornecido por candidato é executado
por este harness. Não há chamadas externas, pagamento, apply de infraestrutura,
modificação de configuração global ou autorização adicional.

## Comandos reproduzíveis

Na raiz do repositório:

```powershell
python -B tools/guardian_professional_depth.py validate
python -B tools/guardian_professional_depth.py run
python -B tools/guardian_professional_depth.py run --role S13
python -B tools/guardian_professional_depth.py plan --role S04
python -B tools/guardian_professional_depth.py template --role S04
python -B tools/guardian_professional_depth.py check --case S04:depth:1 --result caminho/recibo.json
python -B -m unittest tests.test_professional_audit_improvements
python -B tools/guardian_catalog.py
python -B tools/generate_catalog_docs.py --check
```

`template` gera um ponto de partida intencionalmente não aprovado, com revisão e
stack ainda não observadas. Não preencher recibos a partir do plano: executar os
checks autorizados da aplicação, preservar logs reais e obter corroboração
independente. Cada entrada `coverage` usa `<case_id>:criterion:<n>` e referencia
IDs dos checks declarados ou uma razão de não verificado; nenhuma obrigação
pode desaparecer por não haver ferramenta. Checks negativos passam quando a
asserção esperada de rejeição é satisfeita (`exit_code=0` do teste), e não por
qualquer falha de importação/processo.

Todos os exercícios locais têm controle correto e implementação defeituosa
plausível; o teste confirma que o mutante produz observação diferente da
expectativa predefinida. A execução invertida dos casos independentes testa
dependência de ordem/estado compartilhado. A renomeação de IDs do grafo é outro
metamorfismo. Isso não afirma robustez geral a toda transformação ou escalonamento.

## Calibração, repetições e incerteza

`calibrate` aceita observações **públicas de desenvolvimento** já produzidas,
vinculadas por digest a uma política anterior à execução. A política fixa modelo,
effort, ambiente, dataset, unidade de custo, mínimos e erro máximo por família.
O módulo não muda modelo/effort nem executa uma avaliação de LLM por conta própria.

```powershell
python -B tools/guardian_professional_depth.py calibrate --result caminho/tentativas.json --policy caminho/politica.json
```

Cada tentativa contém `case_id`, `attempt`, `outcome` (`passed`, `failed`,
`not_run`, `inconclusive`), `latency_ms`, `cost` (`kind`, `amount`),
`policy_sha256` e `binding` igual ao da política. O digest do dataset deve ser
`guardian_qualification.digest(catalog)` da revisão atual. A política tem
`schema_version=1`, `partition=PUBLIC_DEVELOPMENT`, `binding` com `model`,
`effort`, `environment_sha256`, `dataset_sha256`, `cost_unit`, e `families`
indexadas pelo harness, cada uma com `min_observations` e `max_error_rate`.

O resumo preserva numerador/denominador, erros, não executados/inconclusivos,
intervalo de Wilson de 95% e quantidade de amostras de latência. Custo estimado,
medido e desconhecido permanecem separados, na unidade fornecida. Contexto ou
política divergente, caso desconhecido, tentativa duplicada, custo/latência
não finitos e partição de holdout privada são recusados. Ausência de observações
é incerteza, nunca acurácia perfeita. Sucesso de subescopo não autoriza promoção;
autenticidade/independência de tentativas e qualificação de agente continuam
não verificadas por um documento JSON.

## Fonte única e compatibilidade

`capability_summary()` deriva listas completas e tipadas do contrato. S04 expõe
suas 33 capacidades de revisão e G01 as 132; listas legadas concorrentes e remoção
de IDs (incluindo 4.13 e 10.6) falham no pré-voo. O catálogo continua proprietário
da identidade e das instruções-base, e os contratos dos métodos/capacidades.
As 39 TOMLs e os playbooks são derivados, sem editar permissões ou modelos.

O formato de contrato continua schema v1; o conteúdo profissional atual passa
a `contract_version=1.1.0` e os resultados precisam declarar essa versão.
Versão/hash antigos não são silenciosamente promovidos à revisão nova. Identidades
técnicas, títulos profissionais, ownership da taxonomia e papéis de revisão foram
preservados. A versão de release é tratada separadamente nas notas `Unreleased`.
