.PHONY: ds dbs dbshell djs mig migrate shell test

shell:
	python manage.py shell_plus
ds: shell
djs: shell

dbshell:
	python manage.py dbshell
dbs: dbshell

test:
	flake8
	python manage.py test

migrate:
	python manage.py makemigrations
	python manage.py migrate
mig: migrate

bash-prod: ## Open a bash shell on the production platform
	scalingo run --region osc-secnum-fr1 --app aidants-connect-prod bash

bash-preprod: ## Open a bash shell on the preproduction platform
	scalingo run --region osc-fr1 --app aidants-connect-preprod bash

bash-inte: ## Open a bash shell on the integration platform
	scalingo run --region osc-fr1 --app aidants-connect-integ bash
bash-integ: bash-inte

ds-prod: ## Open a Django shell on the production platform
	scalingo run --region osc-secnum-fr1 --app aidants-connect-prod python manage.py shell_plus

ds-preprod: ## Open a Django shell on the preproduction platform
	scalingo run --region osc-fr1 --app aidants-connect-preprod python manage.py shell_plus

ds-inte: ## Open a Django shell on the integration platform
	scalingo run --region osc-fr1 --app aidants-connect-integ python manage.py shell_plus
ds-integ: ds-inte
