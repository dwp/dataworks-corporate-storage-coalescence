SHELL:=bash

aws_profile=default
aws_region=eu-west-2

default: help

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: bootstrap
bootstrap: ## Bootstrap local environment for first use
	@make git-hooks
	pip3 install --user Jinja2 PyYAML boto3
	@{ \
		export AWS_PROFILE=$(aws_profile); \
		export AWS_REGION=$(aws_region); \
		python3 bootstrap_terraform.py; \
	}
	terraform fmt -recursive

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
	tox -c tests/*.py

integration-tests: services coalescer
	docker-compose up integration-tests

tests: unit-tests integration-tests

s3-clear-manifest:
	awslocal s3 rm --recursive s3://manifest-data

s3-clear-corporate:
	awslocal s3 rm --recursive s3://corporate-data

s3-clear: s3-clear-manifest s3-clear-corporate

repopulate: s3-clear
	@{ \
		cd containers/localstack; \
		./run.sh; \
	}

s3-list:
	awslocal s3 ls --recursive s3://corporate-data

clean:
	rm -rf dist build coalescer/dataworks_corporate_data_coalescence.egg-info .tox
	find . -type d -name __pycache__ | xargs -r rm -vrf


.PHONY: terraform-workspace-new
terraform-workspace-new: ## Creates new Terraform workspace with Concourse remote execution
	declare -a workspace=( management ) \
	make bootstrap ; \
	cp terraform.tf workspaces.tf && \
	for i in "$${workspace[@]}" ; do \
		fly -t aws-concourse execute --config create-workspace.yml --input repo=. -v workspace="$$i" ; \
	done
	rm workspaces.tf

.PHONY: concourse-login
concourse-login: ## Login to concourse using Fly
	fly -t aws-concourse login -c https://ci.dataworks.dwp.gov.uk/ -n dataworks

.PHONY: utility-login
utility-login: ## Login to utility team using Fly
	fly -t utility login -c https://ci.dataworks.dwp.gov.uk/ -n utility

.PHONY: update-pipeline
update-pipeline: ## Update the main pipeline
	aviator

.PHONY: update-corporate-storage-coalescer-pipeline
update-corporate-storage-coalescer-pipeline: ## Update the corporate-storage-coalescer pipeline
	aviator -f aviator-corporate-storage-coalescer.yml
