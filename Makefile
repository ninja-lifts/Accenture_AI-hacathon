# One entry point per thing a judge might want to do.
# `make reproduce` is the promise in the README - if it breaks, the submission breaks.

.PHONY: help setup data freeze eval eval-live baseline app reproduce test fetch-rs fetch-psqueeze clean

help:
	@echo "setup      - install dependencies"
	@echo "data       - generate the Meridian dataset from the committed manifest"
	@echo "eval       - run the 17-scenario harness in REPLAY mode (forced - never billed), write eval/scorecard.md and eval/cost_receipt.md"
	@echo "eval-live  - run the 17-scenario harness against a LIVE key (billed calls) - explicit opt-in only"
	@echo "baseline   - run B1/B2/B3 baselines, write eval/baseline_scorecard.md"
	@echo "app        - launch the UI locally"
	@echo "test       - unit tests"
	@echo "reproduce  - setup + data + eval + test. The single command in the README. Never makes a billed call."
	@echo "fetch-rs   - clone RiskLoc for the external benchmark (not committed)"

setup:
	python -m pip install -r requirements.txt

data:
	python data/generate.py --seed 20260829 --out data/generated

eval:
	GLASSBOX_REPLAY=1 python -m eval.harness --scenarios all --out eval/scorecard.md

# Explicit opt-in, separate from `eval` on purpose - a judge running `make
# reproduce` must never be able to trigger a billed call even with a key
# configured in their .env. GLASSBOX_REPLAY=0 here overrides .env either way,
# so this target really does go live regardless of what's ambient.
eval-live:
	@echo "WARNING: eval-live makes real, billed calls against a live LLM provider - not a replay run."
	@GLASSBOX_REPLAY=0 python -c "from engine import config; s = config.load(); print(f'  provider={s.llm_provider} model={s.llm_model or \"(unset)\"}')"
	@echo "  approximate call count: up to 18 across the 17-scenario harness (1 narration per scenario that reaches answer/abstention, +1 for SC-17's intent parse) - already-cached responses are skipped, not re-billed"
	GLASSBOX_REPLAY=0 python -m eval.harness --scenarios all --out eval/scorecard.md

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
