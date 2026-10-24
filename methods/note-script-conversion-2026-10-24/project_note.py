"""Short-note script conversion. AI-created: OpenAI Codex, GPT-6 Astra, Ultra, 2026-10-24.
Exact note converter; see the localized README for its limited input domain.
"""
import argparse
import re
from pathlib import Path

def project_note(s):
    """Project only new prose; preserve TeX commands, original title and Roman II."""
    alphabet=dict(zip('abcvdgđeěžzijklmnoprstufhčšyęų','абцвдгђеєжзијклмнопрстуфхчшыѧѫ'))
    alphabet.update({k.upper():v.upper() for k,v in list(alphabet.items())})
    def plain(x):
        for a,b in [('Dž','Дж'),('dž','дж'),('Lj','Љ'),('lj','љ'),('Nj','Њ'),('nj','њ')]:x=x.replace(a,b)
        return ''.join(alphabet.get(c,c) for c in x)
    parts=re.split(r'(\\[A-Za-z]+|Idealtheorie|\bII\b)',s)
    return ''.join(x if i%2 else plain(x) for i,x in enumerate(parts))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    result=project_note(args.source.read_text(encoding='utf-8-sig'))
    with args.output.open('x',encoding='utf-8',newline='') as stream:
        stream.write(result)

if __name__=='__main__':
    main()
