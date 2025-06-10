#!/bin/bash
#########################################################################
#Name: delete-influxdb2-measurement-timerange.sh
#Subscription: This Script deletes values of a measurement in influxDB2 within
#              a configured timerange. 
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
# InfluxDB Organisation
ORG=yourorganisation
# InfluxDB Bucket
BUCKET=yourbucket
# InfluxDB2 admin Token (generate one if you do not have one)
INFLUXDBAUTH="TkrV8yQ8G2Wb1pk4xsacrewfervce9xVTGgtzsb_bfcasdcasdc-ascdD-JlB7AKBZjE>"
# Measurement, das gelöscht werden soll
MEASUREMENT="SMAEnergyMeter_BezogeneLeistung"
# Define Timerange
START="2025-06-02T16:10:00.000Z"
STOP="2025-06-07T09:15:00.000Z"

# do the stuff
curl --request POST "http://$INFLUXHOST:8086/api/v2/delete?org=$ORG&bucket=$BUCKET>
  --header "Authorization: Token $INFLUXDBAUTH" \
  --header 'Content-Type: application/json' \
  --data '{
    "start": "'$START'",
    "stop": "'$STOP'",
    "predicate": "_measurement=\"'"$MEASUREMENT"'\""
  }'