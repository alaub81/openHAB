#!/bin/bash
#########################################################################
#Name: delete-influxdb2-measurement.sh
#Subscription: This Script deletes influxdb 2 measurements, defined under MEASUREMENTS
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
# InfluxDB Host
INFLUXHOST=localhost
# openHAB Database
INFLUXDB=openhab_db
# InflusDB API Key
INFLUXDBAUTH="TkrV8yQ8G2hjtziuhf5V1OhXoE9xVTGgtzsb_bfucYeAQ7i8uAHSeTID-JlB7AKBZjE47TCwf8w-jGCFzpChw=="
# Measurements to delete (seperated by space)
MEASUREMENTS="LaubIot07BME680_Gas LaubIot07BME680_Temperature LaubIot07BME680_Altitude LaubIot07BME680_Pressure"

# delete not used measurements
for i in $MEASUREMENTS; do
        echo delete measurement: $i
        curl -s --get http://$INFLUXHOST:8086/query?db=$INFLUXDB \
                --header "Authorization: Token $INFLUXDBAUTH" \
                --data-urlencode "q=DROP MEASUREMENT $i"
done
