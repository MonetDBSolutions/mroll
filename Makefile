export DB_FARM ?= $$(pwd)/dbfarm
export TEST_DB_NAME ?= mroll_test_db
export target ?= tests

.PHONY: test
test: clean setup run_test farmdown

.PHONY: run_test
run_test: 
	poetry run python -m unittest ${target}
	@echo done

.PHONY: setup
setup: clean
	@echo creating ${DB_FARM}
	monetdbd create ${DB_FARM}
	monetdbd start ${DB_FARM}
	monetdb create ${TEST_DB_NAME}
	monetdb release ${TEST_DB_NAME}
	@echo done

.PHONY: farmup
farmup:
	(pgrep -ax monetdbd) || { monetdbd start ${DB_FARM}; sleep 3; }


.PHONY: farmdown
farmdown: 
	if [[ -n "$$(pgrep -ax monetdbd)" ]];then\
		if [[ -e "${DB_FARM}/.merovingian_properties" ]];then\
			monetdbd stop ${DB_FARM};\
		fi;\
	fi

.PHONY: clean
clean: farmdown
	if [[ -d ${DB_FARM} ]];then\
		rm -r ${DB_FARM};\
	fi
