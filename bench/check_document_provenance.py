"""Reject historical or stale visual QA for the current document and source."""
import hashlib
import json
import re
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
PDF=ROOT/'output/pdf/redis-jetstream-reliability.pdf'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    paths=[*(ROOT/'paper').glob('*.tex'),*(ROOT/'paper').glob('*.bib'),
           *(ROOT/'paper/figures').glob('*.pdf'),*(ROOT/'data/derived').glob('*.tex')]
    return {str(p.relative_to(ROOT)):digest(p) for p in sorted(paths)}


def validate_review(review,pdf=PDF):
    if review.get('pdf_sha256')!=digest(pdf):
        raise ValueError('Visual-review receipt identifies a different PDF')
    if review.get('source_sha256')!=source_hashes():
        raise ValueError('Document inputs changed after visual review')
    pages=list(range(1,len(PdfReader(pdf).pages)+1))
    if review.get('page_count')!=len(pages) or review.get('pages_rendered')!=pages or review.get('pages_visually_inspected')!=pages:
        raise ValueError('Incomplete current-document page review')
    if review.get('remaining_visual_defects')!=[] or review.get('status')!='pass':
        raise ValueError('Unresolved document QA')
    renders=review.get('rendered_page_sha256',{})
    if len(renders)!=len(pages):
        raise ValueError('Missing retained page renderings')
    for name,expected in renders.items():
        path=ROOT/name
        if not path.is_file() or digest(path)!=expected:
            raise ValueError(f'Rendered review evidence changed: {name}')


def main():
    review=json.loads((ROOT/'data/derived/visual-review.json').read_text())
    validate_review(review)
    check=json.loads((ROOT/'data/derived/paper-check.json').read_text())
    assert check['pdf_sha256']==review['pdf_sha256']
    assert check['source_sha256']==review['source_sha256']
    assert check['pages']==review['page_count']
    assert check['reference_count']==review['reference_count']
    rejected={}
    for name in ('revisions/20260924-final/historical-visual-review.json',
                 'revisions/20260924-submission/historical-visual-review.json',
                 'revisions/20260924-followup/historical-visual-review.json',
                 'revisions/20260925-integrated/historical-visual-review.json'):
        previous=json.loads((ROOT/name).read_text())
        try:
            validate_review(previous)
        except ValueError as error:
            rejected[name]=str(error)
        else:
            raise AssertionError('Historical visual review was accepted for the current PDF')
    for name in ('EXECUTION_RECEIPT.md','REVISION_VALIDATION.md'):
        doc=(ROOT/'docs'/name).read_text()
        assert 'Historical' in doc.splitlines()[0]
        assert 'FINAL_REVISION_VALIDATION.md' in doc
    readme=(ROOT/'README.md').read_text()
    assert 'current validation record is `docs/FINAL_REVISION_VALIDATION.md`' in readme
    narrative=(ROOT/'docs/FINAL_REVISION_VALIDATION.md').read_text()
    counts=re.search(r'\*\*(\d+) pages and (\d+) cited references\*\*',narrative)
    assert counts and tuple(map(int,counts.groups()))==(review['page_count'],review['reference_count']),'Current validation narrative has stale document counts'
    result={'status':'pass','pdf_sha256':digest(PDF),'pages':review['page_count'],
            'source_inputs_checked':len(review['source_sha256']),
            'rendered_pages_checked':len(review['rendered_page_sha256']),
            'historical_review_rejected':True,'historical_reviews_rejected':rejected}
    (ROOT/'revisions/20260925-integrated/document-provenance-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
