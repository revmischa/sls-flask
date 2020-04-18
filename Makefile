.PHONY: init init-from-template run hooks seed test check cfn-lint ldb migrate idb flask-deploy-dev deploy-dev

PYTHON=poetry run

init: init-from-template hooks

init-from-template:
	@bash script/initialize_project.sh
	git init
	npm install

run:
	FLASK_ENV=development $(PYTHON) flask run --reload

hooks:
	$(PYTHON) pre-commit install

seed:
	$(PYTHON) flask seed

test:
	$(PYTHON) pytest

check:
	$(PYTHON) flake8
	$(PYTHON) mypy .
	$(PYTHON) bento check
	$(PYTHON) pytest

cfn-lint:
	npm run sls-package
	cfn-lint

# documentation
doc:
	poetry install --extras "doc"
	$(MAKE) -C doc html

# init DB
idb: dropcreatedb migrate seed

dropcreatedb:
	dropdb TEMPLATE --if-exists
	createdb TEMPLATE

migrate:
	flask db upgrade

deploy-dev:
	sls deploy --stage dev
	sls --stage dev invoke -f migrate

seed-dev: deploy-dev
	sls --stage dev invoke -f seed

deploy-prd:
	sls deploy --stage prd
	sls --stage prd invoke -f migrate
