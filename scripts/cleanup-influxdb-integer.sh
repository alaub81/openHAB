#!/bin/bash
#########################################################################
#Name: cleanup-influxdb-integer.sh
#Subscription: This Script deletes all integer measurements, which causes
#problems in openHAB. The Message in the log is "field type conflict: input field"
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
# openHAB logfile
OPENHABLOG="/var/lib/docker/volumes/openhab3_data_openhab_userdata/_data/logs"
# InfluxDB Command
INFLUX="docker exec -ti openhab3_influxdb_1 influx"
# InfluxDB Host
INFLUXHOST=localhost
# openHAB Database
INFLUXDB=openhab_db

# do the stuff
for i in $(grep "field type conflict: input field" $OPENHABLOG | cut -d'"' -f4 | sort -n | uniq); do
        $INFLUX -host $INFLUXHOST -port '8086' -database $INFLUXDB -execute "drop measurement $i"
        echo delete measurement: $i
done
