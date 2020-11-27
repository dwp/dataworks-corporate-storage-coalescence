SHELL:=bash

default: help

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: bootstrap
bootstrap: ## Bootstrap local environment for first use
	@make git-hooks

.PHONY: git-hooks
git-hooks: ## Set up hooks in .githooks
	@git submodule update --init .githooks ; \
	git config core.hooksPath .githooks \


localstack: ## bring up localstack container and wait for it to be ready
	docker-compose up -d localstack
	@{ \
			while ! docker logs localstack 2> /dev/null | grep -q "^Ready\." ; do \
					echo Waiting for localstack.; \
					sleep 2; \
			done; \
	}
	docker-compose up localstack-init

services: localstack

.PHONY: coalescer
coalescer:
	docker-compose up coalescer

unit-tests:
	tox tests/*.py

integration-tests: services coalescer
	docker-compose up integration-tests

tests: unit-tests integration-tests

s3-clear:
	awslocal s3 rm --recursive s3://corporate-data

s3-list:
	awslocal s3 ls --recursive s3://corporate-data
