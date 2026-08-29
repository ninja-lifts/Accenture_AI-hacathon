# One entry point per thing a judge might want to do.
# `make reproduce` is the promise in the README - if it breaks, the submission breaks.

.PHONY: help setup data freeze eval baseline app reproduce test fetch-rs fetch-psqueeze clean

help:
	@echo "setup      - install dependencies"
	@echo "data       - generate the Meridian dataset from the committed manifest"
	@echo "eval       - run the 17-scenario harness, write eval/scorecard.md"
	@echo "baseline   - run B1/B2/B3 baselines, write eval/baseline_scorecard.md"
	@echo "app        - launch the UI locally"
	@echo "test       - unit tests"
	@echo "reproduce  - setup + data + eval + test. The single command in the README."
	@echo "fetch-rs   - clone RiskLoc for the external benchmark (not committed)"

setup:
	python -m pip install -r requirements.txt

data:
	python data/generate.py --seed 20260829 --out data/generated

eval:
	python -m eval.harness --scenarios all --out eval/scorecard.md

baseline:
	python -m eval.harness --baseline --out eval/baseline_scorecard.md

app:
	streamlit run app/main.py

test:
	pytest -q

reproduce: setup data eval test
	@echo ""
	@echo "Done. Scorecard: eval/scorecard.md"

fetch-rs:
	@mkdir -p data/external
	git clone --depth 1 https://github.com/shaido987/riskloc data/external/riskloc

fetch-psqueeze:
	@echo "Download Zenodo record 8153849 (CC BY 4.0) into data/external/psqueeze/"

clean:
	rm -rf data/generated runs .pytest_cache
