"""Build the review manuscript and CEURART source; optionally render with Tectonic."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil
import re
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent          # .artifacts: build inputs, checks, outputs
SRC = HERE.parent                                # the draft: abstract, sections, bibliography, figures, PDF
TITLE = 'REAL: Human-Inspectable Intermediate Representations for AI-Assisted Video Editing'
AUTHORS = 'Anonymous authors'


def convert(text, target):
    return subprocess.check_output(['pandoc', '-f', 'markdown', '-t', target, '--natbib'],
                                   input=text, text=True, cwd=HERE)


def compact_tables(tex):
    """Keep the model comparison together with a caption above the table."""
    caption = ('REAL and direct Claude CLI generation from the same supplied plan '
               '(30 development projects per condition). Temporal F1 measures identity '
               'and boundaries; format pass requires both validators.')
    def replace(match):
        body = match.group(1).replace(r'\begin{longtable}[]', r'\begin{tabular}')
        body = body.replace('\\endhead\n\\bottomrule\\noalign{}\n\\endlastfoot\n', '')
        body = body.replace(r'\end{longtable}', '\\bottomrule\n\\end{tabular}')
        columns = '\n'.join(
            f'  >{{{align}\\arraybackslash}}p{{(\\linewidth - 10\\tabcolsep) * \\real{{{width}}}}}'
            for align, width in [(r'\raggedright', '.22'), (r'\raggedright', '.16'),
                                 (r'\raggedleft', '.14'), (r'\raggedleft', '.16'),
                                 (r'\raggedleft', '.16'), (r'\raggedleft', '.16')])
        replacement = '\\begin{tabular}{@{}\n' + columns + '@{}}\n'
        body, changed = re.subn(r'\\begin\{tabular\}\{.*?(?=\\toprule)',
                                lambda _: replacement, body, count=1, flags=re.S)
        if changed != 1:
            raise ValueError('table column definition not found')
        return ('\\begin{table}[htbp]\n\\centering\n\\caption{' + caption + '}\n\\small\n'
                + body + '\n\\end{table}')
    pattern = r'\{\\def\\LTcaptype\{none\} % do not increment counter\n(.*?\\end\{longtable\})\n\}'
    tex, count = re.subn(pattern, replace, tex, flags=re.S)
    if count != 1:
        raise ValueError('expected one short-paper table; review the table conversion')
    return tex


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tectonic', type=Path)
    a = p.parse_args()
    subprocess.run([sys.executable, str(HERE/'make_results.py')], check=True)
    abstract = (SRC/'abstract.md').read_text().strip()
    sections = sorted(SRC.glob('0[1-7]-*.md'))
    body = '\n\n'.join(s.read_text().strip() for s in sections)
    appendix = (SRC/'08-appendix.md').read_text().strip()
    subprocess.run([sys.executable, str(HERE/'audit_citations.py')], check=True)
    front = (f'# {TITLE}\n\n{AUTHORS}\n\n'
             'HIMAS at IUI Workshops 2027, Helsinki, Finland — submission draft\n\n'
             '## Abstract\n\n'+abstract+'\n\n')
    (HERE/'REAL-HIMAS-2027.md').write_text(front+body+'\n\n# References {.unnumbered}\n\n::: {#refs}\n:::\n\n'
                                           + '# Appendix {.unnumbered}\n\n' + appendix + '\n')
    subprocess.run(['pandoc','REAL-HIMAS-2027.md','-s','--embed-resources',
                    '--citeproc','--bibliography='+str(SRC/'references.bib'),'--csl=numeric.csl',
                    '--resource-path='+str(SRC),
                    '--metadata','link-citations=true',
                    '--metadata','pagetitle='+TITLE,'-o','REAL-HIMAS-2027.html'],cwd=HERE,check=True)
    preamble = r'''% This manuscript is untagged; claim archival PDF/A-1b, not accessible PDF/A-1a.
% pdfx processes declared options in order, with a-1b after the class's a-1a.
\PassOptionsToPackage{a-1b}{pdfx}
\documentclass{ceurart}
\usepackage{longtable}
\usepackage{bookmark}
\providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
\providecommand{\pandocbounded}[1]{#1}
\begin{document}
\copyrightyear{2027}
\conference{IUI Workshops 2027: Joint Proceedings of the ACM Conference on Intelligent User Interfaces Workshops; HIMAS, February 2027, Helsinki, Finland}
\title{REAL: Human-Inspectable Intermediate Representations for AI-Assisted Video Editing}
\author{Anonymous authors}
\begin{abstract}
'''
    tex = preamble + convert(abstract,'latex') + r'''
\end{abstract}
\begin{keywords}
AI-assisted video editing \sep human-AI collaboration \sep intermediate representations \sep multimodal systems \sep local correction
\end{keywords}
\maketitle
''' + convert(body,'latex') + '\n\\emergencystretch=3em\n\\bibliography{references}\n\\end{document}\n'
    # Use vector figures in the print version.
    figures = ['architecture', 'catalogue-path', 'placement-trace']
    for figure in figures:
        tex = tex.replace(figure + '.png', figure + '.pdf')
    tex = tex.replace(r'\begin{figure}', r'\begin{figure}[htbp]')
    tex = compact_tables(tex)
    # Loosen line breaking for the reference list only, so DOI tokens do not overflow.
    tex = tex.replace('\\section*{References}',
                      '\\section*{References}\n\\emergencystretch=3em\n')
    # The technical appendix follows the references, numbered A, A.1, A.2 ...
    # Its tables are long; keep them as longtables, set small.
    appendix_tex = convert(appendix, 'latex')
    appendix_tex = appendix_tex.replace('\\begin{longtable}', '\\begingroup\\small\\begin{longtable}')
    appendix_tex = appendix_tex.replace('\\end{longtable}', '\\end{longtable}\\endgroup')
    appendix_tex = appendix_tex.replace('\\begin{verbatim}', '\\begingroup\\small\\begin{verbatim}')
    appendix_tex = appendix_tex.replace('\\end{verbatim}', '\\end{verbatim}\\endgroup')
    marker = '\\bibliography{references}\n'
    if tex.count(marker) != 1:
        raise ValueError('bibliography marker not found once')
    tex = tex.replace(marker, marker + '\\appendix\n\\emergencystretch=1em\n' + appendix_tex + '\n')
    (HERE/'REAL-HIMAS-2027.tex').write_text(tex)
    # Standalone LaTeX package: no repository-relative files are required.
    with zipfile.ZipFile(HERE/'REAL-HIMAS-2027-source.zip', 'w', zipfile.ZIP_DEFLATED) as package:
        package.writestr('main.tex', tex.replace('../figures/', 'figures/'))
        for name in ['ceurart.cls', 'cc-by.pdf', 'template-provenance.json',
                     'references.bib', 'elsarticle-num-names.bst', 'bibliography-provenance.json']:
            package.write((SRC if name == 'references.bib' else HERE)/name, name)
        for path in sorted(HERE.glob('Copyright*')):
            package.write(path, path.name)
        for figure in figures:
            package.write(SRC/(figure + '.pdf'), figure + '.pdf')
        package.writestr('README.txt',
                         'REAL HIMAS 2027 anonymous review draft. Main file: main.tex.\n'
                         'Compile main.tex with XeLaTeX, then BibTeX main, then XeLaTeX twice.\n'
                         'This package is not a submission. Authors must approve the content,\n'
                         'metadata, and AI declaration and verify final archival requirements.\n')
    if a.tectonic:
        # Compile in a scratch folder holding exactly what the standalone
        # package holds, so the PDF cannot depend on anything else in the tree.
        build = HERE/'build'
        shutil.rmtree(build, ignore_errors=True); build.mkdir()
        for name in ['ceurart.cls', 'cc-by.pdf', 'elsarticle-num-names.bst']:
            shutil.copyfile(HERE/name, build/name)
        shutil.copyfile(SRC/'references.bib', build/'references.bib')
        for figure in figures:
            shutil.copyfile(SRC/(figure + '.pdf'), build/(figure + '.pdf'))
        (build/'REAL-HIMAS-2027.tex').write_text(tex)
        # Tectonic lacks pdfcreationdate; provide the actual UTC creation date
        # in a wrapper, preserving the original CEURART class and paper source.
        stamp=datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
        wrapper=build/'REAL-HIMAS-2027-render.tex'
        wrapper.write_text("\\edef\\pdfcreationdate{\\string D:"+stamp+"+00'00'}\n"
                           "\\input{REAL-HIMAS-2027.tex}\n")
        subprocess.run([str(a.tectonic.resolve()),'--keep-logs',wrapper.name],cwd=build,check=True)
        shutil.copyfile(build/'REAL-HIMAS-2027-render.pdf',SRC/'REAL-HIMAS-2027.pdf')
        subprocess.run([sys.executable,str(HERE/'audit_rendered_citations.py')],check=True)
        subprocess.run([sys.executable,str(HERE/'audit_anonymity.py')],check=True)


if __name__ == '__main__':main()
