#!/bin/bash
#########################################################################
#Name: rename-influxdb-measurement.sh
#Subscription: This Script renames influxdb measurements
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
# InfluxDB Command
INFLUX="docker exec -ti openhab3_influxdb_1 influx"
# InfluxDB Host
INFLUXHOST=localhost
# openHAB Database
INFLUXDB=openhab_db

OLDMEASUREMENT=$1
NEWMEASUREMENT=$2

# do the stuff
if [ "$1" = "" -o "$2" = "" ]; then
        echo -e "Usage: ${0} { OldMeasurementName } { NewMeasurementName }\n"
        exit
fi

# Rename MEASUREMENT
$INFLUX -host $INFLUXHOST -port '8086' -database $INFLUXDB -execute "SELECT * INTO $NEWMEASUREMENT FROM $OLDMEASUREMENT"
$INFLUX -host $INFLUXHOST -port '8086' -database $INFLUXDB -execute "DROP MEASUREMENT $OLDMEASUREMENT"
echo "deleted old measurement: $OLDMEASUREMENT"
