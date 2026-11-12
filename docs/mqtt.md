# Prepare MQTT passwords and TLS

Run these steps from the repository root **before first starting the MQTT broker**.
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

Download the selected stack images once using `docker compose pull` as shown in
the [quick start](../README.md#2-download-images-and-prepare-mqtt). No separate
broker startup is needed during preparation.

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
certificate must match the broker address used by clients that verify it. Clients
with certificate verification enabled trust the CA;
the supplied configuration does not require client certificates. Alternatively,
use the following local-CA example for a new installation.

### Quick option: generate certificates for one broker address

For a new installation, set `MQTT_HOST` to the DNS name or IPv4 address clients
will use. The disposable local test used `localhost`; use your real broker
address for other machines:

```bash
MQTT_HOST=mqtt.example.invalid bash certs/generate-certs.sh --execute
```

The helper creates a local CA, server certificate with one matching SAN, and an
optional client certificate. It refuses to overwrite existing output files and
copies only `ca.crt`, `server.crt` and `server.key` into the broker directory.
Without `--execute`, it only previews the operation. Continue with
[file permissions](#set-broker-file-permissions), then start the entire stack
through the README. The broker does not require the generated client certificate.
The CA is valid for 3,650 days; server and client certificates for 365 days.
Keep `certs/ca.key` private and renew leaf certificates before expiry.

### Alternative: create a certificate with multiple SANs

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
`ca.crt` to clients. Renew the server certificate before expiry.

## Set broker file permissions

Let the image's `mosquitto` account read the password file and server key. The
helper below adjusts only the files mounted in the broker's configuration.
Run it once after creating or replacing those files, not before every startup.
Generated files initially have owner-only permissions; the broker must be able
to read them after dropping privileges.

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
the configured username/password. Clients using certificate verification must
trust the issuing CA when connecting to 8883. The TCP healthcheck proves listener availability, not
successful authentication or certificate validation; verify a publish/subscribe
exchange using a real client.

### Connect openHAB using TLS and certificate pinning

After the full stack is healthy, install the MQTT binding and add an MQTT Broker
Thing under **Settings → Things → + → MQTT Binding**. openHAB uses host networking,
so select the broker's published host port, not Docker service DNS:

| Setting | Value for the local test |
| --- | --- |
| Host (`host`) | `localhost`, matching the generated server certificate |
| Port (`port`) | `8883`, or `MOSQUITTO_MQTTS_PORT` from `.env` |
| Secure (`secure`) | `true` |
| Validate hostname (`hostnameValidated`) | `true` |
| Username / password | The account configured above |
| Certificate pinning (`certificatepin`) | `true` |
| Public key pinning (`publickeypin`) | `false` |

For another broker address, use a name/IP covered by its certificate. Enable
advanced settings and set **Certificate hash** (`certificate`) to the output of:

```bash
openssl x509 -in certs/server.crt -noout -fingerprint -sha256 \
  | sed 's/^.*=//; s/://g; s/^/SHA-256:/'
```

The required format is `SHA-256:` followed by the hexadecimal hash **without
colons between bytes**. An unmodified OpenSSL fingerprint contains extra colons
and causes `HANDLER_INITIALIZING_ERROR` with `Algorithm is missing`. Pinning this
known certificate authenticates it without a separate Java CA import. Update
the configured hash after deliberately renewing/replacing the certificate.
Save the Thing and check that it becomes **ONLINE**.

See the [MQTT binding settings](https://www.openhab.org/addons/bindings/mqtt/#bridge-configuration).

### Optional publish/subscribe check

For a server certificate containing `localhost`, run this after startup. Enter
the broker password when prompted; it is not entered literally in shell history.
It sends only a synthetic, non-retained message:

```bash
docker compose exec mosquitto sh -c '
  printf "MQTT password: "
  read -r -s password
  printf "\n"
  mosquitto_sub -h localhost -p 8883 \
    --cafile /mosquitto/config/certs/ca.crt \
    -u mosquitto -P "$password" -t firstsetup/test -C 1 -W 10 -v &
  subscriber=$!
  sleep 1
  mosquitto_pub -h localhost -p 8883 \
    --cafile /mosquitto/config/certs/ca.crt \
    -u mosquitto -P "$password" -t firstsetup/test -m firstsetup-ok -q 1
  wait "$subscriber"
'
```

Expect `firstsetup/test firstsetup-ok`. This checks authentication, certificate
validation and message delivery inside the container; it does not by itself
verify access from a remote client. Adapt the hostname to your certificate.

### Optional bridge connections

The SMA and BMW bridge examples use TLS on 8883 with certificate verification
disabled. They encrypt traffic but do not authenticate the broker certificate or
hostname and do not require a client CA file. The broker's own server certificate
and key are still required. Keep the bridge TLS flags enabled when applying
those examples; the [Advanced guide](bridges.advanced.md) describes their settings.

References: [Mosquitto password utility](https://mosquitto.org/man/mosquitto_passwd-1.html),
[broker configuration](https://mosquitto.org/man/mosquitto-conf-5.html),
[OpenSSL request command](https://docs.openssl.org/3.0/man1/openssl-req/).
