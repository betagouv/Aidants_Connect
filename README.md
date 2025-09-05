# Aidants Connect

[![CircleCI](https://circleci.com/gh/betagouv/Aidants_Connect/tree/main.svg?style=svg)](https://circleci.com/gh/betagouv/Aidants_Connect/tree/main)

Aidants Connect est une application web qui propose à des aidants les fonctionnalités suivantes :

- créer un mandat de connexion via [FranceConnect](https://franceconnect.gouv.fr/) avec un ou plusieurs usagers sur un périmètre et une durée définis ;
- connecter via FranceConnect un usager dans les conditions des mandats créés ;
- accéder à des ressources sur l'accompagnement des usagers ;
- accéder à un suivi de ses mandats.

Aidants Connect est construit sur les éléments suivants :

- Python 3.11
- Django 4.2
- PostgreSQL

## Installer et lancer l'application

Lancement rapide si vous avez déjà installé la base de données et les dépendances de test :

```shell
git clone git@github.com:betagouv/Aidants_Connect.git
cd Aidants_Connect
cp .env.example .env
virtualenv venv
source venv/bin/activate
pip install --user pipenv
pipenv install --dev
python manage.py collectstatic
pre-commit install
```

Ensuite, vous devriez pouvoir faire tourner les tests :

```shell
python manage.py test
```

Et lancer le serveur :

```shell
python manage.py runserver 3000
```

### Installer la base de données

Utilisez votre gestionnaire de paquets préféré pour installer la base.
L'exemple qui suit emploie le gestionnaire [Homebrew](https://brew.sh) via la commande `brew`.

Dans un terminal, installez [PostgreSQL](https://www.postgresql.org) :

```sh
brew install postgresql
```

Démarrez le service postgresql :

```sh
brew services start postgresql
```

Ceci démarre le serveur de la base de données et active sa réexécution au login.

Dans le cas où ce serait votre première utilisation de PostgreSQL, créez une base d'essai à votre nom :

```sh
createdb `whoami`
```

Puis, démarrez l'invite de commande PostgreSQL :

```sh
psql
```

Vous pouvez dès à présent visualiser :

- la liste des bases de données existantes avec cette commande PostgreSQL `\list`
- la liste des rôles existants avec `\du`

Ajoutez une base `aidants_connect` appartenant au nouvel utilisateur `aidants_connect_team` en poursuivant dans l'invite de commmande PostgreSQL :

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

### Installer l'application

Dans votre répertoire de travail, créez et activez un environnement virtuel :

```shell
virtualenv venv
source venv/bin/activate
```

Installez pipenv :

```shell
brew install pipenv  # Sur Mac
# Ou
pip install pipenv
```

Installez les dépendances :

```shell
pipenv install --dev
```

Si vous avez un Mac M1, ou si la commande précédente déclenche le message d'erreur `ld: library not found for -lssl`, référez-vous à la section [Troubleshooting](#troubleshooting).

### Configurer les variables d'environnement

Dupliquez le fichier `.env.example` à la racine du projet en tant que `.env` :

```shell
cp .env.example .env
```

En test en local, vous ne devriez pas avoir à modifier ce `.env`.

Créez un répertoire `staticfiles` à la racine du projet :

```shell
mkdir staticfiles
```

Appliquez les migrations de la base de données :

```shell
python manage.py migrate
```

### Peupler la base de données

Il existe plusieurs moyens de peupler la base de données.

#### Utiliser les _fixtures_

Des données de test qui créent un environnement complet :

```shell
  python manage.py loaddata admin.json
  python manage.py loaddata usager_autorisation.json
  python manage.py loaddata faq.json
  python manage.py loaddata testimonies.json
```

Ce process crée automatiquement un _superuser_ `admin@email.com`. Plus d'information sur comment se connecter avec ce compte sont disponible dans la section [Se connecter à l'application](#se-connecter-à-lapplication)

#### Créer manuellement un _superuser_

Créez un profil administrateur avec une organisation par défaut :

```shell
python manage.py createsuperuser --username <insert_admin_email> --organisation-name <insert_organisation_name>
```

Une organisation avec l'email que vous avez spécifié sera automatiquement créée pour ce profil.
Si vous avez déjà créé une organisation vous pouvez passer son numéro dans la base de donnée à la création du profil
admin :

```shell
python manage.py createsuperuser --username <insert_admin_email> --organisation <insert_organisation_pk>
```

Pour pouvoir vous connecter à votre instance locale, il faut apparier à votre `superuser` un dispositif TOTP (`TOTP device`).

Pour cela, commencez par lui adjoindre un [jeton OTP](https://fr.wikipedia.org/wiki/Mot_de_passe_%C3%A0_usage_unique) [statique](https://django-otp-official.readthedocs.io/en/stable/overview.html#module-django_otp.plugins.otp_static) :

```shell
python manage.py addstatictoken <insert_admin_email> -t <insert_6_numbers>
```

Notez ce code, il vous permettra de vous connecter la première fois à l'interface d'administration.

### Lancer les tests

Si vous ne les avez pas, installez les éléments suivants :

- Navigateur Firefox en [téléchargement](https://www.mozilla.org/fr/firefox/download/thanks/)
- [Gecko driver](https://github.com/mozilla/geckodriver/releases)

Installation de Gecko Driver :

- Mac OS : `brew install geckodriver `
- Linux : vous pouvez télécharger [ici](https://github.com/mozilla/geckodriver/releases) la dernière
  version du driver et déposer le fichier `geckodriver` dans `VOTRE_VENV/bin` (ou dans `/usr/local/bin` si vous voulez
  donner un accès global au driver).

Puis lancez les commandes suivantes pour vérifier le style du code source et exécuter les tests de l'application :

```shell
flake8
black --check .
python manage.py test
```

Les tests fonctionnels (Selenium) sont lancés sur `http://localhost:3000`.
Il faut s'assurer que rien d'autre n'occupe ce port pendant leur exécution.

Par défaut, les tests Selenium sont lancés en mode _headless_, c'est-à-dire sans ouverture de fenêtre de navigateur. Pour modifier ce comportement, inversez la valeur de la variable d'environnement `HEADLESS_FUNCTIONAL_TESTS` dans votre fichier `.env`.

Astuce : la plupart des cas de tests portent une directive `@tag` pour leur associer des tags décrivant des fonctionnalités ou des caractéristiques des tests. Par exemple, `functional` pour les tests fonctionnels, `create_mandat` pour ce qui implique une création de mandat, etc.
Cela vous permet de lancer seulement certains tests, grâce à l'option `--tag`. Par exemple, pour lancer les tests portant le tag `parrot` :

```shell
python manage.py test --tag parrot
```

### Lancer l'application

Pour lancer l'application sur le port `3000` :

```shell
python manage.py runserver 3000
```

L'application sera disponible à l'URL `http://localhost:3000/`.

### Se connecter à l'application

Votre _superuser_ est créé et a un login, un mot de passe et un _static token_ c'est-à-dire un code à 6 chiffres utilisable une seule fois. Il faut maintenant obtenir le QR code qui vous permettra de vous connecter de manière pérenne.

#### Trouver la page d'admin

La page d'admin se trouve sur `/[Variable d'environnement ADMIN_URL]`. En local, `/adm`.

Attention, `/admin` n'est pas un vrai site d'admin… c'est un [pot de miel](https://pypi.org/project/django-admin-honeypot/).

#### Se connecter à l'admin

- ⏩ Si vous avez utilisé les _fixtures_ pour peupler votre base de données,
  - identifiant : `admin@email.com`;
  - mot de passe : `admin`;
  - Static OTP : `111111`
- Sinon, utilisez le login, mot de passe et static token créés dans la section [Installation sur un serveur : Créer un _superuser_](#installation-sur-un-serveur--créer-un-superuser)

#### Pérenniser son authentification à double facteur (2FA)

Une fois connecté à l'admin, cliquez sur **_TOTP devices_**

- ⏩ Si vous avez utilisé les _fixtures_ :
  - Cliquez sur le lien `qr code` à droite de l'entrée pour Admin
  - Scannez le QRcode dans une application TOTP telle que [Authy](https://authy.com/) ou [Google Authenticator](https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2)

Si vous avez créé votre propre _superuser_ :

1. Cliquez sur le bouton `Ajouter TOTP device +`
2. Choisissez votre _superuser_ grâce à l'icône "loupe" située à côté du champ _User_
3. Saisissez un nom pour votre dispositif TOTP (par exemple : _Mon téléphone_) dans le champ `Name`
4. Cliquez ensuite sur _Enregistrer et continuer les modifications_ tout en bas du formulaire
5. Une fois l'enregistrement effectué, l'écran devrait se rafraîchir et vous proposer un lien vers un [QR Code](https://fr.wikipedia.org/wiki/Code_QR)
6. Vous pouvez à présent scanner celui-ci dans une application TOTP telle que [Authy](https://authy.com/) ou [Google Authenticator](https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2) pour utiliser l'authentification à double facteur dans votre environnement local.

## Contribuer à l'application

Il faut d'abord avoir correctement installé l'application.

Installez les _git hooks_ :

```
pre-commit install
```

## Travailler sur le côté client (CSS et JavaScript)

### JS

Le projet utilise massivement [Stimulus](https://stimulus.hotwired.dev/). Avec la réécriture DSFR, le projet adopté
les [modules ES6](https://developer.mozilla.org/fr/docs/Web/JavaScript/Guide/Modules) et les
[importmaps](https://developer.mozilla.org/fr/docs/Web/HTML/Element/script/type/importmap) à l'aide de
[`dj-importmap`](https://github.com/christophehenry/dj-importmap). Les modules Js du projet sont nommés au format
`.mjs`. Autant que possible, le vieux JS du projet est réécrit au fur et à mesure pour utiliser ces bonnes pratiques.

Le projet a aussi profité de la réécriture DSFR pour utiliser [l'API de rendu des formulaires Django](https://docs.djangoproject.com/en/dev/ref/forms/renderers/).
Les bonnes pratiques actuelles du projet sont de rendre les formulaires autonomes grâce à cette API et l'utilisation
des [form assets](https://docs.djangoproject.com/en/5.1/topics/forms/media/).

### CSP et JavaScript inline

La CSP (content security policy) de Aidants Connect fonctionne en liste blanche : elle nécessite de lister tous les scripts inline (dans des balises `<script>`).

Si vous devez modifier ou ajouter un bout de JavaScript inline, vous pouvez [utiliser la propriété `csp_nonce` de l'objet `HttpRequest` générée par `django-csp`](https://django-csp.readthedocs.io/en/3.8/nonce.html#middleware) :

```django
<script nonce="{{request.csp_nonce}}">
    var hello="world";
</script>
```

### CSS et SCSS

Le projet utilise un peu SCSS. Autant que possible, nous tentons d'utiliser du CSS pur et de réduire l'utilisation de
SASS. La réécriture du front avec le DSFR a permis d'en réduire considérablement l'utilisation. La tendance actuelle
est de remplacer les fichiers SCSS précédemment écris par du CSS pur à l'exception de
[`aidants_connect_common/static/scss/main.scss`](./aidants_connect_common/static/scss/main.scss).

Pour compiler les fichiers SCSS en CSS, vous devez avoir installé sass sur votre poste, la commande `sass` doit être disponible dans votre `$PATH`.

Ensuite, utilisez une des deux commandes suivantes :

```
python manage.py scss # compilation one-shot
# ou bien :
python manage.py scss --watch # compilation automatique à chaque modification de SCSS
```

## Installation sur un serveur

### Variables d'environnement

Sur un serveur, vous voudrez ajouter vos informations dans le fichier .env ou dans les variables d'environnement de votre hébergeur :

- Les champs obligatoires sont indiqués par le préfixe `<insert_`.
- Les informations de production `FC_AS_FS` et `FC_AS_FI` sont à récupérer via des [habilitations FranceConnect](https://franceconnect.gouv.fr/partenaires).
- Vous allez devoir calculer la valeur `HASH_FC_AS_FI_SECRET` à partir de la valeur de `FC_AS_FI_SECRET` : pour cela voir dans les annexes [la procédure](#calcul-de-hash_fc_as_fi_secret-à-partir-de-la-valeur-de-fc_as_fi_secret).
- Les valeurs de sécurité sont issues de [la section "sécurité" de la documentation Django](https://docs.djangoproject.com/fr/3.2/topics/security/) et de [la conférence Django and Web Security Headers](https://www.youtube.com/watch?v=gvQW1vVNohg).

### Création d'un superuser sans accès à la console Django

Il existe deux solutions.

### Solution avant installation du code

- déployer la branche de la [PR 473](https://github.com/betagouv/Aidants_Connect/pull/473) avant de déployer main (utilisé pour notre environnement sandbox).
  - avant de déployer le code, insérer les variables d'environnement `INIT_*` mentionnées dans la PR ;
  - installer l'application à partir de la branche de la PR 473 ;
  - déployer ensuite l'application à partir de la branche `main`.

### Solution après installation du code

- insérer directement les données dans la base de données après l'installation de l'application.

## Annexes

### Documentation de FranceConnect

- Fournisseur d'Identité (FI): [ici](https://partenaires.franceconnect.gouv.fr/fcp/fournisseur-identite)
- Fournisseur de Service (FS): [ici](https://partenaires.franceconnect.gouv.fr/fcp/fournisseur-service)

### Ré-initialiser la base de données

#### Avec les données de test (_fixtures_) : Utiliser le Makefile

Pour simplifier le lancement de certaines commandes, un Makefile est disponible. Exemples de commandes :

```shell
make destroy-rebuild-dev-db
```

Sur Windows, la commande `make` n'est pas disponible ;
Il faut passer chaque commande du `Makefile` (fichier présent à la racine du projet) les unes après les autres.

#### Avec des données existantes

Si vous avez des données existantes, vous pouvez d'abord les sauvegarder :

```shell
python manage.py dumpdata --exclude auth.permission --exclude contenttypes > db.json
```

Puis il vous faudra recréer la base de donnée PostgreSQL :

- Dans le shell :

  ```shell
  psql
  ```

- Puis, dans l'invite de commande `psql` :

  ```sql
  DROP DATABASE aidants_connect;
  CREATE DATABASE aidants_connect OWNER aidants_connect_team;
  ALTER USER aidants_connect_team CREATEDB;
  \q
  ```

Ensuite, de retour dans le _shell_, pour lancer les migrations :

```shell
python manage.py migrate
```

Enfin, chargez les données :

- Soit des données sauvegardées précédement :

  ```shell
  python manage.py loaddata db.json
  ```

- Soit repartir de zéro en recréant un _superuser_ (plus de détails dans la section [Installer l'application](#installer-lapplication)) :

  ```shell
  python manage.py createsuperuser
  ```

### Purger les connexions expirées

Les objets Django de type `Connection` repésentent une forme de cache pendant l'établissement de la connexion FranceConnect.
À ce titre, ils contiennent des données personnelles et doivent donc être purgés régulièrement pour respecter nos engagements en la matière.
Pour ce faire, il suffit d'exécuter ou de planifier la commande suivante :

```shell
python manage.py delete_expired_connections
```

### Calcul de `HASH_FC_AS_FI_SECRET` à partir de la valeur de `FC_AS_FI_SECRET`

Il faut utiliser `generate_sha256_hash`.

```python
from aidants_connect_web.utilities import generate_sha256_hash
generate_sha256_hash("VALUE_FC_AS_FI_SECRET".encode("utf-8"))
```

## Troubleshooting

### Erreur `ld: library not found for -lssl`

Si la commande précédente déclenche le message d'erreur suivant `ld: library not found for -lssl`, essayez :

```shell
export LIBRARY_PATH=$LIBRARY_PATH:/usr/local/opt/openssl/lib/
```

### Si vous avez un Mac M1

- Si, lors de l'installation de `psycopg2-binary`, vous avez le message d'erreur suivant :

```
 ld: warning: directory not found for option '-L/usr/bin/openssl/lib/'
    ld: library not found for -lssl
    clang: error: linker command failed with exit code 1 (use -v to see invocation)
    error: command 'clang' failed with exit status 1
```

- Si vous avez installé `openssl` via `brew`, vous pouvez essayer la commande suivante :

```shell
env LDFLAGS='-L/opt/homebrew/opt/openssl@1.1/lib -L/opt/homebrew/opt/readline/lib' pip install -r requirements.txt
```

> https://stackoverflow.com/a/42264168

- Si, lors de l'installation de `pillow` vous avez le message d'erreur suivant :

```shell
The headers or library files could not be found for zlib,
    a required dependency when compiling Pillow from source.

```

Vous pouvez essayer :

```shell
brew install libjpeg
```

> https://github.com/python-pillow/Pillow/issues/5042#issuecomment-746681171

## Les tests fonctionnels échouent de manière inexpliquée

Dans de rares cas (comportement observé à ce jour sur une seule machine de dev), les tests d'intégration échouent car _la première connexion_ à une URL via l'API Selenium plante de manière inexpliquée.

Un contournement empirique a été mis en place ; si vous rencontrez ce problème vous pouvez l'activer en passant à `True` la variable d'environnement `BYPASS_FIRST_LIVESERVER_CONNECTION` dans votre fichier `.env`.
