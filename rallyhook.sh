#! /bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

read -r -d '' help_text<<'EOD'
command   description

build     create virtualenv, pip install, create certs, create logfiles
start     create gunicorn daemon
restart   restart gunicorn process
stop      kill gunicorn process
EOD

read -r -d '' usage_text<<'EOD'
Usage: rallyhook.sh <command>
EOD

case "$1" in
    build)
        # conf file check
        if [[ ! -f "$DIR"/.rallyhook.json ]]; then
            printf "Setup the app with a .rallyhook.json file\n"
            exit 1
        fi

        # virtualenv
        if [[ ! -d "$DIR"/venv/bin ]]; then
            mkdir "$DIR"/venv
            virtualenv "$DIR"/venv
        fi

        # pip install
        source "$DIR"/venv/bin/activate
        pip install --upgrade pip
        pip install \
            "pyral>=1.3.1,<1.4" \
            "Flask>=0.12.1,<0.13.0" \
            "slacker>=0.9.2,<0.9.5" \
            "gunicorn>=19.7.1,<20.0.0"
        deactivate

        # TODO figure out our instance' environment and get rid of these
        mv "$DIR"/venv/lib64/python2.7/dist-packages/markupsafe/ "$DIR"/venv/lib64/python2.7/site-packages/
        mv "$DIR"/venv/lib64/python2.7/dist-packages/MarkupSafe-1.0-py2.7.egg-info/ "$DIR"/venv/lib64/python2.7/site-packages/

        # TODO get a domain name so we can get real certs?
        if [[ ! -f "$DIR"/rallyhook.pem ]] || [[ ! -f "$DIR"/cert.pem ]]; then
            openssl req \
                    -x509 \
                    -newkey rsa:4096 \
                    -keyout rallyhook.pem \
                    -out cert.pem \
                    -days 365
            openssl rsa -in rallyhook.pem -out rallyhook.pem

            if [[ ! "$?" -eq 0 ]]; then
                printf "Certs failed\n"
                exit 1
            fi

            printf "Created certs\n"
        fi

        # log files
        if [[ ! -d "$DIR"/.log ]]; then
            logfile="$DIR"/.log
            mkdir "$logfile"
            touch \
                "$logfile"/error.log \
                "$logfile"/access.log
        fi

        printf "Ready... ??\n";;

    start)
        # build check
        if [[ ! -f "$DIR"/.rallyhook.json ]] || \
               [[ ! -f "$DIR"/.log/error.log ]] || \
               [[ ! -f "$DIR"/rallyhook.pem ]] || \
               [[ ! -f "$DIR"/cert.pem ]] || \
               [[ ! -d "$DIR"/venv/bin ]]; then
            printf "Build needed\n"
            exit 1
        fi

        # daemonize
        "$DIR"/venv/bin/gunicorn \
              --daemon \
              --bind 0.0.0.0:5050 \
              --certfile "$DIR"/cert.pem \
              --keyfile "$DIR"/rallyhook.pem \
              --access-logfile "$DIR"/.log/access.log \
              --error-logfile "$DIR"/.log/error.log \
              --pid "$DIR"/.pid \
              rallyhook:app;;

    restart)
        if [[ ! -f "$DIR"/.pid ]]; then
            printf "No pidfile found. Maybe try a ps?\n"
            exit 1
        fi

        pid=$(cat "$DIR"/.pid)
        kill -HUP "$pid"
        printf "Restarted rallyhook, pid: %s\n" "$pid";;

    stop)
        if [[ ! -f "$DIR"/.pid ]]; then
            printf "No pidfile found. Maybe try a ps?\n"
            exit 1
        fi

        pid=$(cat "$DIR"/.pid)
        kill -9 "$pid"
        printf "Killed rallyhook, pid: %s\n" "$pid";;

    *)
        printf "\n%s\n\n%s\n\n" "$usage_text" "$help_text"

esac
