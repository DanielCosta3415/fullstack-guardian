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
