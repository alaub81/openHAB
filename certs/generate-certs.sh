#!/usr/bin/env bash
#########################################################################
#Name: generate-certs.sh
#Subscription: This Script generates ssl certs
##by A. Laub
#andreas[-at-]laub-home.de
#
#License:
#This program is free software: you can redistribute it and/or modify it
#under the terms of the GNU General Public License as published by the
#Free Software Foundation, either version 3 of the License, or (at your option)
#any later version.
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
#or FITNESS FOR A PARTICULAR PURPOSE.
#########################################################################

# Optional local CA generator; see docs/mqtt.md for manual certificate setup.
set -euo pipefail
umask 077
execute=false
case "${1:---dry-run}" in
    --execute) execute=true ;;
    --dry-run) ;;
    -h|--help) echo 'Usage: MQTT_HOST=broker.example.test bash certs/generate-certs.sh [--execute|--dry-run]'; exit 0 ;;
    *) echo 'Unknown option; use --help.' >&2; exit 1 ;;
esac
[[ $# -le 1 ]] || { echo 'Too many arguments.' >&2; exit 1; }
: "${MQTT_HOST:?Set MQTT_HOST to one DNS name or IPv4 address.}"
[[ $MQTT_HOST =~ ^[A-Za-z0-9][A-Za-z0-9.-]*$ ]] || { echo 'Invalid MQTT_HOST.' >&2; exit 1; }
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cert_dir="$project_dir/certs"
broker_dir="$project_dir/data/mosquitto/conf/certs"
for name in ca.key ca.crt ca.srl server.key server.csr server.crt server.ext client.key client.csr client.crt; do
    [[ ! -e $cert_dir/$name && ! -L $cert_dir/$name ]] || { echo "Refusing to overwrite $cert_dir/$name" >&2; exit 1; }
done
for name in ca.crt server.crt server.key; do
    [[ ! -e $broker_dir/$name && ! -L $broker_dir/$name ]] || { echo "Refusing to overwrite $broker_dir/$name" >&2; exit 1; }
done
printf 'Generate a local CA, server certificate for %s and a client certificate in %s.\n' "$MQTT_HOST" "$cert_dir"
printf 'Copy CA/server certificate and server key to %s.\n' "$broker_dir"
if ! $execute; then echo 'DRY-RUN: no files written. Add --execute to generate.'; exit 0; fi
command -v openssl >/dev/null
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
san="DNS:$MQTT_HOST"
[[ ! $MQTT_HOST =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || san="IP:$MQTT_HOST"
printf 'basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nsubjectAltName=%s\nextendedKeyUsage=serverAuth\n' "$san" > "$work/server.ext"
# Short-lived leaves; the CA key stays outside the broker directory.
printf '[req]\ndistinguished_name=dn\n[dn]\n[ca]\nbasicConstraints=critical,CA:TRUE\nkeyUsage=critical,keyCertSign,cRLSign\n' > "$work/ca.conf"
openssl req -config "$work/ca.conf" -extensions ca -x509 -nodes -sha256 -newkey rsa:2048 -days 3650 -subj '/CN=Local MQTT CA' -keyout "$work/ca.key" -out "$work/ca.crt"
for name in server client; do
    cn=$MQTT_HOST
    [[ $name != client ]] || cn='mqtt-client'
    openssl req -new -nodes -sha256 -newkey rsa:2048 -subj "/CN=$cn" -keyout "$work/$name.key" -out "$work/$name.csr"
    if [[ $name == client ]]; then printf 'extendedKeyUsage=clientAuth\n' > "$work/client.ext"; fi
    openssl x509 -req -sha256 -days 365 -in "$work/$name.csr" -CA "$work/ca.crt" -CAkey "$work/ca.key" -CAserial "$work/ca.srl" -CAcreateserial -extfile "$work/$name.ext" -out "$work/$name.crt"
done
mkdir -p -- "$broker_dir"
for name in ca.key ca.crt ca.srl server.key server.csr server.crt client.key client.csr client.crt; do
    cp -n "$work/$name" "$cert_dir/"
done
cp -n "$work/ca.crt" "$work/server.crt" "$work/server.key" "$broker_dir/"
echo 'Generated files are owner-only. Set the broker-readable key ownership/mode as described in docs/mqtt.md.'
