# Run the existing Grafana service without root

The repository Compose file no longer sets `user: "0"` for Grafana. Docker uses
its image's default user instead. The official image normally uses UID 472;
verify the actual UID and GID from the **installed image**, as shown below.
A primary GID of 0 does not make a nonzero UID the root user.

This procedure changes the Grafana process user and permissions on its existing
`/var/lib/grafana` named volume. It does not upgrade images or migrate databases.
Dashboards, users, data sources, and alert rules are stored in PostgreSQL in this
setup; plugins and other local files remain in the Grafana volume.

Run the commands on the Docker server in Bash, in the existing Compose project
directory. Use the same project name, Compose files, and environment files as
normal. The examples assume `docker-compose.yml` and `.env` in that directory.
If you normally use `-p`, `-f`, or `--env-file`, add those same arguments to the
`dc` function. Do not run `down`, delete volumes, or change version variables.
Grafana and its alert evaluation will be unavailable while stopped. openHAB,
InfluxDB, PostgreSQL, Mosquitto, and the renderer stay running.

Execute each section in order. Stop and investigate if any command fails;
do not continue with an incomplete backup or failed permission check.

## 1. Identify the running instance and installed image

```bash
dc() { docker compose "$@"; }

dc config --quiet
grafana_cid="$(dc ps -q grafana)"
test -n "$grafana_cid"
test "$(docker inspect --format '{{.State.Running}}' "$grafana_cid")" = true

grafana_image_id="$(docker inspect --format '{{.Image}}' "$grafana_cid")"
grafana_volume="$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/var/lib/grafana"}}{{if eq .Type "volume"}}{{.Name}}{{end}}{{end}}{{end}}' "$grafana_cid")"
test -n "$grafana_volume"
docker volume inspect "$grafana_volume" >/dev/null

docker inspect --format 'Current configured user: {{.Config.User}}' "$grafana_cid"
docker image inspect --format 'Image default user: {{.Config.User}}' "$grafana_image_id"

grafana_uid="$(docker run --rm --pull never --network none --entrypoint /bin/sh "$grafana_image_id" -c 'id -u')"
grafana_gid="$(docker run --rm --pull never --network none --entrypoint /bin/sh "$grafana_image_id" -c 'id -g')"
test "$grafana_uid" -gt 0
test "$grafana_gid" -ge 0
printf 'Target UID:GID = %s:%s\nData volume = %s\n' "$grafana_uid" "$grafana_gid" "$grafana_volume"
```

These temporary containers use the image default user and do not mount live
data. If the image default is root, or the data mount is a bind mount rather
than a named volume, stop: this procedure needs adapting for that installation.

## 2. Back up configuration, database, and Grafana files

Keep this Bash session open; later commands reuse the variables above.

```bash
umask 077
grafana_backup_dir="$PWD/backups/grafana-non-root-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$grafana_backup_dir"
cp docker-compose.yml "$grafana_backup_dir/compose-before.yml"

# Pin the exact currently running image for this migration only.
printf 'services:\n  grafana:\n    image: "%s"\n' "$grafana_image_id" > "$grafana_backup_dir/migration-image.yml"
printf 'image=%s\nvolume=%s\nuid=%s\ngid=%s\n' \
  "$grafana_image_id" "$grafana_volume" "$grafana_uid" "$grafana_gid" \
  > "$grafana_backup_dir/instance.txt"

dc stop grafana

dc exec -T postgres sh -ec 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > "$grafana_backup_dir/grafana-postgres.dump"
test -s "$grafana_backup_dir/grafana-postgres.dump"
dc exec -T postgres pg_restore --list \
  < "$grafana_backup_dir/grafana-postgres.dump" > /dev/null

docker run --rm --pull never --network none --user 0 --entrypoint /bin/sh \
  --mount "type=volume,src=$grafana_volume,dst=/data,readonly" \
  --mount "type=bind,src=$grafana_backup_dir,dst=/backup" \
  "$grafana_image_id" -ec 'tar -czf /backup/grafana-data.tar.gz -C /data .'

docker run --rm --pull never --network none --user 0 --entrypoint /bin/sh \
  --mount "type=bind,src=$grafana_backup_dir,dst=/backup,readonly" \
  "$grafana_image_id" -ec 'tar -tzf /backup/grafana-data.tar.gz >/dev/null'
```

The archive preserves the volume contents before ownership changes. The dump
covers the separate Grafana database. Archive listing and `pg_restore --list`
check readability, not a complete test restore. Store backups outside Git and
retain your normal off-server backups. If a backup fails, start the unchanged
Grafana service again and resolve the failure before proceeding.

## 3. Prepare permissions and remove the root override

The following root helper changes only the selected Grafana volume. It does not
start Grafana or connect to the network. No world-writable permissions are added.

```bash
docker run --rm --pull never --network none --user 0 --entrypoint /bin/sh \
  --mount "type=volume,src=$grafana_volume,dst=/data" \
  "$grafana_image_id" -ec 'chown -R "$1:$2" /data; chmod -R u+rwX /data' \
  sh "$grafana_uid" "$grafana_gid"
```

In the **server's existing** Compose file, remove only the Grafana service's
`user: "0"` line. Leave its volumes, environment, ports, networks, and other
services unchanged. The repository version already has that change; avoid
replacing the entire server file if it has installation-specific settings.
Also check any Compose override files for a remaining Grafana `user: "0"`.

```bash
dc config --quiet

# Exercise writes as the image default user before starting the application.
docker run --rm --pull never --network none --entrypoint /bin/sh \
  --mount "type=volume,src=$grafana_volume,dst=/var/lib/grafana" \
  "$grafana_image_id" -ec '
    test "$(id -u)" -ne 0
    test -r /var/lib/grafana
    test -x /var/lib/grafana
    probe="$(mktemp /var/lib/grafana/.non-root-check.XXXXXX)"
    rm "$probe"
    if [ -d /var/lib/grafana/plugins ]; then
      probe="$(mktemp /var/lib/grafana/plugins/.non-root-check.XXXXXX)"
      rm "$probe"
    fi
  '
```

## 4. Recreate only Grafana and verify it

```bash
dc -f docker-compose.yml -f "$grafana_backup_dir/migration-image.yml" \
  up -d --no-deps --pull never --force-recreate grafana

dc ps grafana
dc logs --tail=100 grafana
dc exec -T grafana id
dc exec -T grafana sh -ec '
  test "$(id -u)" -ne 0
  test -w /var/lib/grafana
  probe="$(mktemp /var/lib/grafana/.non-root-check.XXXXXX)"
  rm "$probe"
  wget -qO- http://localhost:3000/api/health
'
```

If your `dc` function already selects Compose files with `-f`, include **all**
those base/override files in the recreate command, followed by the temporary
`migration-image.yml`. Do not omit an existing override or change project name.
The migration override pins the installed image without changing the version
variable in `.env`. Future normal deployments use the usual configured image.

Allow startup to finish, then rerun health/log checks if necessary. Success means:

- The effective process UID is nonzero. `id` may show primary group 0; UID is
  the decisive check for this migration.
- `/api/health` reports `database: ok`, and Docker eventually reports healthy.
- Logs contain no `permission denied`, plugin installation, or database errors.
- Login works; existing dashboards, users, and data sources are present.
- A dashboard panel queries InfluxDB successfully.
- A temporary dashboard can be saved, reloaded, and deleted, confirming database
  writes. Do not modify an important dashboard merely to test permissions.
- Installed plugins load, and an image export works through the unchanged renderer.
- Grafana alert rules evaluate normally. If required, use the notification
  integration's explicit test facility and check receipt; it may send a real
  message. A contact-point test alone does not prove alert screenshots work.

When these checks pass, recreate Grafana once more with the same pinned-image
command and recheck login, health, and plugin loading. This confirms that the
configuration survives recreation. Keep the backups and migration record.

## 5. Roll back if needed

For this user/permissions-only migration, restore the original Compose file and
restart the exact same image. Running as root can still access the volume after
its ownership changed. Database restoration should not be necessary because the
image and schema were not upgraded.

```bash
cp "$grafana_backup_dir/compose-before.yml" docker-compose.yml
dc config --quiet
dc -f docker-compose.yml -f "$grafana_backup_dir/migration-image.yml" \
  up -d --no-deps --pull never --force-recreate grafana

dc exec -T grafana id
dc logs --tail=100 grafana
```

Apply the same Compose-file selection rule as in the forward migration. If the
original file used `user: "0"`, the restored process should have UID 0. Retain the
volume archive and database dump for recovery if an unrelated issue occurs;
do not overwrite live data with a restore unless the cause requires it.

## References

- [Grafana Docker installation and persistent storage](https://grafana.com/docs/grafana/latest/setup-grafana/installation/docker/)
- [Grafana image user configuration](https://github.com/grafana/grafana/blob/main/Dockerfile)
