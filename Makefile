.PHONY: test
TEST_DB_NAME ?= mroll_test_db
target ?= tests
test:
	poetry run python -m unittest ${target}