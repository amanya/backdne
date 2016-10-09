# Backend

A simple backend written in Flask and ready to deploy to Heroku.

## How to install

* Install pip: https://pip.pypa.io/en/stable/installing/
* Install virtualenvwrapper: https://virtualenvwrapper.readthedocs.io/en/latest/install.html#basic-installation
* Create a virtualenv to install project dependencies:
```
$ mkvirtualenv backend
```

* Install dependencies
```
(backend) $ pip install -r requirements/dev.txt
```

* Setup database
```
(backend) $ python manage.py deploy
```

* Setup email server. Edit the file `.venv` and fill it with your GMail (or desired SMTP provider) credentials.
* Start application
```
(backend) $ python manage.py runserver
```

## Procedures

## Create fake data
```
(backend) $ python manage.py shell
>>> User.generate_fake()
>>> School.generate_fake()
```

## Use the api

* List all schools
```
(backend) $ curl localhost:5000/api/v1.0/schools/
```
* Get information about a school
```
(backend) $ curl localhost:5000/api/v1.0/schools/1
```
* List students of a school
```
(backend) $ curl localhost:5000/api/v1.0/schools/1/students/
```
* Create a school
```
(backend) $ export AUTH_TOKEN=$(echo -n <EMAIL>:<PASSWORD> | openssl base64)
(backend) $ curl -X POST \
                -d '{"name": "a_school", "description": "hi there"}' \
                -H "Authorization: Basic $AUTH_TOKEN" \
                -H "Accept: application/json" \
                -H "Content-Type: application/json" \
                http://127.0.0.1:5000/api/v1.0/schools/
```
