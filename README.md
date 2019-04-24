# AidantConnect

AidantConnect is an app that allows people who want to assist FranceConnect users to do so with full transparency.

[![CircleCI](https://circleci.com/gh/betagouv/AidantConnect/tree/master.svg?style=svg)](https://circleci.com/gh/betagouv/AidantConnect/tree/master)


## Stack
Django

## Environment
AidantConnect runs on Python 3.7

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

Create a `.env` file at the root of the project with the following entries:
```
HOST= <insert_your_data> #e.g. http://localhost:8000

FC_CALLBACK_URL=<insert_your_data>

TEST="Everything is awesome"
```

Run the migrations
```
python manage.py makemigrations
python manage.py migrate
```

## How to run the tests

```
flake8
python manage.py test
```
## How to run the app

To run the app on port 8000
```
python manage.py runserver 8000
```

## How to run the functional tests
Install [Gecko driver](https://github.com/mozilla/geckodriver/releases)

```
brew install geckodriver
```

## Test FranceConnect credentials
[here](https://github.com/france-connect/identity-provider-example/blob/master/database.csv)
