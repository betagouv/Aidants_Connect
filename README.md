# Aidants Connect

[![CircleCI](https://circleci.com/gh/betagouv/Aidants_Connect/tree/master.svg?style=svg)](https://circleci.com/gh/betagouv/Aidants_Connect/tree/master)

Aidants Connect est une application web qui propose à des aidants les fonctionnalités suivantes :
- créer un mandat de connexion via FranceConnect avec un ou plusieurs usagers sur un périmètre et une durée définis ;
- connecter via FranceConnect un usager dans les conditions des mandats créés ;
- accéder à des ressources sur l'accompagnement des usagers ;
- accéder à un suivi de ses mandats.

## Pile technique

- Python 3.7
- Django 2.2
- PostgreSQL

## Comment installer la base de données (pour Mac OSX)

Utiliser votre gestionnaire de paquet préféré pour installer la base.
L'exemple qui suit emploie le gestionnaire [Homebrew](https://brew.sh) via la commande `brew`.

Dans un terminal, installer [PostgreSQL](https://www.postgresql.org) :

```sh
brew install postgresql
```

Démarrer le service postgres :

```sh
brew services start postgresql
```

> Ceci démarre le serveur de la base de données postgres et active sa réexécution au login.

Dans le cas où ce serait votre première utilisation de postgreSQL, créer une base d'essai à votre nom :

```sh
createdb `whoami`
```

Puis, démarrer l'invite de commande postgreSQL :

```sh
psql
```

Vous pouvez dès à présent visualiser :
* la liste des bases de données existantes avec cette commande postgreSQL `\list`
* la liste des roles existants avec `\du`

Ajouter une base `aidants_connect` appartenant au nouvel utilisateur `aidants_connect_team` en poursuivant dans l'invite de commmande postgreSQL :

```sql
CREATE USER aidants_connect_team;
CREATE DATABASE aidants_connect OWNER aidants_connect_team;
ALTER USER aidants_connect_team CREATEDB;
```

:tada: La base de donnée `aidants_connect` est installée. Vous pouvez la voir et quitter l'invite de commande avec :

```sql
\list
\q
```

## Installer l'application

Dans votre répertoire de travail, créez et activez un environnement virtuel :

```shell
virtualenv venv
source venv/bin/activate
```

Installer les dépendances :

```shell
pip install -r requirements.txt
```

Si la commande précédente déclenche le message d'erreur suivant `ld: library not found for -lssl`, essayer :

```shell
export LIBRARY_PATH=$LIBRARY_PATH:/usr/local/opt/openssl/lib/
```

Changer le fichier `.env.example` à la racine du projet en `.env` et ajouter vos informations :
- Les champs obligatoires sont indiqués par le préfixe `<insert_`
- Les informations `FC_AS_FS` et `FC_AS_FI` sont à récupérer via des [habilitations FranceConnect](https://franceconnect.gouv.fr/partenaires)
- Les valeur de sécurité sont issues de https://docs.djangoproject.com/fr/2.2/topics/security/ et de https://www.youtube.com/watch?v=gvQW1vVNohg

Créer un répertoire `staticfiles` à la racine du projet :

```shell
mkdir staticfiles
```

Appliquer les migrations de la base de données : 

```shell
python manage.py migrate
```

Créer un `superuser` :

```shell
python manage.py createsuperuser --username <insert_admin_name> 
```

```
python manage.py shell
from aidants_connect_web.models import Aidant, Organisation
a = Aidant.objects.get(pk=1)
a.organisation = Organisation.objects.create(name=<insert_organisation_name>)
exit()
```

### Lancer les tests

Si vous ne les avez pas, installer les éléments suivants :
- Navigateur Firefox en [téléchargement](https://www.mozilla.org/fr/firefox/download/thanks/)
- [Gecko driver](https://github.com/mozilla/geckodriver/releases) avec cette commande :
    ```shell
    brew install geckodriver
    ```

Puis lancer les commandes suivantes pour vérifier le style du code source et exécuter les tests de l'application :

```shell
flake8
python manage.py test
```

Les tests fonctionnels sont lancés sur `http://localhost:3000`.
Il faut s'assurer que rien d'autre n'occupe ce port pendant leur exécution.

## Lancer l'application

Pour lancer l'application sur le port `3000` :

```shell
python manage.py runserver 3000
```

## Annexes

### Documentation de FranceConnect

- Fournisseur d'Identité (FI): [ici](https://partenaires.franceconnect.gouv.fr/fcp/fournisseur-identite)
- Fournisseur de Service (FS): [ici](https://partenaires.franceconnect.gouv.fr/fcp/fournisseur-service)

### Ré-initialiser la base de données

Récupérez les données :

```shell
python manage.py dumpdata --exclude auth.permission --exclude contenttypes > db.json
```

Dans le shell :

```shell
psql
```

Puis, dans l'invite de commande psql :

```sql
DROP DATABASE aidants_connect;
CREATE DATABASE aidants_connect OWNER aidants_connect_team;
ALTER USER aidants_connect_team CREATEDB;
\q
```

Ensuite, de retour dans le shell :

```shell
python manage.py makemigrations
python manage.py migrate
```

Chargez les données :

```shell
python manage.py loaddata db.json
```
ou 
```shell
python manage.py createsuperuser
```
