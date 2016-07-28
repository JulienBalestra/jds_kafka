#!/usr/bin/env bash

set -o pipefail

ENDPOINT=()

function join { local IFS="$1"; shift; echo -n "$*"; }

if [ -z $PORT ]
then
    PORT=9092
fi

if [ -z $SINCEDB ]
then
    echo '$SINCEDB missing'
    exit 1
fi

if [ -z $JDS ]
then
    echo '$JDS missing'
    exit 1
fi

if [ -z $DNS_SEARCH ]
then
    echo 'DNS_SEARCH missing like: "kafka.skydns.local" for kafka0.kafka.skydns.local, kafka1.kafka.skydns.local, ... '
    exit 1
fi

for ENTRY in $(dig +short @localhost $DNS_SEARCH)
do
    ENDPOINT+=("$ENTRY:$PORT")
done

echo $(join , ${ENDPOINT[@]})
exec $JDS $(join , ${ENDPOINT[@]}) --sincedb_path $SINCEDB