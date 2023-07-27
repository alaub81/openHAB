# openHAB Setup and Tools

In this repsoitory I collect everything needed to have a good running openHAB Setup. This Setup is based on a docker compose deployment. Included you can find the following toolset:

* openHAB - Smart Home Hub
* InfluxDB2 - for persistence
* grafana inclusive renderer - for the grafics
* postgres - for grafana configuration
* Mosquitto MQTT - MQTT Broker for IoT Devices

## Docker compose project

Just clone that complete repository (`/opt/openHAB`):

```bash
git clone https://github.com/alaub81/openHAB.git
```

And configure the `.env`file.

* Change the passwords!
* If you like to have grafana configured for mailing, change `GF_SMTP_ENABLED=true` and configure you mail setup.

Then you can create an openhab user and group on the host system if you like to map them.

```bash
groupadd -g 9001 openhab
useradd -u 9001 -g openhab -r -s /sbin/nologin openhab
```

Now we need the certificates for the secure mqtt connection of Mosquitto. For the generation of the certs we will use the `generate-certs.sh`. Just configure the script upfront:

* Configure at least the `IP` Variable, use the FQDN
* Change all other variables to your needs!

```bash
cd /opt/openHAB/certs
chmod +x generate-certs.sh
./generate-certs.sh
```

After that you schould be able to start the whole setup with:

```bash
cd /opt/openHAB
docker compose up -d
```

Now the Setup should be reachable:

* openHAB: <http://YOURSERVERNAME:8080> und <https://YOURSERVERNAME:8433>
* Grafana: <http://YOURSERVERNAME:3000>
* InfluxDB 2: <http://YOURSERVERNAME:8086>

### Configure Mosquitto User

to connect to the secure MQTT Broker, you need at minimum one configured user. Just create the first one:

```bash
cd /opt/openHAB
docker compose exec mosquitto mosquitto_passwd -c /mosquitto/config/mosquitto.passwd mosquitto
```

## Scripts / Tools

here you can find some usefull scripts I am using to administrate my openHAB setup. For example there are some scripts to do things in the persistnece layer, influxDB. Or to bring more stability into the digitalstrom binding. Just have a look at the Script Descriptions on top of each script.

To make the scripts running, please add the execute right to them and then just start it, e.g.:

```bash
cd scripts
chmod +x cleanup-influxdb-integer.sh
./cleanup-influxdb-integer.sh
```

## Links

If you need more Details about the setup:

* <https://www.laub-home.de/wiki/OpenHAB_4_Docker_Installation>
* <https://www.laub-home.de/wiki/OpenHAB_3_Docker_Installation>
