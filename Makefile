destroy-rebuild-dev-db:
	psql -c 'DROP DATABASE aidants_connect;'
	psql -c 'CREATE DATABASE aidants_connect OWNER aidants_connect_team;'
	psql -c 'ALTER USER aidants_connect_team CREATEDB;'
	python manage.py migrate
	python manage.py loaddata admin.json
	python manage.py loaddata usager_autorisation.json
