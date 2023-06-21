# WPSS

WPSS, a web panel sample service developped in the framework of SSHOC H2020 lead by ESS ERIC.

Disclaimer: Where WPSS name has been chosen by ESS, we initially called our project QxSMS. Any of the acronyms is used. Both are completely equivalent.

## General idea
See ./docs/user for general presentation, user roles and features ([also available online](https://cdsp-scpo.github.io/wpss-doc/)).

## Installation guide

### Qualtrics licence configuration

In order to be able to use all the features, you will need an active Qualtrics licence including:
1. XM Directory with **contact deduplication** activated (deduplication is configured in `Directory settings` -> `Identity resolution` -> `Merge newly added contacts` -> `Merge contacts with uplicate External Data reference`),
1. **API access**
1. Optionally SMS option and SMS credits (no option is necessary to send emails)

Depending on your needs, you can also activate a [data isolation option](https://www.qualtrics.com/support/survey-platform/sp-administration/brand-customization-services/data-isolation).

For a production environment, keep the Qualtrics licence neat and tidy. You will need:

1. To create a **dedicated Qualtrics account** that will be used for the API calls.
1. That **Questionnaires** are **shared** by their owner with this account so they are available in WPSS for distribution.
1. Deciding on a **shared library** accessible to a Qualtrics "message editors group". This will be the library, where messages (and their translations) will be stored.

Fo a testing environment, this setup can be simplified (one user onlycan be used as the Qualtics QxSMS account).

### WPSS development environement

Begin by coupling QxSMS to the (dedicated) Qualtrics account.

Copy the environment file:

```sh
cp .env.template .env
```

This file (ignored by git) has to be edited with your Qualtrics IDs and API key (find them in Qualtrics > Account Settings > Qualtrics IDs). The variables are as follows:

- `QXSMS_API_KEY`: the Qualtrics API key, of the user used for the API calls (we recommend a dedicated Qualtrics account for a production environment)
- `QXSMS_LIBRARY_ID`: the shared library where messages are available
- `QXSMS_DIRECTORY_ID`: the directory to use for contact creation
- `QXSMS_SECRET_KEY`: web application secret
- `QXSMS_SMS_SURVEY`: survey that will be used to send sms and email to respondents
- `QXSMS_QX_DOMAIN`: Qualtrics domain used

With Docker and Docker Compose installed, the first step is to build images and start the services.

Copy the configuration:

```sh
cp docker-compose.dev.yml docker-compose.yml
```

Build the images:

```sh
docker compose build
```

Start the containers:

```sh
docker compose up
```

The QxSMS app is then accessible at `localhost:8000`.

Here is the services description:

- `db`: Postgres database
- `rabbit`: Rabbitmq server, used as a task broker by celery
- `worker`: celery worker process, that pops and executes tasks from Rabbitmq
- `qxsms`: Django web application
- `doc`: user documentation

### our WPSS production environement

include production.md (or summarise ?)

## Minimal setup
It is now time to create a minimal setup on the django app:

1. create a django admin account
2. create a study coordinator (aka HQ user belonging to th HQ group). For the study setup, you can no refer to [the online wiki](https://cdsp-scpo.github.io/wpss-doc/hq/seeding-a-study/)

### User creation - notes -

An email with a link to reset the password is sent upon user creation (only nc). When the password is reset, the user is automatically logged in.

This is done by the `send_welcome()` method in the `User` model.

The password reset link timeout has been set to 1 day (see `setting.PASSWORD_RESET_TIMEOUT_DAYS`).

## Going further

### Internationalisation / regionalisation (I18N)

The whole django app is regionalisable.
To generate `.po` files used for localization, we exclude `hq` and `manager` apps since only the panelist interface is meant to be translated for now:

```sh
django-admin makemessages -i hq -i manager -i distributions -i templates/hijack
```
### WPSS management command

`python manage.py <command>`

#### HQ

- `initdb`: Init database (default) or revert with --revert argument
- `csvimport`: ?

#### Manager

- `fakecsv`: Generate fake profile CSV data
- `fix_panelist_deactivation`: Runs deactivation process on manually anonymized profiles.
- `get_panelist_ids`: Get panelist IDs from a list of Profile.uid (extRef on Qualtrics side)
- `time_import_worker`: Measure time to import CSV panelists
- `time_import`: Measure time to import CSV panelists

#### Qxauth

- `createadmin`: Creates an admin account and sends its credentials by email to ADMINS

### Frontend
We use SCSS as a preprocessor for CSS files. The source files are located under `/frontend/scss/`.

#### Environments

The SCSS files are compiled in the Dockerfiles by the `nbuilder` and then copied by the last stage.

In development, the CSS files are copied to `/static/` folder and the location is appended to the `STATICFILES_DIRS` setting. The generated files could not be copied to a folder inside `/qxsms/` because a volume is mounted there by docker-compose. The mounted folder would replace all files and the CSS would not be available to serve.

In production, the CSS files are copied directly to the `/qxsms/static/` folder since no volume is mounted.

`bootstrap.native` js is also copied from `node_modules` to `/qxsms/static`.


### Qualtrics integration mechanisms

[Generating individual links](./docs/user/src/hq/fieldwork.md) for a survey creates a snapshot (Qualtrics transaction) of the information about the panelists used in Qualtrics: contact information (name, email, phone, ...) + [embedded data](./docs/user/src/survey/survey-creation.md). Each time the links are used to send a message, the panelist information used is taken from this snapshot. If panelists are updated after the creation of the links, the state of this information will not update. The new information will only be included in future link creations, when new snapshots are made.

All links are stored in the WPSS database, and they are also available as embedded data on Qualtric side, with other variables (see [survey creation](./docs/user/src/survey/survey-creation.md)).
