"""Preserve source identifiers when projecting Interslavic LaTeX to Cyrillic.

OpenAI Codex, GPT-6 Astra, Ultra effort; 2026-10-24.
This deterministic postprocessor uses corresponding Latin-source mbox labels.
It does not translate prose or replace the historical script converter.
"""
import argparse,re
from pathlib import Path

BOX=re.compile(r'\\mbox\{([^{}]*)\}')
LABEL=re.compile(r'[A-Za-z](?:\)|\\ [0-9]+)?')
CYR=dict(zip('ABCD EFG abcd efg'.replace(' ',''),'АБЦД ЕФГ абцд ефг'.replace(' ','')))
RULES={
    'lettered_item_or_reference':re.compile(r"(?<![\w\\])([A-Za-zА-Яа-яЈјЉљЊњЏџЅѕ])('?)(?=\))"),
    'formula_suffix':re.compile(r'\([0-9]+\.?\)([A-Za-zА-Яа-я])(?=[).,\s}])'),
    'section_suffix':re.compile(r'(?:§|\\S(?:\\|\s)*)(?:\s|\\)*[0-9]+[.,\s\\]*([A-Ha-hАБЦДЕФГХабцдефгх])(?=[).,\s}])'),
    'numbered_identifier_suffix':re.compile(r'(?<![\w])\d+([a-hабцдефгх])(?=[).,\s}])'),
}

def preserve(latin,cyrillic):
    a=list(BOX.finditer(latin));z=list(BOX.finditer(cyrillic))
    if len(a)!=len(z):raise ValueError('Corresponding mbox inventories differ')
    changes=[]
    for n,(x,y) in enumerate(zip(a,z)):
        label=x.group(1);old=y.group(1)
        if not LABEL.fullmatch(label):continue
        projected=CYR.get(label[0],label[0])+label[1:]
        if old not in {label,projected}:raise ValueError(f'Unexpected label at ordinal {n}: {old!r}')
        if old!=label:changes.append(dict(ordinal=n,start=y.start(1),end=y.end(1),before=old,after=label,latin_start=x.start(1)))
    for x in reversed(changes):cyrillic=cyrillic[:x['start']]+x['after']+cyrillic[x['end']:]
    for rule,pattern in RULES.items():
        a=list(pattern.finditer(latin));z=list(pattern.finditer(cyrillic))
        if len(a)!=len(z):raise ValueError(f'{rule}: corresponding inventories differ')
        extra=[]
        for n,(x,y) in enumerate(zip(a,z)):
            expected=x.group(1);actual=y.group(1)
            if expected==actual:continue
            if CYR.get(expected)!=actual:raise ValueError(f'{rule}: unexpected letter pair {expected!r}/{actual!r}')
            # All replacements preserve character length, so recorded offsets
            # remain valid across these successive, nonoverlapping stages.
            extra.append(dict(rule=rule,ordinal=n,start=y.start(1),end=y.end(1),before=actual,after=expected,latin_start=x.start(1),
                              latin_context=latin[max(0,x.start()-60):x.end()+70],cyrillic_context=cyrillic[max(0,y.start()-60):y.end()+70]))
        for q in reversed(extra):cyrillic=cyrillic[:q['start']]+q['after']+cyrillic[q['end']:]
        changes.extend(extra)
    return cyrillic,changes

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('latin',type=Path);p.add_argument('cyrillic',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    out,changes=preserve(a.latin.read_text(encoding='utf-8-sig'),a.cyrillic.read_text(encoding='utf-8-sig'))
    if a.output.exists():raise FileExistsError(a.output)
    a.output.write_text(out,encoding='utf-8',newline='\n');print(f'{len(changes)} source identifiers preserved')
