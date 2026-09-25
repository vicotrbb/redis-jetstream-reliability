PYTHON ?= .venv/bin/python
.PHONY: analyze analyze-followup paper verify experiment collect clean-homelab checksums verify-revision validate-homelab release

analyze:
	$(PYTHON) bench/analyze.py

analyze-followup:
	$(PYTHON) bench/followup/analyze.py
	$(PYTHON) bench/followup/report.py

paper:
	$(PYTHON) bench/build_paper.py

verify:
	$(PYTHON) bench/analyze.py
	$(PYTHON) bench/check_paper.py

checksums:
	$(PYTHON) bench/checksums.py

release: verify-revision
	$(PYTHON) bench/package_release.py

experiment:
	python3 bench/run_homelab.py run --campaign "$(CAMPAIGN)" --attempt "$(ATTEMPT)"

collect:
	python3 bench/run_homelab.py collect --campaign "$(CAMPAIGN)" --attempt "$(ATTEMPT)"

clean-homelab:
	python3 bench/run_homelab.py cleanup --campaign "$(CAMPAIGN)" --attempt "$(ATTEMPT)"

validate-homelab:
	python3 bench/run_homelab.py validation --campaign "$(CAMPAIGN)" --attempt "$(ATTEMPT)"

verify-revision:
	$(PYTHON) bench/check_paper.py
	$(PYTHON) bench/check_revision.py
	$(PYTHON) bench/check_followup.py
	$(PYTHON) bench/check_manuscript_numbers.py
	$(PYTHON) bench/check_document_provenance.py
