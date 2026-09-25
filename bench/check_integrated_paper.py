"""Verify that integration retains the prior document's evidence and full proofs.

This is an offline preservation check against the archived v1.2.0 sources. It
does not rerun experiments or compile the abstract Lean model.
"""
import hashlib
import json
import re
import tarfile

from check_document_provenance import ROOT, PDF, digest, source_hashes


def main():
    revision=ROOT/'revisions/20260925-integrated'
    baseline=json.loads((revision/'baseline.json').read_text())
    for name,expected in baseline['protected_sha256'].items():
        assert digest(ROOT/name)==expected, ('Protected evidence changed',name)
    with tarfile.open(revision/'previous-v1.2.0-document.tar.gz') as archive:
        old={name:archive.extractfile(name).read() for name in baseline['previous_document_sha256']}
    for name,expected in baseline['previous_document_sha256'].items():
        assert hashlib.sha256(old[name]).hexdigest()==expected, ('Historical document changed',name)
    old_inputs=json.loads(old['data/derived/build-receipt.json'])['source_sha256']
    retained_generated={name:expected for name,expected in old_inputs.items()
                        if name.startswith(('paper/figures/','data/derived/'))}
    for name,expected in retained_generated.items():
        assert digest(ROOT/name)==expected, ('Prior figure or numerical table changed',name)
    old_model=old['paper/supplement-model.tex'].decode()
    model=(ROOT/'paper/appendix-proofs.tex').read_text()
    # Only the redundant section heading was removed from this entire source.
    assert model.strip()==old_model.split('\n',1)[1].strip()
    pattern=r'\\begin\{(theorem|proposition|corollary|definition|proof)\}.*?\\end\{\1\}'
    prior_statements=[m.group(0) for m in re.finditer(pattern,old_model,re.S)]
    current_statements=[m.group(0) for m in re.finditer(pattern,model,re.S)]
    assert prior_statements==current_statements and len(prior_statements)==13
    supp=old['paper/supplement.tex'].decode()
    history=supp[supp.index('\\section{Original statistical method'):supp.index('\\section{Complete original concurrency matrix}')]
    history=history.replace('\\subsection{','\\subsubsection{').replace('\\section{','\\subsection{')
    history=history.replace('\\label{sec:method}','\\label{app:history-method}').replace('\\label{sec:results}','\\label{app:history-results}')
    history=history.replace('(the serial table below)','(Appendix~\\ref{app:serial})')
    assert history.strip()==(ROOT/'paper/appendix-history.tex').read_text().strip()
    waits=supp[supp.index('\\section{Client waits and observation conventions}'):supp.index('\\section{Follow-up condition summaries}')]
    assert waits.split('\n',1)[1].strip()==(ROOT/'paper/appendix-client-waits.tex').read_text().strip()
    previous_followup=supp[supp.index('\\section{Follow-up condition summaries}'):].split('\n',1)[1].split('\\begingroup\\raggedright\n\\bibliographystyle')[0]
    previous_followup=previous_followup.replace('The main article presents synchronization diagnostics.',
        'Section~\\ref{sec:followup-diagnostics} presents synchronization diagnostics.')
    current_followup=(ROOT/'paper/appendix-followup.tex').read_text().replace('\\label{app:followup-failures}','')
    paragraphs=[p.strip() for p in previous_followup.strip().split('\n\n') if p.strip()]
    # Additions may intervene, but no historical paragraph or table may vanish.
    position=0
    for paragraph in paragraphs:
        found=current_followup.find(paragraph,position)
        assert found>=0, ('Prior follow-up paragraph missing or reordered',paragraph[:120])
        position=found+len(paragraph)
    sources={p.name:p.read_text() for p in (ROOT/'paper').glob('*.tex')}
    all_source='\n'.join(sources.values())
    prior_inputs=re.findall(r'\\(?:input|includegraphics)(?:\[[^\]]*\])?\{([^}]+)\}',supp)
    evidence_inputs=[n for n in prior_inputs if n.startswith('../data/derived/') or n.startswith('figures/')]
    current_inputs=re.findall(r'\\(?:input|includegraphics)(?:\[[^\]]*\])?\{([^}]+)\}',all_source)
    assert set(evidence_inputs)<=set(current_inputs)
    for name in current_inputs:
        path=ROOT/'paper'/name
        assert path.is_file() or path.with_suffix('.tex').is_file(), ('Missing included source',name)
    labels=re.findall(r'\\label\{([^}]+)\}',all_source)
    assert len(labels)==len(set(labels)), 'Duplicate labels after document integration'
    assert not list((ROOT/'paper').glob('supplement*'))
    assert list(PDF.parent.glob('*.pdf'))==[PDF]
    result={'status':'pass','archived_document_files_checked':len(old),
            'protected_evidence_identities_checked':len(baseline['protected_sha256']),
            'hand_statement_and_proof_environments_preserved':len(prior_statements),
            'original_history_and_client_wait_text_preserved':True,
            'prior_followup_paragraphs_preserved':len(paragraphs),
            'prior_figure_and_numerical_table_identities_checked':len(retained_generated),
            'prior_table_and_figure_inputs_preserved':sorted(set(evidence_inputs)),
            'unique_source_labels':len(labels),'current_article_count':1,
            'pdf_sha256':digest(PDF),'source_sha256':source_hashes(),
            'scope':'Document and evidence preservation; no new experiment or proof compilation.'}
    (revision/'integration-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_sha256','prior_table_and_figure_inputs_preserved')},indent=2))


if __name__=='__main__':main()
