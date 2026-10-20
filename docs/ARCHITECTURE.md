# Arquitetura do Guardian: base e extensão profissional

A extensão dev.4 mantém os limites desta base e acrescenta contratos profissionais por papel, obrigações do pedido, responsabilidades por fase e verificação de handoffs. Consulte [Professional Assurance](PROFESSIONAL_ASSURANCE.md) e [Hooks](HOOKS.md). O principal continua responsável pela interpretação semântica; classificações determinísticas, perfis e hooks não constituem uma prova de compreensão universal nem substituem permissões efetivas.

## Finalidade

Um arranjo de **29 papéis** (A00 + 26 especialistas + G01 + G02) que cobre uma taxonomia autoral de 12 macrodomínios e 132 capacidades. A política do repositório torna o **agente principal do Codex** responsável pela orquestração A00. O TOML A00 fica disponível também para planejamento delimitado; não há garantia de que Codex escolha ou execute um subagente específico somente porque o arquivo existe.

## Pipeline de decisão

1. Entender objetivo, critérios de aceitação, contexto, dependências e proibições.
2. Distinguir modo `BUILD`, `AUDIT` e `REMEDIATE`, criticidade e possíveis ações destrutivas.
3. Para pedidos não triviais, chamar `guardian-routing` e realizar inventário estático. Tratar resposta como candidato, não como decisão definitiva.
4. Quando arquitetura for relevante, avaliar As-Is, To-Be, criticidade e lacunas. Sem evidência suficiente, manter resultado `undetermined`.
5. Selecionar agentes de acordo com fluxo/capacidades, minimizar delegações e confirmar permissões e tools.
6. Dividir atividades independentes; tarefas de escrita compartilhada devem ser sequenciadas ou isoladas em worktrees.
7. Verificar implementação com testes reais da stack. Escalonar G01 para alto risco e auditorias. Convocar G02 para releases.
8. Consolidar relatório: evidências, testes executados, alterações, risco residual, limitações, aprovação externa requerida.

## Política de risco

- `low`: escopo reduzido, mudanças reversíveis e nenhum risco especial conhecido.
- `medium`: requisitos arquiteturais, dados ou preparação de release sem indícios de efeito destrutivo.
- `high`: dados financeiros, autorização, segurança, transações concorrentes ou ação destrutiva potencial.
- `critical`: ação destrutiva associada a produção ou transação financeira; reavaliar por contexto.

**Atenção:** esse classificador textual é conservador, superficial e sujeito a falsos negativos e falsos positivos. A classificação real pode ser elevada por fatos encontrados no repositório, riscos operacionais e políticas da organização. O roteador não faz *enforcement* de deploy nem concede permissões.

## Orquestração por ondas

O roteador sugere grupos de até quatro agentes em baixo risco, seis em alto e oito em auditorias. Esses números **não são limites reais de execução paralela**; a configuração do Codex é quem limita subagentes simultâneos (`max_concurrent_threads_per_session=4` na configuração de exemplo). O A00 deve delegar tarefas independentes; etapas de revisão ocorrem **depois** da implementação. O roteador pode incluir G01/G02 na lista inicial, mas **não** significa executá-los ao mesmo tempo que o implementador.

## Fluxos de arquitetura

As-Is: sinais estáticos e evidências de código/infra, nunca tratados como demonstração da arquitetura implantada.

To-Be: oito dimensões com escala 0-3 e pesos definidos em `architecture-dimensions.json`; avaliação somente quando todas possuem evidência declarada. To-Be preliminar deve ser confirmado via ADR e critérios concretos. O agregado não pode eliminar controles compulsórios nem forçar microsserviços por uma pontuação alta.

Gap: análise qualitativa feita pelo S03 com dependências, trade-offs, riscos, custos e plano de migração. O script não finge gerar GAP completo autonomamente sem documentação e teste do projeto.

## Governança

- Todo tópico tem responsável principal e revisor no catálogo; revisores podem variar com domínio.
- `AUDIT` é funcionalmente independente e não altera código. Autonomia de modelos não implica sandbox somente leitura; a execução deve realmente estar configurada para esse acesso.
- Evidências de testes não executados são marcadas como `não verificado`, jamais inferidas.
- G01 e G02 são recomendações técnicas, não substituem aprovação do proprietário do produto, do responsável por produção ou do compliance.
- Descrições de agentes e skills são sucintas para reduzir instruções concorrentes e uso de contexto.
- Avaliações e padrões de arquitetura devem ser incrementais e versionados, não reescritas indiscriminadas.

## Limitações da tecnologia

O utilitário Python realiza **roteamento simbólico**. A delegação efetiva depende do agente principal do Codex, das ferramentas de multiagentes, do modelo, da versão do cliente e das permissões. Nenhum módulo cria sessões do Codex por API nem pressupõe acesso a ferramentas MCP que não estejam conectadas. Sem integração com o Codex real, não é possível demonstrar taxas de sucesso operacional.
