"""Correlate supported native tool records, not arbitrary model success claims."""
import json,re

def paired_outcomes(payloads,case):
    calls={p['call_id']:p for p in payloads if p.get('type') in ('function_call','custom_tool_call') and isinstance(p.get('call_id'),str)}
    results=[]
    for output in payloads:
        if output.get('type') not in ('function_call_output','custom_tool_call_output'):continue
        call=calls.get(output.get('call_id'),{})
        code=call.get('input',call.get('arguments',''))
        if not isinstance(code,str) or not re.search(r'python\s+-B\s+check\.py',code):continue
        # Current harness requires the concrete case cwd in the tool invocation.
        if 'workdir' not in code or case['id'] not in code:continue
        blocks=output.get('output',[])
        if isinstance(blocks,str):blocks=[{'text':blocks}]
        if not isinstance(blocks,list):continue
        for block in blocks:
            try:data=json.loads(block.get('text','')) if isinstance(block,dict) else None
            except (ValueError,TypeError):continue
            # Current A00 uses a parallel batch, check command at index zero.
            if isinstance(data,dict) and data.get('i')==0 and isinstance(data.get('value'),dict):data=data['value']
            if isinstance(data,dict) and type(data.get('exit_code')) is int and isinstance(data.get('output'),str):
                results.append(data['exit_code'])
    return results

def fixture_passed(outcomes,rule):
    if rule.get('build'):
        return len(outcomes)>=2 and (1 in outcomes if rule.get('seeded_failure') else outcomes[0]==0) and outcomes[-1]==0
    return bool(outcomes) and outcomes[-1]==(1 if rule.get('seeded_failure') else 0)
