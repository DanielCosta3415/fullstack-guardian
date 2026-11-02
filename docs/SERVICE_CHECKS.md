# Checks locais reais de serviços e persistência

`tools/guardian_service_checks.py` executa oito fixtures confiáveis e fixas,
cada uma com implementação correta e um defeito específico. Não executa código
de candidato, resposta de agente, comando arbitrário, URL fornecida externamente
ou dependência de produção. O padrão somente descreve o plano.

```powershell
python -B -X utf8 tools/guardian_service_checks.py
python -B -X utf8 tools/guardian_service_checks.py --run --out C:/workspace/guardian-service-evidence-new
python -B -m unittest tests.test_service_checks -v
```

O diretório de saída precisa ser novo e fora do checkout. Arquivos existentes
e ancestrais symlink/reparse são recusados. As únicas conexões são HTTP direto
para endereço numérico `127.0.0.1` em portas efêmeras de servidores criados pelo
próprio ensaio; não se usam proxy nem DNS externo. Threads e sockets são fechados
e as pastas temporárias são removidas antes de produzir o relatório. Se houver
erro arbitrário, inclusive import/timeout, o caso permanece ERROR/FAILED.

| Caso | Item da auditoria | Observação real e defeito semeado |
|---|---|---|
| transaction | S08-P1 | SQLite em disco, débito/outbox, entrada inválida, rollback antes de commit, timeout após commit e reabertura; mutante confirma operação cancelada |
| fencing | S10-P1 | Worker atrasado liberado após mudança de epoch, CAS no armazenamento, efeito/idempotência após reabertura; mutante omite a condição de fencing |
| migration | S11-P1 | Dois conectores, SQLITE_BUSY observado, transação DDL parcialmente executada e rollback, retry/forward-fix e reconciliação por chave/valor; mutante confirma DDL incompleto |
| wire | S09-P1 | HTTP POST e HMAC sobre bytes reais, retry idêntico e replay com conteúdo diferente; mutante normaliza JSON antes de verificar assinatura |
| consumer | S09-P1 | HTTP JSON com mudança de tipo e enum novo; consumidor antigo/estrito rejeita e tolerante preserva desconhecido; mutante aceita bool como inteiro |
| resource_auth | RB-S13-2 | HTTP por recurso para dono e outro tenant, exposição observada antes/depois da proteção; mutante omite autorização por recurso |
| destinations | RB-S13-1 | Stub permitido e proibido, redirect e resolução controlada que muda endereço; mutante revalida somente primeiro hop e resolve novamente antes de conectar |
| token_rotation | RB-S14-1 | Compact JWT HS256 com HMAC efetivo, kid atual/desconhecido/novo, refresh local permitido, algoritmo e assinatura inválida; mutante ignora allowlist de algoritmo |

O recibo contém versões reais Python/SQLite/OS, argv do CLI quando executado por
ele, hashes do harness/fixture, dos seis bancos preservados e dos dois recibos de
tempo de bloqueio/SQLITE_BUSY, observações por
variante, discriminador exato e duração. O efeito negativo esperado só é aceito
se a implementação defeituosa produzir sua divergência específica. Falhar de
qualquer maneira não conta como rejeitar corretamente o defeito.

Em um sandbox que bloqueie conexão local, os três testes dependentes de socket
registram skip explícito **HTTP NOT VERIFIED**, enquanto os testes de SQLite e
criptografia continuam. O runner `--run` conserva esse bloqueio como ERROR e
retorna código1; ele não converte a ausência de rede em sucesso. O ensaio completo
precisa de permissão efetiva para os sockets loopback, sem conceder autorização
para destinos externos.

## Limites obrigatórios

Esses checks avaliam implementações confiáveis de fixtures, **não o desempenho
dos 39 agentes**. Acrescentam subescopos reais e reproduzíveis; não concluem todos
os critérios dos itens citados. SQLite não comprova semântica de PostgreSQL,
SQLServer, filas ou armazenamento distribuído. Três linhas são dataset mínimo
de reconciliação, não evidência de capacidade ou escalonamento geral. O worker
usa barreira determinística, não exploração exaustiva de interleavings ou
garantia sob crash de processo/host.

A política SSRF usa portas loopback como destinos permitido/proibido e um
resolver injetado determinístico. Os sockets HTTP são reais; isso **não prova**
resistência geral à troca de DNS do SO, NAT, IPv6, proxies, redes externas ou
isolamento de rede. O header de tenant é uma identidade fornecida pelo teste,
sem afirmar autenticação. JWT HS256 usa criptografia HMAC efetiva, mas não
comprova OIDC discovery, JWKS/RS256, disponibilidade de emissor externo nem
cadeia de confiança de fornecedor. Não há certificação profissional, SME,
holdout privado, benchmark de superioridade ou autorização de release.
