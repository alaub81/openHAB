#!/bin/bash
#########################################################################
#Name: cleanup-openhab-influxdb2.sh
#Subscription: This Script deletes unused item entrys in the influxdb2 
#              with InfluxDB Queries over http API
#
#by A. Laub
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
#Set the language
export LANG="en_US.UTF-8"
#Load the Pathes
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

#set the variables:

# Tempfolder
TMPDIR=/tmp/
# openHAB Server
OPENHABSERVER=localhost
# openHAB API Authentification Token
OPENHABAUTH="oh.laubraspi4.5hZjIGQVizb8P8UXFnyRJ83pQJuzZlQVdj8BJdzwjTznZQkcK1sIysEasdae34353Tg"

# InfluxDB Command
INFLUX="docker exec -ti openhab3_influxdb_1 influx"
# InfluxDB Host
INFLUXHOST=localhost
# openHAB Database
INFLUXDB=openhab_db
# InflusDB API Key
INFLUXDBAUTH="TkrV8yQ8G2Wb1pk4WnXXVGgtzsb_bxsasdca33333fucYeAQwqduAHSeTID-JlB7AKBZjE47TCwf8w-jGCFzpChw=="

# do the stuff
# generate Items list
curl -s -k -X GET "https://$OPENHABSERVER:8443/rest/items?recursive=false&fields=name" -H "accept: application/json" -H "Authorization: Bearer $OPENHABAUTH" | sed 's/,/\n/g' | awk -F '"' '{ print $4}' | sort -n > $TMPDIR/items.txt

# read Measurements from InfluxDB
curl -s --get http://$INFLUXHOST:8086/query?db=$INFLUXDB \
  --header "Authorization: Token $INFLUXDBAUTH" \
  --data-urlencode "q=SHOW measurements" |\
  awk -F '"values":\[' '{ print $2 }' |\
  sed 's/,/\n/g' |\
  awk -F '"' '{ print $2 }' |\
  sort -n > $TMPDIR/measurements.txt

# delete not used measurements
for i in $(diff -Zu $TMPDIR/items.txt $TMPDIR/measurements.txt | grep -i ^+[a-z,0-9] | cut -d '+' -f 2); do
	echo delete measurement: $i
	curl -s --get http://$INFLUXHOST:8086/query?db=$INFLUXDB \
  		--header "Authorization: Token $INFLUXDBAUTH" \
  		--data-urlencode "q=DROP MEASUREMENT $i"
done

# cleanup
rm $TMPDIR/items.txt
rm $TMPDIR/measurements.txt
