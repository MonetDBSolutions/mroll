.PHONY: test
TEST_DB_NAME ?= mdb_test_db

test:
	poetry run python -m unittest