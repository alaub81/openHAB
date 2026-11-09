# Prepare MQTT passwords and TLS

Run these steps from the repository root **before first enabling the `mqtt` profile**.
The supplied broker rejects anonymous clients and expects a password file plus
TLS certificates. Existing installations should retain their working accounts
and certificates.

## Example broker account

The repository includes `data/mosquitto/conf/mosquitto.passwd` with this public
example account:

- Username: `mosquitto`
- Password: `mosquitto-mqtt`

The password file contains a salted PBKDF2-SHA512 hash generated with
`mosquitto_passwd`, not the plaintext password. **These credentials are public;
replace the example password before using the broker in your own installation.**
The hash does not make a publicly documented password private.

## Replace the example password

This one-off container runs only the password utility, without starting the
broker or its dependencies. It prompts for the new password without putting it
in the command line and preserves other accounts:

```bash
docker compose run --rm --no-deps --user 0 \
  --entrypoint mosquitto_passwd mosquitto \
  /mosquitto/config/mosquitto.passwd mosquitto
```

To add another account, replace the final `mosquitto` with your desired username.
Remove the public example account with `mosquitto_passwd -D` if you do not use it.
Use `-c` only when deliberately replacing the entire password file: it overwrites
all existing accounts. Restart a running broker after account changes during a
suitable maintenance window.

The example password file is tracked by Git. Keep your deployment password file
on the host and do not commit real account hashes or overwrite it when updating
from the repository.

## Provide certificates

The broker expects these files under `data/mosquitto/conf/certs/`:

| File | Purpose |
| --- | --- |
| `ca.crt` | Issuing CA certificate, also trusted by MQTT clients |
| `server.crt` | Broker certificate, including its DNS/IP Subject Alternative Names |
| `server.key` | Broker private key |

You may install certificates from your existing CA at those paths. The server
certificate must match the broker address used by clients. Clients trust the CA;
the supplied configuration does not require client certificates. Alternatively,
use the following local-CA example for a new installation.

### Create a local CA and broker certificate

These commands create new keys and overwrite files with the same names. Use
them only for initial setup, not to replace a working CA during an update.
Set `mqtt_dns` and `mqtt_ip` to the real broker hostname and reachable address.
The example uses OpenSSL 1.1.1+ and a repository path without spaces.

```bash
umask 077
mqtt_dns=mqtt.example.invalid
mqtt_ip=192.0.2.10
mkdir -p certs data/mosquitto/conf/certs

openssl req -x509 -newkey rsa:3072 -nodes -sha256 -days 3650 \
  -subj '/CN=Local MQTT CA' \
  -addext 'basicConstraints=critical,CA:TRUE' \
  -addext 'keyUsage=critical,keyCertSign,cRLSign' \
  -keyout certs/ca.key -out certs/ca.crt

openssl req -new -newkey rsa:2048 -nodes -sha256 \
  -subj "/CN=$mqtt_dns" \
  -keyout certs/server.key -out certs/server.csr

printf 'basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:%s,IP:%s\n' \
  "$mqtt_dns" "$mqtt_ip" > certs/server.ext

openssl x509 -req -sha256 -days 365 \
  -in certs/server.csr -CA certs/ca.crt -CAkey certs/ca.key \
  -CAcreateserial -extfile certs/server.ext -out certs/server.crt

cp certs/ca.crt certs/server.crt certs/server.key data/mosquitto/conf/certs/
openssl verify -CAfile certs/ca.crt certs/server.crt
```

Retain the CA key securely for future certificate renewal and distribute only
`ca.crt` to clients. Renew the server certificate before expiry. The legacy
[`generate-certs.sh`](../certs/generate-certs.sh) helper uses a configured fixed
project path and Common Names without SAN extensions; the procedure above
explicitly supplies SANs for hostname/IP verification.

## Set broker file permissions

Let the image's `mosquitto` account read the password file and server key. The
helper below adjusts only the files mounted in the broker's configuration.

```bash
chmod 755 data/mosquitto/conf/certs

docker compose run --rm --no-deps --user 0 --entrypoint sh mosquitto -ec '
  owner="$(id -u mosquitto):$(id -g mosquitto)"
  chown "$owner" /mosquitto/config/mosquitto.passwd /mosquitto/config/certs/server.key
  chmod 640 /mosquitto/config/mosquitto.passwd /mosquitto/config/certs/server.key
  chmod 644 /mosquitto/config/certs/ca.crt /mosquitto/config/certs/server.crt
'
```

Generated certificate files and the local `.env` are ignored by Git. Only the
public example password hash belongs in the tracked `mosquitto.passwd`; do not
commit deployment password hashes.

## Start and connect

Return to the [stack quick start](../README.md#3-validate-and-start). After startup:

```bash
docker compose ps mosquitto
docker compose exec -T mosquitto tail -n 50 /mosquitto/log/mosquitto.log
```

The default published ports are 1883 for plaintext and 8883 for TLS. Both require
the configured username/password. Set the client to use TLS and trust `ca.crt`
when connecting to 8883. The TCP healthcheck proves listener availability, not
successful authentication or certificate validation; verify a publish/subscribe
exchange using a real client.

References: [Mosquitto password utility](https://mosquitto.org/man/mosquitto_passwd-1.html),
[broker configuration](https://mosquitto.org/man/mosquitto-conf-5.html),
[OpenSSL request command](https://docs.openssl.org/3.0/man1/openssl-req/).
