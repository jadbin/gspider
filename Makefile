build:
	pip install -e .

test:
	pytest tests

doc:
	@make -C docs html

clean:
	@rm -rf build dist *egg-info
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@make -C docs clean

.PHONY: build test doc clean
