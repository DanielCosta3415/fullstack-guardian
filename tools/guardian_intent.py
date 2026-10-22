"""Bounded intent obligations. Pattern candidates are advice, never semantic proof.

The primary interprets the request and may submit a strict declared contract.
Neither that JSON nor detected text is authorization or evidence of execution.
"""
from __future__ import annotations
import re
import unicodedata

DOMAINS = {
    'product': ('S01',), 'requirements': ('S02',), 'architecture': ('S03',),
    'frontend_architecture': ('S04',), 'frontend': ('S05',), 'accessibility': ('S06', 'S17'),
    'web_compatibility': ('S07',), 'backend': ('S08',), 'api': ('S09',),
    'concurrency': ('S10', 'S18'), 'database': ('S11',), 'data_governance': ('S12',),
    'security': ('S13', 'S14'), 'supply_chain': ('S15',), 'quality': ('S16',),
    'frontend_quality': ('S17',), 'backend_quality': ('S18',), 'performance': ('S19',),
    'resilience': ('S20',), 'observability': ('S21',), 'cloud': ('S22',),
    'delivery': ('S23',), 'maintenance': ('S24',), 'governance': ('S25',), 'ai': ('S26',),
}
RISK = ('low', 'medium', 'high', 'critical')
# Deliberately bounded PT/EN candidate rules. Unknown meanings require primary triage.
RULES = {
 'product': r'clientes precisam|customers need|validate.*(?:demand|hypothes)|validar.*hipotes|antes de construir|before building',
 'requirements': r'criterios de aceitacao|acceptance criteria|verifiable requirements',
 'frontend_architecture': r'propriedade do estado|state ownership|entre componentes|routing architecture',
 'accessibility': r'\b(?:a11y|aria|wcag|teclado|keyboard|focus trap)\b|nao usa mouse|without.*mouse|foco perdido|screen reader|leitor de tela',
 'web_compatibility': r'\b(?:inp|lcp|cls|i18n|rtl|locale|pluralizacao|plural rules)\b|right.to.left|formatos de data|outros paises',
 'backend': r'registros somem|records disappear|apos reiniciar|after restarting',
 'api': r'\bopenapi\b|sem quebrar consumidores|without breaking consumers|contract compatibility',
 'concurrency': r'duas vezes|twice|same.*(?:message|order).*again|mesma mensagem|duplicate delivery|idempoten',
 'database': r'\b(?:postgresql|constraints|sqlite)\b|registros somem|records disappear',
 'data_governance': r'\b(?:cdc|lakehouse|linhagem|retencao|lineage|retention)\b|restauracao de backups|backup restor',
 'security': r'cross.tenant|multi.tenant|outra empresa|outra organizacao|outra conta|entre organizacoes|another.*(?:organization|company|account)|\b(?:ssrf|xss|csrf)\b',
 'supply_chain': r'\b(?:sbom|supply.chain)\b|dependencias transitivas|transitive dependencies',
 'frontend_quality': r'\bplaywright\b|testes.*jornada|journey.*test',
 'backend_quality': r'testar contrato|test.*api contract|contrato da api',
 'performance': r'\bp99\b|gargalo|bottleneck',
 'resilience': r'\b(?:slo|sli|rto|rpo)\b|error budget',
 'observability': r'\b(?:traces|logs|telemetry)\b',
 'cloud': r'\b(?:terraform|aws|azure|gcp)\b|infraestrutura|infrastructure',
 'delivery': r'\b(?:ci/cd|pipeline)\b',
 'maintenance': r'migracao de versao|version migration|descomission|decommission|sistema legado|legacy system',
 'governance': r'fornecedores|vendors|obrigacoes contratuais|contractual obligations|finops|governanca|governance',
}

def _norm(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))

def _strings(value, field, nonempty=True):
    if not isinstance(value, list) or (nonempty and not value) or len(value) > 64 or any(not isinstance(x, str) or not x.strip() or len(x) > 2000 for x in value):
        raise ValueError('Invalid intent ' + field)

def validate_intent(contract):
    """Closed schema validation; declared meaning does not grant authority."""
    fields = {'schema_version', 'goals', 'obligations', 'risk', 'constraints', 'uncertainties'}
    if not isinstance(contract, dict) or set(contract) != fields or type(contract['schema_version']) is not int or contract['schema_version'] != 1:
        raise ValueError('Invalid intent contract schema')
    for name in ('goals', 'constraints', 'uncertainties'):
        _strings(contract[name], name, nonempty=name == 'goals')
    if not isinstance(contract['risk'], str) or contract['risk'] not in RISK:
        raise ValueError('Invalid intent risk')
    obs = contract['obligations']
    if not isinstance(obs, list) or not obs or len(obs) > 64:
        raise ValueError('Intent obligations required')
    seen = set()
    for item in obs:
        if not isinstance(item, dict) or set(item) != {'id', 'domain', 'acceptance', 'evidence'}:
            raise ValueError('Invalid intent obligation fields')
        if not isinstance(item['id'], str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', item['id']) or item['id'] in seen:
            raise ValueError('Invalid or duplicate obligation id')
        seen.add(item['id'])
        if not isinstance(item['domain'], str) or item['domain'] not in DOMAINS:
            raise ValueError('Unknown intent obligation domain')
        _strings(item['acceptance'], 'acceptance')
        _strings(item['evidence'], 'evidence')
    return contract

def interpret_candidates(prompt, contract=None):
    text = _norm(prompt)
    detected = sorted(domain for domain, pattern in RULES.items() if re.search(pattern, text))
    if contract is not None:
        validate_intent(contract)
    declared = sorted({o['domain'] for o in contract['obligations']}) if contract else []
    domains = sorted(set(detected + declared))
    floor = 'high' if {'security', 'concurrency'} & set(domains) else 'medium' if {'database', 'cloud', 'governance', 'data_governance', 'architecture'} & set(domains) else 'low'
    if contract:
        floor = RISK[max(RISK.index(floor), RISK.index(contract['risk']))]
    return {
        'source': 'primary_declared_with_pattern_candidates' if contract else 'pattern_candidates_only',
        'contract': contract, 'candidate_domains': domains, 'detected_domains': detected,
        'minimum_risk': floor, 'primary_interpretation_required': contract is None,
        'deviations': [
            {'domain': domain, 'reason': 'Primary-declared obligation not detected by bounded patterns; retained for coverage.'} for domain in sorted(set(declared)-set(detected))
        ] + [
            {'domain': domain, 'reason': 'Pattern candidate absent from primary contract; retained pending relevance adjudication, never silently waived.'} for domain in sorted(set(detected)-set(declared))
        ] if contract else [],
        'semantic_understanding_verified': False, 'content_is_authority': False,
        'uncertainties': list(contract['uncertainties']) if contract else ['Primary must verify intent, omissions and irrelevant candidates before delegation.'],
        'obligation_coverage': [
            {'id': o['id'], 'domain': o['domain'], 'candidate_agents': list(DOMAINS[o['domain']]), 'acceptance': o['acceptance'], 'evidence_required': o['evidence']}
            for o in contract['obligations']
        ] if contract else [
            {'id': 'candidate-' + domain, 'domain': domain, 'candidate_agents': list(DOMAINS[domain]), 'acceptance': [], 'evidence_required': [], 'status': 'requires_primary_adjudication'} for domain in domains
        ],
    }
