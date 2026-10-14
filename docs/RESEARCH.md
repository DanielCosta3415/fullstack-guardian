# Fontes e decisões de engenharia — consultadas em 14/10/2026

## Documentação oficial OpenAI

1. Subagents, formato de TOML, agentes pessoais/projeto e herança de permissões: https://developers.openai.com/codex/multi-agent
2. `AGENTS.md` global/projeto, descoberta e precedência: https://developers.openai.com/codex/guides/agents-md
3. Skills e locais de descoberta (`.agents/skills`, `~/.agents/skills`): https://developers.openai.com/codex/skills
4. Referência de config (`agents.enabled`, `agents.max_concurrent_threads_per_session`): https://developers.openai.com/codex/config-reference
5. Melhores práticas de prompts e skills para GPT-6 Astra, 11/09/2026: https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra
6. Harness engineering, invariantes verificáveis, documentação enxuta, feedback loops: https://openai.com/index/harness-engineering/
7. Open source Symphony, coordenação e revisão humana: https://openai.com/index/open-source-codex-orchestration-symphony/
8. Sandboxing, boundary de permissões e aprovações: https://developers.openai.com/pt-BR/docs/sandboxing
9. Multiagent Agents API: https://developers.openai.com/api/docs/guides/agents-api/multi-agent — **não confundir config de Agents API com config da CLI Codex**.

## Referências profissionais externas

10. Martin Fowler / Thoughtworks, fitness functions para governança verificável: https://martinfowler.com/articles/fitness-functions-data-products.html
11. Google SRE Workbook, Simplicity: https://research.google/pubs/the-site-reliability-engineering-workbook-chapter-simplicity/
12. OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/
13. W3C WCAG 2.2: https://www.w3.org/TR/WCAG22/
14. OpenTelemetry: https://opentelemetry.io/docs/

## Decisões aplicadas

- **A00 como função do agente principal**: uma definição TOML não instala um roteador mágico sempre ativo. O `AGENTS.md` precisa tornar essa responsabilidade permanente.
- **Validação em vez de promessa**: critérios estruturais e testes sintéticos são verificáveis; comportamento de agentes precisa de avaliação real separada.
- **Skills específicas**: descrições curtas e ativação contextual conforme recomendações Astra.
- **Limites externos**: sandbox/approval são distintos de instruções normativas; nenhum TOML deve ser tratado como uma fronteira de segurança.
- **Risco separado de arquitetura**: um sistema pequeno pode ser altamente crítico; evitar empilhar infraestrutura desnecessária.
- **Sem invocação redundante**: apenas agentes com domínio relevante e evidência de necessidade; high-risk aciona auditoria independente.
- **Arquitetura como função das necessidades**, não da quantidade de tecnologias, extensões ou arquivos.

Estas fontes fundamentam as decisões; o artefato é um projeto autoral e não uma implementação oficial OpenAI.
