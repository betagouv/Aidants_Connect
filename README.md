# Aidants Connect

Aidants Connect is an app that allows people who want to assist FranceConnect users to do so with full transparency.

[![CircleCI](https://circleci.com/gh/betagouv/Aidants_Connect/tree/master.svg?style=svg)](https://circleci.com/gh/betagouv/Aidants_Connect/tree/master)

## Stack
Django
PostgreSQL

## Environment
AidantConnect runs on Python 3.7

# How to setup the Database

Install PostgreSQL (for Mac OSX)
```
brew install postgresql
brew services start postgresql
createdb `whoami`
```

Create the database
```
psql
```
In the postgreSQL prompt
``` 
CREATE USER aidants_connect_team;
CREATE DATABASE aidants_connect OWNER aidants_connect_team;
ALTER USER aidants_connect_team CREATEDB;
\q
```

## How to install the app

Use a virtual environment in your working directory

```
virtualenv venv
source venv/bin/activate
```

Install the dependencies

```
pip install -r requirements.txt
```

If you get `ld: library not found for -lssl` as an error message, try:
```
export LIBRARY_PATH=$LIBRARY_PATH:/usr/local/opt/openssl/lib/
```

Create a `.env` file at the root of the project
 
Add the following entries to the `.env` file:
```
HOST= <insert_your_data> #e.g. http://localhost:8000
APP_SECRET=<insert_your_secret>
TEST="Everything is awesome"

DATABASE_NAME=aidants_connect
DATABASE_USER=aidants_connect_team
DATABASE_PASSWORD='' or <insert_your_data>
DATABASE_URL='' or <insert_your_data>
DATABASE_PORT='' or <insert_your_data>

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

Create a `staticfiles` directory
```
mkdir staticfiles
```

Run the migrations
```
python manage.py migrate
```

Create a superuser
```
python manage.py createsuperuser --username <insert_admin_name> 
```

## How to run the tests
Install [Firefox](https://www.mozilla.org/fr/firefox/download/thanks/)

Install [Gecko driver](https://github.com/mozilla/geckodriver/releases)

```
brew install geckodriver
```
Then run:

```
flake8
python manage.py test
```

The functional test run on `http://localhost:3000`
Make sure nothing else is running on that port.

## How to run the app

To run the app on port 3000
```
python manage.py runserver 3000
```

## FranceConnect FI documentation
[here](https://partenaires.franceconnect.gouv.fr/fcp/fournisseur-identite)

## Database from scratch
```
psql
```
then
```
DROP DATABASE aidants_connect;
CREATE DATABASE aidants_connect OWNER aidants_connect_team;
ALTER USER aidants_connect_team CREATEDB;
\q
```
then
```
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

