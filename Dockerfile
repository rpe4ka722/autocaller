FROM alt:latest

RUN mkdir /opt/autocaller
WORKDIR /opt/autocaller
COPY . /opt/autocaller

RUN apt-get update \
    && apt-get install tts-base -y\
    && apt-get install RHVoice-bin -y\
    && apt-get install RHVoice-Russian -y\
    && apt-get install RHVoice-Russian-elena -y\
    && apt-get install python3 -y\ 
    && apt-get install python3-module-django -y\ 
    && apt-get install python3-module-django-dbbackend-sqlite3 -y\
    && apt-get install python3-module-jinja2 -y\
    && apt-get install python3-module-django-environ -y\
    && apt-get install python3-module-requests -y\
    && apt-get install python3-module-openpyxl -y\
    && apt-get install python3-module-celery -y\
    && apt-get install python3-module-gunicorn -y\
    && apt-get install sox -y\
    # && apt-get install RHVoice -y\
    && apt-get install python3-module-redis-py -y
    