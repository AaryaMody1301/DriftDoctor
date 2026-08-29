PYTHON ?= python3.13

.PHONY: install test benchmark evaluate preflight verify demo-agent

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py'

benchmark:
	$(PYTHON) scripts/validate_benchmark.py
	$(PYTHON) scripts/smoke_benchmark.py --timeout 90

evaluate:
	$(PYTHON) scripts/run_phase9_primary.py

preflight:
	$(PYTHON) scripts/submission_preflight.py

verify: test benchmark evaluate preflight

demo-agent:
	$(PYTHON) scripts/run_agent_fallback_demo.py --model qwen2.5-coder:1.5b
