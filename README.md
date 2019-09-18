# Aidants Connect
[![CircleCI](https://circleci.com/gh/betagouv/Aidants_Connect/tree/master.svg?style=svg)](https://circleci.com/gh/betagouv/Aidants_Connect/tree/master)

Aidants Connect est une application web qui propose à des aidants les fonctionnalités suivantes :
- créer un mandat de connexion via FranceConnect avec un ou plusieurs usagers sur un périmètre et une durée définis ;
- connecter via FranceConnect un usager dans les conditions des mandats créés ;
- accéder à des ressources sur l'accompagnement des usagers ;
- accéder à un suivi de ses mandats.

### Pile technique
- Python 3.7
- Django 2.2
- PostgreSQL

## Comment installer la base de données (pour Mac OSX)

Installer PostgreSQL
```sh
brew install postgresql
brew services start postgresql
createdb `whoami`
```

Créer la base de données
```sh
psql
```

Dans l'invite de commmande postgreSQL :
```
CREATE USER aidants_connect_team;
CREATE DATABASE aidants_connect OWNER aidants_connect_team;
ALTER USER aidants_connect_team CREATEDB;
\q
```

## Installer l'application

Dans votre répertoire de travail, créez et activez un environnement virtuel
```
virtualenv venv
source venv/bin/activate
```

Installer les dépendances

```
pip install -r requirements.txt
```

Si la commande précédente déclenche le message d'erreur suivant `ld: library not found for -lssl`, essayer :
```
export LIBRARY_PATH=$LIBRARY_PATH:/usr/local/opt/openssl/lib/
```

Créer un fichier `.env` à la racine de votre projet et y ajouter les éléments suivants :
 

```
HOST= <insert_your_data> #e.g. http://localhost:8000
APP_SECRET=<insert_your_secret>
TEST="Everything is awesome"

DATABASE_NAME=aidants_connect
DATABASE_USER=aidants_connect_team
DATABASE_PASSWORD='' or <insert_your_data>
DATABASE_URL='' or <insert_your_data>
DATABASE_PORT='' or <insert_your_data>
# Can be replaced by a POSTGRES_URL (from https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING)

FC_AS_FS_BASE_URL=<insert_your_data>
FC_AS_FS_ID=<insert_your_data>
FC_AS_FS_SECRET=<insert_your_data>
FC_AS_FS_CALLBACK_URL=<insert_your_data>
FC_AS_FS_TEST_PORT=<insert_your_data> or ''

FC_AS_FI_ID=<insert_your_data>
FC_AS_FI_SECRET=<insert_your_data>
FC_AS_FI_CALLBACK_URL=<insert_your_data>

# Optional
DATABASE_SSL
DEBUG
```

Créer un repertoire `staticfiles` 
```
mkdir staticfiles
```

Appliquer les migrations de la base de données
```
python manage.py migrate
```

Créer un `superuser`
```
python manage.py createsuperuser --username <insert_admin_name> 
```

### Lancer les tests
Installer les éléments suivants :
- [Firefox](https://www.mozilla.org/fr/firefox/download/thanks/)
- [Gecko driver](https://github.com/mozilla/geckodriver/releases)

```
brew install geckodriver
```
puis lancer les commandes suivantes :

```
flake8
python manage.py test
```

Les tests fonctionnels sont lancés sur `http://localhost:3000`.
Il faut s'assurer que rien d'autre n'occupe ce port pendant les tests.

## Lancer l'application

Pour lancer l'application sur le port 3000 :
```
python manage.py runserver 3000
```

## Annexes
### Documentation de FranceConnect FI 
[here](https://partenaires.franceconnect.gouv.fr/fcp/fournisseur-identite)

### Ré-initialiser la base de données

Dans le shell
```
psql
```
puis, dans l'invite de commande psql
```
DROP DATABASE aidants_connect;
CREATE DATABASE aidants_connect OWNER aidants_connect_team;
ALTER USER aidants_connect_team CREATEDB;
\q
```

puis dans le shell
```
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

