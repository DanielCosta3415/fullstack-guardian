#!/usr/bin/env python3
"""Guardian System: safe static discovery, heuristic routing, audit schemas and validation. Standard library only."""
import argparse, json, os, re, sys, tomllib, unicodedata, stat
from collections import Counter
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent.parent
IGNORE={'.git','node_modules','bin','obj','dist','build','.next','.venv','venv','__pycache__','.terraform','coverage','target','.gradle','.idea','.vs','.guardian'}

def load(s):return json.loads((ROOT/'core'/s).read_text(encoding='utf-8'))
def norm(s):return ''.join(c for c in unicodedata.normalize('NFKD',s.lower()) if not unicodedata.combining(c))

def is_link_or_reparse(path):
    info=Path(path).lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400))

def inspect_project(path):
    root=Path(path).expanduser().resolve()
    if not root.is_dir():raise ValueError('Diretório de projeto inválido')
    names=[]; truncated=False
    for base,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=[d for d in sorted(dirs) if d not in IGNORE and not is_link_or_reparse(Path(base)/d)]
        for file in sorted(files):
            if len(names)>=8000:truncated=True;break
            p=Path(base)/file
            if is_link_or_reparse(p) or re.search(r'(^\.env|secret|credential|private.?key|\.pem$|\.pfx$|\.key$)',file,re.I):continue
            names.append(norm(p.relative_to(root).as_posix()))
        if truncated:break
    files={n.rsplit('/',1)[-1] for n in names}
    def has(*tokens):return any(any(token in n for token in tokens) for n in names)
    def exact(*tokens):return any(t in files for t in tokens)
    candidates=[
     (has('.csproj','.sln') or exact('global.json'),'.NET / C#','backend'),
     (exact('package.json','pnpm-lock.yaml','yarn.lock'),'Node.js ecosystem','frontend'),
     (has('.tsx','.jsx') or exact('vite.config.ts','next.config.js'),'JSX/React compatible','frontend'),
     (has('.razor','.cshtml'),'Razor / ASP.NET UI','frontend'),
     (exact('angular.json'),'Angular','frontend'),(has('.vue'),'Vue','frontend'),
     (exact('pyproject.toml','requirements.txt'),'Python','backend'),
     (exact('pom.xml','build.gradle'),'JVM','backend'),(exact('go.mod'),'Go','backend'),
     (exact('docker-compose.yml','compose.yaml','compose.yml'),'Container compose','container'),
     (exact('dockerfile') or has('/dockerfile'),'Docker','container'),
     (has('.tf','terraform/'),'Terraform','cloud'),
     (has('.github/workflows/','.gitlab-ci.yml','jenkinsfile'),'CI/CD','ci'),
     (has('openapi','swagger'),'API contracts','api'),
     (has('migration','migrations','postgres','mongo','sqlite','dbcontext'),'Data markers','data'),
     (has('k8s/','kubernetes/','helm/','chart.yaml','rabbitmq','kafka','servicebus'),'Distributed markers','distributed'),
     (has('.spec.ts','.test.ts','/tests/','test_'),'Test artifacts','tests')]
    tech=[lab for yes,lab,tag in candidates if yes]
    tags={tag for yes,lab,tag in candidates if yes}
    score=int('api' in tags)+int('data' in tags)+2*int('distributed' in tags)+int('cloud' in tags)+int({'backend','frontend'}<=tags)+int(len({'ci','cloud','container','distributed'}&tags)>=3)
    level='simple' if score<=1 else 'intermediate' if score<=4 else 'robust'
    return {'project':str(root),'files_scanned':len(names),'truncated':truncated,'technologies':tech,'tags':sorted(tags),
        'architecture_as_is_heuristic':{'level':level,'score':score,'confidence':'low','warning':'Inferência por nomes de arquivos, não é uma auditoria real.'},
        'criticality':'unknown','architecture_to_be':'requires requirements and runtime evidence',
        'unknowns':['demanda/carga','impacto de falhas','RTO/RPO/SLO','regulação','ambiente real','ameaças','orçamento e equipe']}

TRIGGERS={
'finance':'pagamento|transferencia|pix|saldo|faturamento|cobranca|cartao|financial|payment|bank|dinheiro|account balance|money transfer|invoice|billing|charge|transaction',
'security':'seguranca|security|vulnerab|autentic|autoriz|oauth|oidc|jwt|token|segredo|secrets|privacidade|lgpd|xss|csrf|authentication|authorization|privacy|ssrf',
'data':'dados|database|banco de dados|sql|mongo|migration|migracao|transacao|integridade|persistencia|transaction|integrity|persistence',
'concurrency':'concorrencia|simultane|race condition|idempoten|fila|event|queue|retry|duplicad|concurren|duplicate|retries',
'release':'deploy|implant|producao|release|go live|rollout',
'destructive':'apagar|excluir|deletar|drop table|wipe|destruir|rotacionar senha|delete|truncate',
'frontend':'frontend|front-end|interface|pagina|tela|formulario|react|vue|angular|css|html|layout|ux|acessibil|wcag',
'backend':'backend|back-end|api|endpoint|controller|servico|service|microservico|.net|asp.net|c#',
'architecture':'arquitetura|architect|microservic|monolito|solucao|escalabilidade|distribuid',
'audit':'auditar|auditoria|audit|review|revisar|validar completamente|production readiness',
'ai':'llm|rag|modelo de ia|ia generativa|ai feature|chatbot|prompt injection'}

SKILLS={'audit':'fullstack-audit','release':'production-readiness','security':'security-review','frontend':'frontend-assurance','backend':'backend-assurance','architecture':'architecture-assessment'}

def route(prompt,inventory=None,mode='auto'):
    if not prompt.strip():raise ValueError('Prompt vazio')
    text=norm(prompt);hit={k:any(token in text for token in v.split('|')) for k,v in TRIGGERS.items()}
    # Remove narrowly scoped explicit exclusions from release candidate selection.
    # Destructive/security/financial risk is deliberately never suppressed by this.
    release_text=re.sub(r'\b(?:no|without|sem)\s+(?:release|deploy(?:ment)?|production|producao)(?:\s+(?:or|e|ou)\s+(?:release|deploy(?:ment)?|production|producao))?(?:\s+actions)?','',text)
    release_text=re.sub(r'\b(?:do not|dont|nao)\s+(?:deploy|implant\w*)\b','',release_text)
    hit['release']=any(token in release_text for token in TRIGGERS['release'].split('|'))
    mode=('AUDIT' if hit['audit'] else 'BUILD') if mode=='auto' else mode.upper()
    if mode not in ('AUDIT','BUILD','REMEDIATE'):raise ValueError('Modo inválido')
    critical=hit['destructive'] and (hit['release'] or hit['finance'])
    high=any(hit[x] for x in ('finance','security','concurrency','destructive'))
    risk='critical' if critical else 'high' if high else 'medium' if any(hit[x] for x in ('release','data','architecture')) else 'low'
    selected={}
    def add(ids,reason):
        for id in ids.split():selected.setdefault(id,[]).append(reason)
    rules=[('finance','S08 S10 S11 S14 S18','Operações financeiras'),('security','S13 S14','Segurança'),
      ('concurrency','S10 S11 S18','Concorrência e idempotência'),('data','S11 S18','Dados/transações'),
      ('frontend','S05 S17','Front-End'),('backend','S08 S18','Back-End'),('architecture','S03 S02','Arquitetura/requisitos'),
      ('release','S20 S23','Release/confiabilidade'),('ai','S26','IA incorporada ao produto')]
    for tag,ids,reason in rules:
        if hit[tag]:add(ids,reason)
    if 'escalabilidade' in text or 'latencia' in text or 'performance' in text or 'carga' in text:add('S19','Desempenho/capacidade')
    if any(w in text for w in ('observabil','logs','trace','tracing','monitoramento','alerta','incidente')):add('S21','Observabilidade e resposta a incidentes')
    if any(w in text for w in ('indisponibil','falha operacional','incidente de producao','recuperacao de desastre')):add('S20','SRE, disponibilidade e recuperação')
    if any(w in text for w in ('teste','test','qualidade','cobertura')):add('S16','Estratégia de qualidade')
    if any(w in text for w in ('teste de integracao','testes de integracao','api contract','xunit','contrato de api')):add('S18','Testes de integração/API')
    reg=load('agents.json');entries={a['id']:a for a in reg['agents']}
    matches=[]
    for a in reg['agents']:
        if a['id'] in ('A00','G01','G02'):continue
        n=sum(norm(k) in text for k in a['keywords'] if len(norm(k))>2)
        if n>=2:matches.append((n,a['id']))
    for _,id in sorted(matches,key=lambda it:(-it[0],it[1]))[:3]:add(id,'Especialidade fortemente relacionada ao pedido')
    tags=set(inventory.get('tags',[])) if inventory else set()
    if not selected:
        add('S05' if 'frontend' in tags and 'backend' not in tags else 'S08' if 'backend' in tags and 'frontend' not in tags else 'S02','Triagem inicial; escopo não inequívoco')
    if mode=='AUDIT':
        add('S16 G01','Auditoria e revisão independente')
        if 'frontend' in tags:add('S04 S06','Camada Front-End identificada')
        if 'backend' in tags:add('S08 S18','Camada Back-End identificada')
        if 'cloud' in tags or 'container' in tags:add('S22','Infraestrutura identificada')
        if 'ci' in tags:add('S23','CI detectada')
    elif risk in ('high','critical'):add('G01','Revisão independente obrigatória')
    if hit['release'] or critical:add('G02','Prontidão de produção')
    priority={'G02':98,'G01':97,'S13':90,'S14':90,'S10':88,'S11':87,'S18':85,'S03':80,'S20':79,'S23':78,'S16':77,'S08':70,'S05':70}
    ranked=sorted(selected,key=lambda a:(-priority.get(a,50),a))
    limit=8 if mode=='AUDIT' else 6 if risk in ('high','critical') else 4
    workers=[id for id in ranked if id not in ('G01','G02')]
    phases=[{'phase':'investigation_and_implementation' if mode!='AUDIT' else 'domain_audit','agents':workers[i:i+limit]} for i in range(0,len(workers),limit)]
    if 'G01' in ranked:phases.append({'phase':'independent_review','agents':['G01']})
    if 'G02' in ranked:phases.append({'phase':'production_readiness_gate','agents':['G02']})
    skills=['guardian-routing']+(['fullstack-audit'] if mode=='AUDIT' else [])+[s for k,s in SKILLS.items() if k!='audit' and hit.get(k)]
    if hit['finance'] and 'security-review' not in skills:skills.append('security-review')
    approvals=[]
    if hit['release']:approvals.append('Deploy em produção depende de autorização externa real; nenhuma permissão é elevada aqui.')
    if hit['destructive']:approvals.append('Operações irreversíveis exigem autorização, backup e plano de restauração.')
    if hit['finance']:approvals.append('Exigir testes das invariantes de negócio e decisão humana para riscos materiais.')
    return {'mode':mode,'risk':risk,'architecture_as_is_guess':inventory['architecture_as_is_heuristic'] if inventory else 'unknown',
      'architecture_to_be':'undetermined; needs requirements, constraints and evidence',
      'agents':[{'id':id,'name':entries[id]['name'],'reason':sorted(set(selected[id]))} for id in ranked],
      'execution_waves':[p['agents'] for p in phases],'phases':phases,'suggested_skills':list(dict.fromkeys(skills)),
      'approval_boundaries':approvals,'routing_confidence':'medium' if any(hit.values()) else 'low',
      'notice':'Regras heurísticas. O Codex deve validar e convocar subagentes nativamente; este script NÃO cria subagentes.'}


def assess(project, profile):
    """Assess To-Be only from documented scores; never infer requirements from filename heuristics."""
    if not isinstance(profile,dict):raise ValueError('Perfil precisa ser objeto')
    as_is=inspect_project(project)
    definition=load('architecture-dimensions.json')['fields']
    observed=profile.get('dimensions',{})
    if not isinstance(observed,dict):raise ValueError('Dimensions precisa ser objeto')
    validated=[]; missing=[];errors=[]
    for key,descriptor in definition.items():
        entry=observed.get(key,{})
        if not isinstance(entry,dict):raise ValueError('Dimensão precisa ser objeto: '+key)
        score=entry.get('score')
        evidence=entry.get('evidence')
        if score is None or not evidence:
            missing.append(key);continue
        if isinstance(score,bool) or not isinstance(score,int) or score not in (0,1,2,3):
            errors.append('Score deve ser inteiro 0..3: '+key);continue
        if not isinstance(evidence,str) or len(evidence.strip())<6:
            errors.append('Evidência insuficiente: '+key);continue
        validated.append((key,score,float(descriptor['weight']),evidence))
    if errors:raise ValueError('; '.join(errors))
    mean=round(sum(v*w for _,v,w,_ in validated)/sum(w for _,_,w,_ in validated),3) if validated else None
    to_be='undetermined' if missing else ('simple' if mean<=0.9 else 'intermediate' if mean<=1.8 else 'robust')
    critical=any(v==3 for k,v,w,e in validated if k in ('business_criticality','data_integrity','availability_recovery','security_compliance'))
    overrides=profile.get('mandatory_controls',[])
    if not isinstance(overrides,list):raise ValueError('mandatory_controls precisa ser lista')
    strong_controls=bool(critical or overrides)
    decisions=[]
    if critical:decisions.append('Alta criticidade identificada: reforçar controles de segurança/integridade/recuperação sem presumir microsserviços.')
    if overrides:decisions.append('Respeitar controles obrigatórios documentados: '+', '.join(map(str,overrides)))
    if missing:decisions.append('Não concluir To-Be antes de fundamentar as dimensões faltantes: '+', '.join(missing))
    if not missing:decisions.append('To-Be preliminar a confirmar pelo S03 mediante ADR, testes e requisitos; não implica tecnologia específica.')
    return {'as_is':as_is['architecture_as_is_heuristic'],'to_be_preliminary':to_be,'dimensions_provided':len(validated),
      'dimensions_missing':missing,'weighted_score':mean,'critical_control_override':strong_controls,
      'recommended_control_posture':'strict' if strong_controls else 'proportional',
      'business_criticality':next((v for k,v,w,e in validated if k=='business_criticality'),'unknown'),
      'decisions':decisions,'evidence_quality':'complete_declared_not_independently_verified' if not missing else 'insufficient',
      'warning':'O script confere estrutura declarada, não a veracidade da evidência. Revisão arquitetural humana/assistida continua necessária.'}

def validate():
    errors=[];r=load('agents.json')['agents'];t=load('taxonomy-v3.json');caps=t['capabilities'];ids={a['id'] for a in r}
    if len(r)!=29 or len(ids)!=29 or len({a['name'] for a in r})!=29:errors.append('Agentes diferentes de 29 ou duplicados')
    if len(caps)!=132 or len({c['id'] for c in caps})!=132:errors.append('132 capacidades não únicas')
    if len(t['domains'])!=12:errors.append('Macrodomínios diferentes de 12')
    for d,v in t['domains'].items():
        if sum(c['domain']==d for c in caps)!=v['count']:errors.append('Contagem de domínio incorreta '+d)
    for c in caps:
        if c['primary'] not in ids or not c['reviewers'] or not set(c['reviewers'])<=ids:errors.append('Sem guardião válido '+c['id'])
        if c['primary'] in c['reviewers']:errors.append('Autorrevisão de capacidade '+c['id'])
    for a in r:
        f=ROOT/a['file']
        if not f.exists():errors.append('Agente ausente '+str(f));continue
        try:
            doc=tomllib.loads(f.read_text(encoding='utf8'))
            if any(not doc.get(key) for key in ('name','description','developer_instructions')) or doc['name']!=a['name']:errors.append('Campos incorretos '+str(f))
        except Exception as exc:errors.append('TOML inválido '+str(exc))
    try:
        playbooks=load('specialist-playbooks-v1.json')
        if playbooks.get('schema_version')!=1 or set(playbooks.get('agents',{}))!=ids:
            errors.append('Playbooks não cobrem exatamente os agentes principais')
        else:
            for a in r:
                item=playbooks['agents'][a['id']]
                if item.get('name')!=a['name'] or not isinstance(item.get('checkpoints'),list) or len(item['checkpoints'])<3:
                    errors.append('Playbook incompleto '+a['id'])
        lifecycle=load('lifecycle-v1.json')
        stages=['discovery','requirements','architecture','experience','development','integration','data','verification','delivery','operations','evolution','decommission']
        phases=lifecycle.get('phases',[])
        if lifecycle.get('schema_version')!=1 or [p.get('id') for p in phases]!=stages:
            errors.append('Ciclo de vida inválido')
        else:
            for phase in phases:
                if not phase.get('criteria') or not set(phase.get('responsible',[]))<=ids:
                    errors.append('Critérios de ciclo de vida inválidos '+phase['id'])
    except (OSError,ValueError,KeyError,TypeError) as exc:
        errors.append('Metadados de plataforma inválidos '+str(exc))
    skills=list((ROOT/'global'/'skills').glob('*/SKILL.md'))
    if len(skills)<8:errors.append('Conjunto mínimo de oito skills ausente')
    if len({p.parent.name for p in skills})!=len(skills):errors.append('Skills duplicadas')
    for p in skills:
        s=p.read_text(encoding='utf8')
        if not s.startswith('---\nname: ') or '\ndescription: ' not in s:errors.append('Frontmatter de skill inválido '+str(p))
    return {'ok':not errors,'errors':errors,'agents':len(r),'capabilities':len(caps),'domains':len(t['domains']),'skills':len(skills)}

def evals():
    cases=load('eval-cases.json')['cases'];failures=[]
    for case in cases:
        result=route(case['prompt'],mode=case.get('mode','auto'))
        ids={a['id'] for a in result['agents']}
        missing=sorted(set(case.get('must_include',[]))-ids)
        unexpected=sorted(ids&set(case.get('must_exclude',[])))
        if missing or unexpected or (case.get('risk') and result['risk']!=case['risk']):
            failures.append({'id':case['id'],'missing':missing,'unexpected':unexpected,'risk':result['risk'],'expected':case.get('risk')})
    return {'total':len(cases),'passed':len(cases)-len(failures),'failed':failures,'limitations':'Testes de roteador heurístico; não testam LLM, spawn real, qualidade do código ou produção.'}

def audit_template(project):
    return {'schema':'guardian-audit-1','project':str(Path(project).resolve()),'created_at':datetime.now(timezone.utc).isoformat(),
      'commit':'not_verified','note':'Template vazio; não representa auditoria realizada.',
      'capabilities':[{'id':c['id'],'status':'nao_verificado','reason':'Pendente','evidence':[],'severity':'unknown'} for c in load('taxonomy-v3.json')['capabilities']],
      'findings':[],'approvals':[],'limitations':['Nenhuma verificação foi realizada.']}

def gate(report):
    def invalid(message):
        return {'decision':'BLOCKED','errors':[message],'unverified':0,'partial_or_failed':0,'high_or_critical_failed':[], 'note':'Relatório inválido; nenhuma autorização concedida.'}
    if not isinstance(report,dict):return invalid('Relatório precisa ser objeto')
    if not isinstance(report.get('capabilities'),list):return invalid('Capabilities precisa ser lista')
    if any(not isinstance(c,dict) or not isinstance(c.get('id'),str) or not isinstance(c.get('status'),str) for c in report['capabilities']):
        return invalid('Capacidade precisa ter ID e status textuais')
    allowed={'atendido','parcial','nao_atendido','nao_aplicavel','nao_verificado'}
    valid={c['id'] for c in load('taxonomy-v3.json')['capabilities']};found=set();errors=[];unknown=partial=0;critical=[]
    for c in report.get('capabilities',[]):
        id=c.get('id');s=c.get('status')
        if id in found:errors.append('Capacidade duplicada '+str(id))
        found.add(id)
        if id not in valid or s not in allowed:errors.append('ID/status inválidos '+str(id));continue
        if c.get('severity') not in ('critical','high','medium','low','info','unknown'):
            errors.append('Severidade de capacidade inválida '+id)
        evidence=c.get('evidence')
        if s=='atendido' and (not isinstance(evidence,list) or not evidence or any(not isinstance(e,str) or not e.strip() for e in evidence)):errors.append('Atendido sem evidência textual válida '+id)
        reason=c.get('reason')
        if s=='nao_aplicavel' and (not isinstance(reason,str) or not reason.strip()):errors.append('N/A sem justificativa '+id)
        if s=='nao_verificado':unknown+=1
        if s in ('parcial','nao_atendido'):partial+=1
        if c.get('severity') in ('critical','high') and s in ('nao_atendido','parcial','nao_verificado'):critical.append(id)
    findings=report.get('findings',[])
    if not isinstance(findings,list):errors.append('Findings precisa ser lista')
    else:
        for index,f in enumerate(findings):
            if not isinstance(f,dict):errors.append('Finding inválido '+str(index));continue
            if f.get('severity') not in ('critical','high','medium','low','info'):
                errors.append('Severidade de finding inválida '+str(index))
            if f.get('severity') in ('critical','high'):
                critical.append('finding:'+str(f.get('id',index)))
    if found!=valid:errors.append(f'Cobertura incompleta: {len(valid-found)} ausentes')
    decision='BLOCKED' if errors or critical else 'UNKNOWN' if unknown else 'CONDITIONAL' if partial else 'READY_FOR_HUMAN_REVIEW'
    return {'decision':decision,'errors':errors,'unverified':unknown,'partial_or_failed':partial,'high_or_critical_failed':critical,
     'note':'Resultado lógico, não valida a autenticidade das evidências e NUNCA autoriza deployment.'}

def main():
    ap=argparse.ArgumentParser(description='Guardian v2: operação estática local, sem executar código de projeto.')
    sub=ap.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('inspect');p.add_argument('--project',default='.')
    p=sub.add_parser('route');p.add_argument('--project');g=p.add_mutually_exclusive_group(required=True);g.add_argument('--prompt');g.add_argument('--prompt-file');p.add_argument('--mode',choices=['auto','build','audit','remediate'],default='auto')
    p=sub.add_parser('assess');p.add_argument('--project',default='.');p.add_argument('--profile',required=True)
    sub.add_parser('validate');sub.add_parser('eval')
    p=sub.add_parser('audit-template');p.add_argument('--project',default='.');p.add_argument('--out',required=True)
    p=sub.add_parser('gate');p.add_argument('--report',required=True)
    a=ap.parse_args()
    try:
        if a.cmd=='inspect':out=inspect_project(a.project)
        elif a.cmd=='route':out=route(a.prompt if a.prompt is not None else Path(a.prompt_file).read_text(encoding='utf8'),inspect_project(a.project) if a.project else None,a.mode)
        elif a.cmd=='assess':out=assess(a.project,json.loads(Path(a.profile).read_text(encoding='utf8')))
        elif a.cmd=='validate':out=validate()
        elif a.cmd=='eval':out=evals()
        elif a.cmd=='audit-template':
            p=Path(a.out).expanduser().resolve()
            if p.exists():raise ValueError('Arquivo já existe; não será sobrescrito: '+str(p))
            p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(audit_template(a.project),ensure_ascii=False,indent=2),encoding='utf8')
            out={'created':str(p),'status':'132 capacidades não verificadas — template, não auditoria'}
        else:out=gate(json.loads(Path(a.report).read_text(encoding='utf8')))
        print(json.dumps(out,ensure_ascii=False,indent=2))
        return 1 if out.get('ok') is False or out.get('failed') or out.get('errors') or out.get('decision')=='BLOCKED' else 0
    except (ValueError,OSError,KeyError,json.JSONDecodeError) as ex:
        print(json.dumps({'error':str(ex)},ensure_ascii=False),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
