# 2.2.0-dev.4 — professional assurance candidate

Implements the N01–N18 audit response: 39 role-specific professional contracts and generated profiles/checkpoints, typed capability/tool policies, intent/obligation and lifecycle coverage, contract-bound results and supervised integration by default, a 142-case development qualification corpus, strict seeded-failure oracles, a two-trial native professional harness, opt-in trust-preserving advisory hooks, and a hash-locked upstream adaptation linter/guide. Open SME scenarios, private holdout and production readiness are not inferred from implementation or synthetic tests. Stable/global installation remains a separate reviewed action.

# 2.2.0-dev.3 — completion candidate

Adds canonical generation of profiles/metadata, supervised acceptance transitions, bounded read retries, journal retention/privacy diagnostics, pack rollback, executable domain adapters, real Windows client probing, installed-runtime functional suites, call-correlated native acceptance, and explicit hosted-rootless grading. Current evidence and unresolved external gates are in docs/COMPLETION-STATUS.md. This is a development candidate; no stable promotion is inferred.

# 2.2.0-dev.2 — hardening candidate

Implements typed contracts, phase/risk gates, explicit eligibility and current inventory checks, capability/policy integration, safe process supervision, private Git checkouts, read-only parallel audits, guarded integration, namespace recovery, shared-root locking, bounded journals, isolated declarative grading, paired evaluations, domain observation contracts, distribution regressions and explicit release gates.

This candidate has not been promoted to stable. Consult docs/IMPLEMENTATION-STATUS.md for actual evidence and limitations. Native acceptance and Docker-backed isolation are not inferred from file presence or a unit test. Existing global installations are not changed by this source update.

# Notas da release

## v2.2.0-dev.1 — Prévia de desenvolvimento (não publicada)

- **Não é a versão estável 2.1.0 nem uma release de produção.**
- Acrescenta skills por etapa do ciclo de vida, playbooks especializados, dez packs opcionais, orquestração CLI supervisionada, avaliação local opt-in e recuperação do instalador.
- Os testes da CI verificam o código em ambientes isolados; a execução nativa no Windows autenticado ainda requer validação separada.
- O PR em rascunho preserva `main`. O uso da prévia requer escolha explícita e revisão de segurança.

# Notas da release

## v2.1.0 — 2026-10-14

Primeira distribuição pública preparada para instalação global preservadora, com marketplace e configuração guiada.

- Mantém 29 especialistas, oito skills e 132 capacidades.
- Empacota uma única skill de onboarding; as skills operacionais são instaladas globalmente.
- Integra registro dos agentes e política de coordenação sem impor modelo, provedor ou credenciais.
- Adiciona manutenção com recibo, backups, atualização, desinstalação e rollback; simulação é o padrão.
- Adiciona lançadores Windows e POSIX que usam Python existente, sem downloads automáticos.
- Adiciona CI multiplataforma e empacotamento com SHA-256.
- Incorpora correções anteriores de instalação e auditoria.

### Evidências e limites

A linha v2.0 foi validada em Windows: 29 execuções individuais de agentes, 23 testes unitários e 20 cenários de roteamento. A v2.1.0 validou o instalador e plugin em destinos isolados, smoke nativo de quatro perfis e uma suíte ampliada de instalação, integridade e roteamento. Veja [VALIDATION](docs/VALIDATION.md) e os checks vinculados à tag; não confunda validação estática com execução de modelo.

Clientes antigos, sessões efêmeras, ambientes cloud sem executor local e políticas organizacionais podem limitar a delegação ou a instalação. Uma nova sessão é necessária para recarregar políticas.
