# AidantConnect

AidantConnect is an app that allows people who want to assist FranceConnect users to do so with full transparency.

## Stack
Django

## How to install the app

Install the dependencies

```
pip install -r requirements.txt
```

Create a `.env` file at the root of the project with the following entries:
```
HOST= <insert_your_data> #e.g. http://localhost:8000

FRANCE_CONNECT_URL=<insert_your_data>
FRANCE_CONNECT_CLIENT_ID=<insert_your_data>
FRANCE_CONNECT_CLIENT_SECRET=<insert_your_data>

TEST="Everything is awesome"
```

## How to run the unit tests

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
```
python functionnal_tests.py 
```
