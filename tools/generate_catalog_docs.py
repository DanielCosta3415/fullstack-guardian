"""Generate human catalog from reviewed canonical metadata; --check never writes."""
import argparse,json
from pathlib import Path
try:
    from .guardian_catalog import validate_catalog
    from .guardian_professional import load_contracts
except ImportError:
    from guardian_catalog import validate_catalog
    from guardian_professional import load_contracts
ROOT=Path(__file__).resolve().parents[1]

def role_display_names(records, root=ROOT):
    """Presentation labels never replace stable role identities or contracts."""
    doc=json.loads((Path(root)/'core/role-display-names-v1.json').read_text(encoding='utf8'))
    if set(doc)!={'schema_version','locale','roles'} or doc['schema_version']!=1 or doc['locale']!='pt-BR':
        raise ValueError('Invalid role display names document')
    names=doc['roles']
    if not isinstance(names,dict) or set(names)!={r['name'] for r in records}:
        raise ValueError('Role display names must cover exactly the canonical identities')
    for name,title in names.items():
        if not isinstance(title,str) or not title.strip() or title!=title.strip() or any(c in title for c in '\r\n|'):
            raise ValueError('Invalid professional role title')
    metadata={a['name']:a['title'] for a in json.loads((Path(root)/'core/agents.json').read_text(encoding='utf8'))['agents']}
    for record in records:
        title=names[record['name']]
        profile=record['profile']
        if not profile['description'].startswith(title+' — ') or not profile['developer_instructions'].startswith('Perfil profissional: '+title+'.\n'):
            raise ValueError('Professional role presentation drift')
        if record['kind']=='core' and metadata.get(record['name'])!=title:
            raise ValueError('Core professional title drift')
    return names

def render(root=ROOT):
    root=Path(root);validate_catalog(root)
    doc=json.loads((root/'core/contracts-catalog-v1.json').read_text(encoding='utf8'))
    titles=role_display_names(doc['records'],root)
    contracts={c['id']:c for c in load_contracts(root)['contracts']}
    skills=sorted(p.parent.name for p in (root/'global/skills').glob('*/SKILL.md'))
    version=(root/'VERSION').read_text().strip()
    lines=['# Generated catalog', '', 'Version: '+version, '', 'Availability is not installation, native loading, or correctness. Model policy inherits by default.', '', 'Reviewed sources: `core/contracts-catalog-v1.json` owns identity/base instructions and metadata; `core/professional-contracts-v1.json` owns the professional methods, typed capabilities, routing terms, required/conditional/optional tool needs, handoffs and unmeasured qualification. The appended professional instruction must exactly match the renderer; neither generated TOMLs nor derived playbooks can rebaseline the canonical sources. `python -B tools/guardian_catalog.py --write` generates 39 TOMLs, core metadata, ten pack manifests and the compatibility playbook. It never writes user configuration or model/sandbox permissions.', '', '| ID | Role | Kind | Reviewer | Profile SHA-256 |','|---|---|---|---|---|']
    for record in doc['records']:
        lines.append('| '+ ' | '.join(str(record[k]) for k in ('id','name','kind','reviewer','sha256'))+' |')
    lines += ['', '## Nomes profissionais oficiais (39)', '', 'Os nomes abaixo são rótulos de apresentação em português. Identificadores `guardian_*`, responsabilidades, roteamento, modelos e permissões permanecem estáveis. Fonte dos nomes: `core/role-display-names-v1.json`; o gerador verifica sua correspondência com os títulos principais e os 39 perfis canônicos.', '', '| Identificador técnico | Nome profissional |', '|---|---|']
    for record in doc['records']:
        lines.append('| '+record['name']+' | '+titles[record['name']]+' |')
    lines += ['', '## Professional contracts (39)', '', 'Contracts are declarations, not certificates. All professional qualification remains `NOT_EVALUATED` until separate measured evidence exists. Core `competencies` now holds taxonomy IDs; routing words remain separately in `routing_terms` and legacy `core/agents.json` keywords.', '', '| ID | Modes | Typed capabilities | Required tool needs | Contract |', '|---|---|---|---|---|']
    for record in doc['records']:
        c=contracts[record['id']]
        lines.append('| '+c['id']+' | '+', '.join(c['modes'])+' | '+str(len(c['capabilities']))+' | '+', '.join(t['capability'] for t in c['tool_policy']['required'])+' | '+c['contract_version']+' |')
    lines += ['', 'Required tool needs are abstract capabilities, not native tool names, permission grants or observations. Dynamic runners are conditional on the task. Missing essential capability blocks only the dependent check; static review must label its limits.', '', '`python -B tools/guardian_professional.py S07` loads the full i18n/performance contract. Python callers use `load_contracts(root)`, `get_contract(agent_id, root)`, and `checkpoints_for(agent_id, root)` for all 29 core and ten optional roles. Unknown roles fail closed; optional roles still require installation and actual eligibility.', '', 'G01/G02 allow only audit/explore. Reviewer ownership is a review responsibility, not an executable dependency edge; it does not create a reciprocal execution cycle. S07 owns a conditional i18n overlay for Unicode/RTL, pluralization, fallback, pseudo-localization, dates/time zones and currency with S06 handoff.', '', 'Schema: `core/professional-contracts-v1.schema.json`; stdlib runtime additionally checks exact identity coverage, taxonomy ownership, independence, and generated method/playbook drift.', '', '## Untrusted specialist result proposals', '', '`core/professional-result-v1.schema.json` documents the closed result shape. `validate_result(result, agent_id, task_id=..., obligation_ids=[...], root=...)` binds the producer identity, version, task and every obligation; rejects traversal, malformed hashes, unknown evidence references, inconsistent check outcomes and self-approved statuses. `produced` remains an untrusted claim. The supervisor must separately bind paths to the allowed scope, read actual bytes, corroborate executed tool calls and obtain independent consumer/reviewer acceptance.', '', 'A result contains the twelve fields: task_id, agent_id, contract_version, obligations, artifacts, facts, assumptions, decisions, checks, not_verified, residual_risks and handoff. Facts reference declared `artifact:<relative-path>` or `check:<id>` evidence. A producer can only declare an obligation produced/blocked/not_verified and a handoff pending_consumer_acceptance/blocked, never verified/integrated/accepted.', '', '```python', 'from tools.guardian_professional import result_template, validate_result', 'proposal = result_template("S08", task_id="task-1", obligation_ids=["O1"])', '# Initial template honestly reports O1 not_verified and handoff blocked.', '# Replace claims with scoped artifact hashes, checks and traceable evidence.', 'validate_result(proposal, "S08", task_id="task-1", obligation_ids=["O1"])', '```', '', '## Operational skills ('+str(len(skills))+')','']+['- `'+name+'`' for name in skills]
    return '\n'.join(lines)+'\n'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();target=ROOT/'docs/CATALOG.md';data=render()
    if a.check:
        if not target.exists() or target.read_text(encoding='utf8')!=data:raise SystemExit('Generated catalog documentation drift')
    else:target.write_text(data,encoding='utf8',newline='\n')
