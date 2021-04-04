# Garmin Health API integration

TODO

* Add mention of installing libmemcached (needed by sherlock)

## Setup

For local development:

1. create an OAuth2 project in Open Humans this app connects to: https://www.openhumans.org/direct-sharing/oauth2-setup/

* `REDIRECT_URL`: `http://127.0.0.1:5000/`

2. copy `env.example` to `.env`

* edit `CLIENT_ID` and `CLIENT_SECRET` using the values provided in the information page for this project you just created on Open Humans website

3. install Heroku's command line client:
   https://devcenter.heroku.com/categories/command-line
   
5. Install dependencies:

pipenv install 
pipenv run python manage.py migrate 
pipenv run python manage.py collectstatic

6. run `heroku local`

7. Forward your port, e.g.

ssh -R 5000:localhost:5000 my_server

You might have to configure your web server to forward the request to the correct port:

```
location /garmin-endpoint/ {
    proxy_pass http://localhost:5000;
}
```

8. Test the connection:

curl -v https://www.bagofwords.be/garmin-endpoint/dailies/ --data '{"dailies":[]}'

9. Other useful commands:

pipenv run python manage.py makemigrations pipenv run python manage.py migrate