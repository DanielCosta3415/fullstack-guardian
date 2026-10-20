"""Canonical typed catalog derived from reviewed profiles; no profile execution."""
from __future__ import annotations
import hashlib,json,re,unicodedata
from pathlib import Path
try:
    from .guardian_registry import discover, _contained
except ImportError:
    from guardian_registry import discover, _contained
ROOT=Path(__file__).resolve().parent.parent
FIELDS={'id','name','aliases','kind','file','sha256','competencies','modes','tool_requirements','model_policy','reviewer','source','license','profile'}
def normalize(value):return unicodedata.normalize('NFKC',value).casefold().replace('-','_')
def observed_catalog_document(root=ROOT):
    root=Path(root).absolute()
    # Validate every declared profile and namespace before catalog hashing. In
    # particular a manifest must never turn a catalog check into an outside read.
    trusted=discover(root)
    agents=json.loads(_contained(root/'core/agents.json',root).read_text(encoding='utf-8'))['agents']; records=[]
    for entry in agents:
        records.append({'id':entry['id'],'name':entry['name'],'aliases':[], 'kind':'core','file':entry['file'],
          'sha256':hashlib.sha256(_contained(root/entry['file'],root).read_bytes()).hexdigest(),'competencies':entry.get('keywords',[]),
          'modes':['audit','build','remediate','explore'],'tool_requirements':[], 'model_policy':'inherit',
          'reviewer':'G02' if entry['id']=='G01' else 'G01','source':'guardian_original','license':'MIT'})
    for pack in trusted['packs']:
        manifest=_contained(root/'packs'/pack['name']/'manifest.json',root)
        doc=json.loads(manifest.read_text(encoding='utf-8'))
        for entry in doc['agents']:
            if not isinstance(entry,dict) or not isinstance(entry.get('file'),str) or not re.fullmatch(r'agents/[a-z][a-z0-9_-]*\.toml',entry['file']):
                raise ValueError('Invalid pack profile path before hashing')
            profile=_contained(manifest.parent/entry['file'],manifest.parent)
            rel=profile.relative_to(root).as_posix()
            records.append({'id':'pack:'+doc['name']+':'+entry['name'],'name':entry['name'],'aliases':[], 'kind':'optional','file':rel,
              'sha256':hashlib.sha256(_contained(root/rel,root).read_bytes()).hexdigest(),'competencies':entry.get('keywords',[]),
              'modes':['audit','build','remediate','explore'],'tool_requirements':[], 'model_policy':'inherit','reviewer':'G01',
              'source':'guardian_reviewed_adaptation','license':'MIT'})
    return {'schema_version':1,'records':records}
def validate_catalog(root=ROOT):
    root=Path(root).absolute();doc=json.loads(_contained(root/'core/contracts-catalog-v1.json',root).read_text(encoding='utf-8'))
    if not isinstance(doc,dict) or set(doc)!={'schema_version','records','metadata_documents'} or doc['schema_version']!=1 or not isinstance(doc['records'],list):raise ValueError('Invalid canonical catalog')
    ids=set();names=set()
    for r in doc['records']:
        if not isinstance(r,dict) or set(r)!=FIELDS:raise ValueError('Unknown/missing catalog contract field')
        if r['id'] in ids:raise ValueError('Duplicate stable ID')
        ids.add(r['id'])
        for name in [r['name']]+r['aliases']:
            key=normalize(name)
            if key in names:raise ValueError('Normalized alias/name collision')
            names.add(key)
        if r['model_policy']!='inherit' or r['reviewer']==r['id']:raise ValueError('Invalid inherited policy/reviewer')
    generated_outputs(root, check=True)
    expected=observed_catalog_document(root)
    for record in expected['records']:record['profile']=next(r['profile'] for r in doc['records'] if r['id']==record['id'])
    expected['metadata_documents']=doc['metadata_documents']
    if doc!=expected:raise ValueError('Canonical catalog metadata drift')
    return {'valid':True,'profiles':len(doc['records']),'source':'core/contracts-catalog-v1.json'}
def catalog_document(root=ROOT):
    """Reviewed source of truth. Editing generated profiles cannot update it."""
    root=Path(root).absolute()
    discover(root)  # Reject unsafe generated manifest paths before accessing catalog.
    return json.loads(_contained(root/'core/contracts-catalog-v1.json',root).read_text(encoding='utf8'))


def generated_outputs(root=ROOT, check=True):
    """Generate ONLY known profile/metadata paths; never config, model or permissions."""
    import tomllib
    root=Path(root).absolute();doc=catalog_document(root);outputs={}
    if set(doc)!={'schema_version','records','metadata_documents'} or doc['schema_version']!=1:raise ValueError('Invalid canonical schema')
    if not isinstance(doc.get('records'),list) or not doc['records']:raise ValueError('Expected reviewed profiles')
    for record in doc['records']:
        if not isinstance(record,dict) or set(record)!=FIELDS or record.get('model_policy')!='inherit':raise ValueError('Unknown canonical field or model override')
        profile=record.get('profile')
        if not isinstance(profile,dict) or set(profile)!={'name','description','developer_instructions'} or any(not isinstance(v,str) for v in profile.values()):
            raise ValueError('Canonical profile permits only name, description and instructions')
        if profile['name']!=record['name']:raise ValueError('Canonical profile identity mismatch')
        rel=record['file']
        if not isinstance(rel,str) or not re.fullmatch(r'(?:global/agents/[a-z][a-z0-9_]*|packs/[a-z][a-z0-9_-]*/agents/[a-z][a-z0-9_]*)\.toml',rel):raise ValueError('Invalid generated profile path')
        text=''.join(key+' = '+json.dumps(profile[key],ensure_ascii=False)+'\n' for key in ('name','description','developer_instructions'))
        if tomllib.loads(text)!=profile:raise ValueError('Profile serialization mismatch')
        outputs[rel]=text.encode('utf8')
        if hashlib.sha256(outputs[rel]).hexdigest()!=record['sha256']:raise ValueError('Canonical generated profile hash mismatch')
    metadata=doc.get('metadata_documents')
    if not isinstance(metadata,dict) or 'core/agents.json' not in metadata:raise ValueError('Missing canonical metadata')
    expected_metadata={'core/agents.json'}|{'/'.join(r['file'].split('/')[:2])+'/manifest.json' for r in doc['records'] if r['kind']=='optional'}
    if set(metadata)!=expected_metadata:raise ValueError('Canonical metadata membership mismatch')
    for rel,value in metadata.items():
        if not isinstance(value,dict) or not isinstance(value.get('agents'),list):raise ValueError('Invalid canonical metadata entries')
        if rel=='core/agents.json':
            actual={(e.get('id'),e.get('name'),e.get('file')) for e in value['agents'] if isinstance(e,dict)}
            expected={(r['id'],r['name'],r['file']) for r in doc['records'] if r['kind']=='core'}
        else:
            prefix=rel.rsplit('/',1)[0]
            if value.get('name')!=prefix.split('/')[-1]:raise ValueError('Canonical pack name mismatch')
            actual={(e.get('name'),prefix+'/'+str(e.get('file'))) for e in value['agents'] if isinstance(e,dict)}
            expected={(r['name'],r['file']) for r in doc['records'] if r['file'].startswith(prefix+'/')}
        if actual!=expected or len(actual)!=len(value['agents']):raise ValueError('Canonical profile/metadata identity mismatch')
        if rel!='core/agents.json' and not re.fullmatch(r'packs/[a-z][a-z0-9_-]*/manifest\.json',rel):raise ValueError('Invalid generated metadata path')
        outputs[rel]=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf8')
    if len(outputs)!=len(doc['records'])+len(metadata):raise ValueError('Duplicate generated path')
    # Preflight every target before any write; output never includes user configuration.
    paths={rel:_contained(root/rel,root) for rel in outputs}
    if check:
        for rel,path in paths.items():
            # Cross-platform checkout newlines do not change TOML semantics.
            if not path.is_file() or path.read_bytes().replace(b'\r\n',b'\n')!=outputs[rel]:raise ValueError('Generated catalog drift: '+rel)
    else:
        for rel,path in paths.items():path.write_bytes(outputs[rel])
    return {'valid':True,'generated':len(outputs),'permissions_granted':False}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--write',action='store_true',help='Generate reviewed canonical outputs; never import local profile edits');a=p.parse_args()
    if a.write:generated_outputs(check=False)
    print(json.dumps(validate_catalog()))


def eligible_pack_profiles(root=ROOT, codex_home=None, available_roles=None, capabilities=None):
    """Read actual receipt/config/bytes before optional selection.

    Caller role inventory is a declaration, not native execution evidence. The
    hash-addressed local capability observation is retained for review; it grants
    no authorization and is not a signature or authenticated runtime attestation.
    """
    import tomllib, platform
    try:
        from .guardian_capabilities import probe_version
    except ImportError:
        from guardian_capabilities import probe_version
    try:
        from .guardian_registry import discover, _contained
    except ImportError:
        from guardian_registry import discover, _contained
    empty={'profiles':[],'state_hash':None,'inventory_status':'declared_not_authenticated','native_verified':False,'limitations':[]}
    if codex_home is None or not available_roles or not capabilities:
        return {**empty,'limitations':['Optional roles require installation, enabled configuration, local capability observation and caller role inventory.']}
    if not isinstance(available_roles,list) or any(not isinstance(x,str) for x in available_roles) or len(available_roles)!=len(set(available_roles)):
        raise ValueError('Role inventory must be a unique string list')
    if not isinstance(capabilities,dict):raise ValueError('Invalid capabilities context')
    home=Path(codex_home).absolute()
    config_path=_contained(home/'config.toml',home); receipt_path=_contained(home/'guardian-packs.json',home)
    if not config_path.is_file() or not receipt_path.is_file():
        return {**empty,'limitations':['No enabled config or managed pack receipt.']}
    if config_path.stat().st_size>4*1024*1024 or receipt_path.stat().st_size>4*1024*1024:raise ValueError('Oversized configuration/receipt')
    config_raw=config_path.read_bytes(); receipt_raw=receipt_path.read_bytes()
    config=tomllib.loads(config_raw.decode('utf-8')); receipt=json.loads(receipt_raw)
    if not isinstance(receipt,dict) or receipt.get('schema_version')!=1 or not isinstance(receipt.get('packs'),dict):
        raise ValueError('Invalid optional pack receipt')
    catalog=discover(root,codex_home=home)
    agents=config.get('agents',{})
    if not isinstance(agents,dict):raise ValueError('Invalid enabled agents config')
    feature_evidence=capabilities.get('capabilities',{})
    if not isinstance(feature_evidence,dict):raise ValueError('Malformed capabilities map')
    observation=feature_evidence.get('spawn',{})
    if not isinstance(observation,dict):raise ValueError('Malformed spawn observation')
    ref=observation.get('evidence','') if isinstance(observation,dict) else ''
    compatible=False; proof_digest=None
    local_version=probe_version() if observation.get('status')=='verified' else None
    if capabilities.get('os')==platform.system() and capabilities.get('client')=='cli' and local_version is not None and capabilities.get('version')==local_version and observation.get('status')=='verified' and isinstance(ref,str) and ref.startswith('file:') and '#sha256=' in ref and capabilities.get('client') and capabilities.get('version') and capabilities.get('os'):
        source,digest=ref[5:].rsplit('#sha256=',1)
        if re.fullmatch('[a-f0-9]{64}',digest):
            proof=Path(source).absolute()
            # Reuse reparse/traversal checks with the declared observation folder.
            _contained(proof,proof.parent)
            if proof.is_file() and proof.stat().st_size<=4*1024*1024 and hashlib.sha256(proof.read_bytes()).hexdigest()==digest:
                proof_doc=json.loads(proof.read_text(encoding='utf-8'))
                compatible=isinstance(proof_doc,dict) and set(proof_doc)=={'schema_version','client','version','os','observed_capability','available_roles'} and proof_doc.get('schema_version')==1 and all(proof_doc.get(k)==capabilities[k] for k in ('client','version','os')) and proof_doc.get('observed_capability')=='spawn' and proof_doc.get('available_roles')==available_roles
                proof_digest=digest if compatible else None
    features=config.get('features',{})
    if not isinstance(features,dict):raise ValueError('Invalid feature enablement config')
    enabled=agents.get('enabled') is True and features.get('multi_agent',True) is not False
    profiles=[]; states=[]
    for pack in catalog['packs']:
        owned=receipt['packs'].get(pack['name'],{})
        expected_files={a['name']+'.toml' for a in pack['agents']}
        if not isinstance(owned,dict) or not isinstance(owned.get('files'),dict) or set(owned['files'])!=expected_files:
            states.append([pack['name'],'receipt_missing_or_mismatched']);continue
        if owned.get('manifest_sha256')!=pack.get('manifest_sha256'):
            states.append([pack['name'],'manifest_drift']);continue
        for entry in pack['agents']:
            role=entry['name']; installed=entry.get('installed') is True and owned['files'].get(role+'.toml')==entry.get('sha256')
            role_config=agents.get(role,{})
            role_enabled=enabled and (not isinstance(role_config,dict) or role_config.get('enabled',True) is not False)
            states.append([role,entry.get('sha256'),installed,role_enabled,compatible,role in available_roles])
            if installed and role_enabled and compatible and role in available_roles:
                terms=[word for word in re.split(r'[_\- ]+',role+' '+pack['name']) if len(word)>2 and word not in {'guardian','specialist','systems','runtime'}]
                if pack['name']=='dotnet':terms+=['.net','asp.net','c#']
                profiles.append({'id':'pack:'+pack['name']+':'+role,'name':role,'keywords':sorted(set(terms)), 'installed':True,'enabled':True,'compatible':True,'file':entry['file'],'native_verified':False})
    state={'receipt':hashlib.sha256(receipt_raw).hexdigest(),'config':hashlib.sha256(config_raw).hexdigest(),'roles':available_roles,'proof':proof_digest,'current_version':local_version,'current_os':platform.system(),'states':states}
    return {'profiles':profiles,'state_hash':hashlib.sha256(json.dumps(state,sort_keys=True).encode()).hexdigest(),
            'inventory_status':'declared_not_authenticated','native_verified':False,
            'limitations':['Hash-checked local supervisor observations and caller inventory are not authenticated native execution evidence.']}
