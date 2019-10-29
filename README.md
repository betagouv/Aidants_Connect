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

Changer le fichier `.env.example` à la racine du projet en `.env` et ajouter vos informations :
- Les informations `FC_AS_FS` et `FC_AS_``I``` sont à récupérer via des habilitations FranceConnect
- Les valeur de sécurité sont issues de https://docs.djangoproject.com/fr/2.2/topics/security/ et de https://www.youtube.com/watch?v=gvQW1vVNohg

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

Récupérez les données
```
python manage.py dumpdata --exclude auth.permission --exclude contenttypes > db.json
```
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
```
Chargez les données
```bash
python manage.py loaddata db.json
```
ou 
```
python manage.py createsuperuser
```

