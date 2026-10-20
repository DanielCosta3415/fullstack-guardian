"""Closed task/result contracts. Validation is never authorization or a sandbox."""
from __future__ import annotations
from pathlib import PurePosixPath
import re

FIELDS = {'goal','allowed_paths','read_paths','checks','operation','retry','idempotent','budget','acceptance','prohibited_effects','tool_requirements','authorization'}
PROHIBITED = ['privilege_escalation','external_mutation','credential_access','policy_override']

def default_contract(goal, phase_criteria):
    return {'goal':goal,'allowed_paths':[],'read_paths':['**'],'checks':[], 'operation':'read',
            'retry':0,'idempotent':True,'budget':{'timeout_seconds':600,'max_output_bytes':1048576},
            'acceptance':list(phase_criteria),'prohibited_effects':list(PROHIBITED),
            'tool_requirements':[], 'authorization':None}

def _paths(value, read=False):
    if not isinstance(value,list) or any(not isinstance(x,str) for x in value) or len(value)!=len(set(value)):
        raise ValueError('Path scope must be a unique list')
    for path in value:
        if not isinstance(path,str) or not path or '\\' in path or ':' in path or '\x00' in path or path.startswith('/'):
            raise ValueError('Scope must use relative POSIX paths')
        if '..' in PurePosixPath(path).parts or '.' in path.split('/') or '//' in path:
            raise ValueError('Traversal/ambiguous scope forbidden')
        if any(part.endswith((' ','.')) for part in path.split('/')):
            raise ValueError('OS-ambiguous trailing dot/space forbidden')
        if '*' in path and not ((read and path=='**') or (path.endswith('/**') and '*' not in path[:-3])):
            raise ValueError('Only directory/** wildcard is supported')
        if not read and path == '**':
            raise ValueError('Unbounded write scope forbidden')

def validate_task_contract(task, executable=False):
    c=task.get('contract') if isinstance(task,dict) else None
    if not isinstance(c,dict) or set(c)!=FIELDS:
        raise ValueError('Missing/unknown task contract fields')
    if not isinstance(c['goal'],str) or not c['goal'].strip() or len(c['goal'])>8000:
        raise ValueError('Task goal required')
    _paths(c['allowed_paths']); _paths(c['read_paths'],read=True)
    if c['operation'] not in ('read','write') or type(c['idempotent']) is not bool:
        raise ValueError('Invalid operation/idempotence')
    if type(c['retry']) is not int or not 0<=c['retry']<=2 or (c['retry'] and (not c['idempotent'] or c['operation']!='read')):
        raise ValueError('Retry requires bounded proven read-only idempotence')
    if c['operation']=='read' and c['allowed_paths']:
        raise ValueError('Read task may not declare writes')
    if executable and c['operation']=='write' and (not c['allowed_paths'] or not c['checks']):
        raise ValueError('Executable write requires explicit file scope and checks')
    checks=c['checks']
    if not isinstance(checks,list) or any(not isinstance(argv,list) or not argv or any(not isinstance(x,str) or not x or '\x00' in x for x in argv) for argv in checks):
        raise ValueError('Checks must be argv arrays, never shell strings')
    budget=c['budget']
    if not isinstance(budget,dict) or set(budget)!={'timeout_seconds','max_output_bytes'} or type(budget['timeout_seconds']) is not int or not 1<=budget['timeout_seconds']<=3600 or type(budget['max_output_bytes']) is not int or not 1024<=budget['max_output_bytes']<=16777216:
        raise ValueError('Invalid resource budget')
    if not isinstance(c['acceptance'],list) or not c['acceptance'] or any(not isinstance(x,str) or not x.strip() for x in c['acceptance']):
        raise ValueError('Acceptance criteria required')
    if not isinstance(c['prohibited_effects'],list) or any(not isinstance(x,str) for x in c['prohibited_effects']) or not set(PROHIBITED)<=set(c['prohibited_effects']):
        raise ValueError('Non-negotiable prohibitions missing')
    if not isinstance(c['tool_requirements'],list) or any(not isinstance(x,str) or not re.fullmatch(r'[a-zA-Z0-9_.:-]{1,128}',x) for x in c['tool_requirements']):
        raise ValueError('Invalid tool requirement')
    if c['authorization'] is not None:
        raise ValueError('Untrusted plan may not embed authorization; use supervisor grant')
    return c

def validate_finding(finding):
    fields={'id','classification','priority','impact','preconditions','evidence','limitations'}
    if not isinstance(finding,dict) or set(finding)!=fields:
        raise ValueError('Finding requires exact evidence contract')
    if finding['classification'] not in ('fact','hypothesis','style') or finding['priority'] not in ('P0','P1','P2','P3','info'):
        raise ValueError('Invalid finding classification/priority')
    for field in ('id','impact','preconditions'):
        if not isinstance(finding[field],str) or not finding[field].strip(): raise ValueError('Missing '+field)
    if not isinstance(finding['evidence'],list) or not finding['evidence'] or any(not isinstance(x,str) or not x.strip() for x in finding['evidence']):
        raise ValueError('Every finding needs a verifiable reference')
    if not isinstance(finding['limitations'],list): raise ValueError('Limitations required')
    if finding['classification']!='fact' and finding['priority'] in ('P0','P1'):
        raise ValueError('Critical priority requires factual impact evidence, not style or conjecture')
    return finding


def validate_result(result):
    """Validate output references without authenticating model-supplied claims."""
    fields={'task_id','status','facts','hypotheses','artifacts','limitations','findings'}
    if not isinstance(result,dict) or set(result)!=fields:
        raise ValueError('Unknown/missing task result fields')
    if not isinstance(result['task_id'],str) or not result['task_id']:
        raise ValueError('Result task identity required')
    if result['status'] not in ('produced','failed','blocked','not_verified'):
        raise ValueError('Model result cannot self-assert checked/reviewed/verified/integrated')
    if not isinstance(result['facts'],list):raise ValueError('Facts must be a list')
    for fact in result['facts']:
        if not isinstance(fact,dict) or set(fact)!={'statement','evidence'} or not isinstance(fact['statement'],str) or not fact['statement'].strip() or not isinstance(fact['evidence'],list) or not fact['evidence'] or any(not isinstance(e,str) or not e.strip() for e in fact['evidence']):
            raise ValueError('Fact without evidence reference')
    for field in ('hypotheses','limitations'):
        if not isinstance(result[field],list) or any(not isinstance(x,str) for x in result[field]):raise ValueError('Invalid '+field)
    if not isinstance(result['artifacts'],list):raise ValueError('Artifact list required')
    for artifact in result['artifacts']:
        if not isinstance(artifact,dict) or set(artifact)!={'path','sha256'} or not isinstance(artifact['sha256'],str) or not re.fullmatch(r'[0-9a-f]{64}',artifact['sha256']):raise ValueError('Artifact hash/reference required')
        _paths([artifact['path']])
    if not isinstance(result['findings'],list):raise ValueError('Findings must be list')
    for finding in result['findings']:validate_finding(finding)
    return {'valid':True,'authenticated_execution':False,'claims':result}
