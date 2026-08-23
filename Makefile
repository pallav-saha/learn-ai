VENV := .venv
PYTHON := $(VENV)/bin/python3

.PHONY: setup delete run

setup:
	uv venv $(VENV)
	uv pip install -r requirements.txt --python $(VENV)/bin/python3

delete:
	rm -rf $(VENV)

# Run any script: make run file=01-llm-basics/llm_basics.py
run:
	$(PYTHON) $(file)
