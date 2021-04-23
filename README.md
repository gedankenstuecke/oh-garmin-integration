# Garmin Health API integration

## Setup local environment

1. Create an OAuth2 project in Open Humans for this app at `https://www.openhumans.org/direct-sharing/oauth2-setup/`. Set `REDIRECT_URL`: `http://127.0.0.1:5000/`.

2. Copy `env.example` to `.env`. Edit `CLIENT_ID` and `CLIENT_SECRET` using the values provided in the information page for this project you just created on Open Humans website

3. Install Heroku's command line client: `https://devcenter.heroku.com/categories/command-line`

5. Install dependencies and migrate the database:

```
pipenv install 
pipenv run python manage.py migrate 
pipenv run python manage.py collectstatic
```

6. Run `heroku local`

7. Change the code and commit the changes to git.

8. Push the changes to production: `git push heroku master`.

7. Optionally: Test the synchronisation of Garmin data to our endpoints locally. Careful! This will break the synchronisation of data on production.

   a. Forward your port, e.g. `ssh -R 5000:localhost:5000 MY_SERVER`. You will have to configure your web server to forward the request to the correct port. For example, in nginx you would add the
   configuration:

   ```
   location /garmin-endpoint/ {
       proxy_pass http://localhost:5000;
   }
   ```

   b. Test the connection:

   ```
   curl -v https://MY_SERVER/garmin-endpoint/dailies/ --data '{"dailies":[]}'
   ```

   c. Configure the endpoints at `https://apis.garmin.com/tools/login`.