"""Check that rendered HTML/PDF citations link to the numbered references.

Requires Pandoc output from build.py and Poppler's pdftohtml. This checks link
integrity, not whether a paper supports the scientific claim citing it.
"""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent


class HTMLReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = set()
        self.links = []
        self.active = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id', '').startswith('ref-'):
            self.targets.add(attrs['id'])
        if tag == 'a' and attrs.get('role') == 'doc-biblioref':
            self.active = [attrs['href'].lstrip('#'), '']

    def handle_data(self, data):
        if self.active is not None:
            self.active[1] += data

    def handle_endtag(self, tag):
        if tag == 'a' and self.active is not None:
            self.links.append(self.active)
            self.active = None


def main():
    audit = json.loads((HERE / 'citation-audit.json').read_text())
    html = HTMLReferences()
    html.feed((HERE / 'REAL-HIMAS-2027.html').read_text())
    expected = {'ref-' + key for key in audit['occurrences']}
    assert html.targets == expected
    assert {key for key, _ in html.links} == expected
    assert len(html.links) == audit['citation_occurrences']
    numbers = {key.removeprefix('ref-'): int(n) for key, n in html.links}
    assert set(numbers.values()) == set(range(1, len(expected) + 1))
    pdf = HERE.parent / 'REAL-HIMAS-2027.pdf'
    with tempfile.TemporaryDirectory() as tmp:
        xml = Path(tmp) / 'links.xml'
        subprocess.run(['pdftohtml', '-xml', '-hidden', '-i', str(pdf), str(xml)],
                       check=True, capture_output=True)
        tree = ET.parse(xml)
    reference_pages = {}
    links = []
    for page in tree.findall('page'):
        page_n = int(page.attrib['number'])
        for block in page.findall('text'):
            content = ''.join(block.itertext())
            match = re.match(r'^\[(\d+)\]\s+\S', content)
            if match:
                reference_pages[int(match[1])] = page_n
            for link in block.findall('a'):
                label = ''.join(link.itertext()).strip()
                target = link.attrib.get('href', '')
                if label.isdigit() and re.search(r'\.html#\d+$', target):
                    links.append((int(label), int(target.rsplit('#', 1)[1])))
    assert set(reference_pages) == set(numbers.values()), reference_pages
    assert len(links) == audit['citation_occurrences'], links
    assert all(reference_pages[n] == target for n, target in links), links
    report = dict(
        pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),
        html_sha256=hashlib.sha256((HERE/'REAL-HIMAS-2027.html').read_bytes()).hexdigest(),
        bibliography_entries=len(expected), html_citation_links=len(html.links),
        pdf_citation_links=len(links), all_links_resolve=True,
        citation_numbers=numbers, reference_pages=reference_pages,
        scope='Rendered citation links; scientific support requires source reading.')
    (HERE/'rendered-citation-audit.json').write_text(json.dumps(report, indent=2)+'\n')
    print(f"Rendered citations: {len(links)} PDF and {len(html.links)} HTML links; all resolve.")


if __name__ == '__main__':
    main()
