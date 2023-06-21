#!/usr/bin/env sh
if [ $QXSMS_DEBUG -eq 1 ]
then
  # dev dependencies have to be installed if debug is set to true in the prod env
  pip install -r requirements.dev.txt;
fi
python manage.py migrate;
python manage.py createcachetable;
python manage.py createadmin;
python manage.py create_group;
python manage.py compilemessages;
python manage.py collectstatic --noinput --link --no-color --clear -v 0;
gunicorn --reload --config=docker-gunicorn.conf.py --access-logfile - --error-logfile - qxsms.wsgi:application;
