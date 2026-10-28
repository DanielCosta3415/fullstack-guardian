"""Correlate the strict tool-call subset required by the native harness.

Unknown JS/tool batching shapes fail closed. This is not a general JS parser or
proof against a malicious same-account writer of all session evidence.
"""
import ast,json,re

OBJECT=re.compile(r"tools\.exec_command\(\s*(\{[^{}]{1,16000}\})\s*\)",re.S)
STRING=r"(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')"

def specifications(source):
    try:
        data=json.loads(source)
        return [data] if isinstance(data,dict) else []
    except ValueError:pass
    single=re.fullmatch(r'\s*text\(await tools\.exec_command\((\{[^{}]{1,16000}\})\)\);?\s*',source,re.S)
    if single:objects=[single[1]]
    else:
        batch=re.fullmatch(r'\s*const results = await Promise\.allSettled\(\[(.*?)\]\);\s*results\.forEach\(\(r,i\)=>text\(\{i,\.\.\.r\}\)\);?\s*',source,re.S)
        if not batch:return []
        objects=[m[1] for m in OBJECT.finditer(batch[1])]
        if not objects or OBJECT.sub('',batch[1]).strip(' \r\n\t,'):return []
    specs=[]
    for obj in objects:
        obj=re.sub(r'(?<=[{,])\s*(cmd|workdir|max_output_tokens|yield_time_ms)\s*:',r'"\1":',obj)
        try:value=ast.literal_eval(obj)
        except (ValueError,SyntaxError):return []
        if not isinstance(value,dict) or set(value)-{'cmd','workdir','max_output_tokens','yield_time_ms'}:return []
        specs.append(value)
    return specs

def same_path(a,b):
    if not isinstance(a,str) or not isinstance(b,str):return False
    a=a.replace('\\','/').rstrip('/');b=b.replace('\\','/').rstrip('/')
    return a.casefold()==b.casefold() if re.match(r'^[A-Za-z]:/',b) else a==b

def paired_outcomes(payloads,case,*,details=False):
    calls={p['call_id']:p for p in payloads if p.get('type') in ('function_call','custom_tool_call') and isinstance(p.get('call_id'),str)}
    results=[];seen_results=set()
    for output in payloads:
        if output.get('type') not in ('function_call_output','custom_tool_call_output'):continue
        call=calls.get(output.get('call_id'),{})
        source=call.get('input',call.get('arguments',''))
        if not isinstance(source,str) or len(source)>64000:continue
        if call.get('name') in ('exec','functions.exec'):
            if call.get('type')!='custom_tool_call' or source.lstrip().startswith('{'):continue
        elif call.get('name') in ('exec_command','functions.exec_command'):
            if call.get('type')!='function_call' or not source.lstrip().startswith('{'):continue
        else:continue
        objects=specifications(source)
        specs=[obj.get('cmd')=='python -B check.py' and same_path(obj.get('workdir'),case.get('case_directory')) for obj in objects]
        blocks=output.get('output',[])
        if isinstance(blocks,str):blocks=[{'text':blocks}]
        if not isinstance(blocks,list):continue
        for block in blocks:
            try:data=json.loads(block.get('text','')) if isinstance(block,dict) else None
            except (ValueError,TypeError):continue
            if not isinstance(data,dict):continue
            if 'i' in data:
                index=data['i']
                if type(index) is not int or not 0<=index<len(specs) or data.get('status')!='fulfilled':continue
                data=data.get('value')
            elif len(specs)==1:index=0
            else:continue
            if specs[index] and isinstance(data,dict) and type(data.get('exit_code')) is int and isinstance(data.get('output'),str):
                identity=(call['call_id'],index)
                if identity in seen_results:return []
                seen_results.add(identity)
                results.append({'exit_code':data['exit_code'],'output':data['output'],'call_id':call['call_id']} if details else data['exit_code'])
    return results

def fixture_passed(outcomes,rule):
    # Schema 1 is historical smoke only; callers must not call it qualification.
    if rule.get('schema_version') == 2:
        if not outcomes or any(not isinstance(o,dict) for o in outcomes):return False
        codes=[o.get('exit_code') for o in outcomes]
        def expected_failure(o):
            text=o.get('output','')
            # stdout JSON may be drained after stderr. Remove only complete JSON
            # containers at the boundaries, never search JSON strings for assertions.
            # Full output remains bound to exact command + cwd by paired_outcomes.
            if not isinstance(text,str):return False
            decoder=json.JSONDecoder()
            text=text.strip()
            while text:
                try:value,end=decoder.raw_decode(text)
                except ValueError:break
                if not isinstance(value,(dict,list)) or (end<len(text) and text[end] not in '\r\n'):break
                text=text[end:].strip()
            lines=text.splitlines()
            for start in range(len(lines)):
                if lines[start].strip() and not lines[start].lstrip().startswith(('{','[')):continue
                suffix='\n'.join(lines[start:]).strip()
                while suffix:
                    try:value,end=decoder.raw_decode(suffix)
                    except ValueError:break
                    if not isinstance(value,(dict,list)) or (end<len(suffix) and suffix[end] not in '\r\n'):break
                    suffix=suffix[end:].strip()
                if not suffix:
                    lines=lines[:start]
                    break
            expected=['AssertionError: '+reason for reason in rule.get('expected_assertions',[])]
            # Reject incompatible exception summaries even before a chained assertion.
            # ExceptionGroup uses a tree instead of column-zero summaries; it is
            # not the single seeded assertion required by this rule.
            if any('Exception Group Traceback' in line or re.match(r'^\s*[|+] .*',line) for line in lines):return False
            if any(re.match(r'^[A-Za-z_][\w.]*:',line) and line not in expected for line in lines):return False
            lines=[line.strip() for line in lines if line.strip()]
            return type(o.get('exit_code')) is int and o['exit_code']==1 and bool(lines) and lines[-1] in expected
        if rule.get('build'):
            return len(outcomes)>=2 and (expected_failure(outcomes[0]) if rule.get('seeded_failure') else codes[0]==0) and codes[-1]==0
        return expected_failure(outcomes[-1]) if rule.get('seeded_failure') else codes[-1]==0
    if rule.get('build'):
        return len(outcomes)>=2 and (1 in outcomes if rule.get('seeded_failure') else outcomes[0]==0) and outcomes[-1]==0
    return bool(outcomes) and outcomes[-1]==(1 if rule.get('seeded_failure') else 0)
