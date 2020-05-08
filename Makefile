.PHONY: test
TEST_DB_NAME ?= mroll_test_db

test:
	poetry run python -m unittest