FROM alt:latest

RUN apt-get update \
    && apt-get install asterisk -y\
    && apt-get install asterisk-core-sounds-ru-wav -y

RUN service asterisk start
ENTRYPOINT ["/bin/sh", "-c", "asterisk -f"]




