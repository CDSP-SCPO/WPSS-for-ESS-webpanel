#!/usr/bin/env sh
python manage.py makemigrations;
python manage.py createcachetable;
python manage.py compilemessages;
python manage.py migrate;
python manage.py createadmin;
python manage.py create_group;
python manage.py runserver 0.0.0.0:8000;
