#!make
include .env
export $(shell sed 's/=.*//' .env)
PROJECT = "../QCStrat"
print-env: ## Print the environment variables
	@echo $(QC_USERID)
	@echo $(QC_API_KEY)
	@echo $(STRATEGY)

##@ Lean
.PHONY: lean-init
lean-init:: ## login to the lean server and initialize lean, you need to do this only once
	poetry run lean login -u $(QC_USERID) -t $(QC_API_KEY)
	poetry run lean whoami
	poetry run lean init

.PHONY: login
login: ## login to the lean server
	poetry run lean login -u $(QC_USERID) -t $(QC_API_KEY)
	poetry run lean whoami

.PHONY: debug-backtest
debug-backtest: ## Debug Local backtest
	poetry run lean backtest $(PROJECT) --debug pycharm