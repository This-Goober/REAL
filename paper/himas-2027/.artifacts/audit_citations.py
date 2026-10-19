"""Fail the paper build for missing/unused references or unkeyed author-year cites."""
import json
from pathlib import Path
import re
import subprocess

HERE=Path(__file__).resolve().parent

def run():
    refs=json.loads(subprocess.check_output(['pandoc','references.bib','-f','biblatex','-t','csljson'],cwd=HERE.parent,text=True))
    ids=[r['id'] for r in refs]
    assert len(ids)==len(set(ids)), 'duplicate bibliography keys'
    occurrences={k:[] for k in ids};unresolved=[];unkeyed=[]
    for p in sorted(HERE.parent.glob('0[1-7]-*.md')):
        text=p.read_text()
        ast=json.loads(subprocess.check_output(['pandoc','-f','markdown','-t','json'],input=text,text=True))
        def walk(node):
            if isinstance(node,dict):
                if node.get('t')=='Cite':
                    for c in node['c'][0]:
                        key=c['citationId']
                        if key not in occurrences: unresolved.append(key)
                        else:occurrences[key].append(p.name)
                for v in node.values():walk(v)
            elif isinstance(node,list):
                for v in node:walk(v)
        walk(ast)
        unkeyed += [(p.name,m.group(0)) for m in re.finditer(r'\([A-Z][^()\n]{0,90},\s*(?:19|20)\d{2}\)',text)]
    unused=[k for k,v in occurrences.items() if not v]
    report={'bibliography_entries':len(ids),'citation_occurrences':sum(map(len,occurrences.values())),
            'missing_keys':unresolved,'uncited_references':unused,'unkeyed_author_year':unkeyed,
            'occurrences':occurrences}
    (HERE/'citation-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    assert not unresolved and not unused and not unkeyed,report
    print(f"Citations: {len(ids)} entries, {report['citation_occurrences']} uses; no missing keys or uncited references.")

if __name__=='__main__':run()
