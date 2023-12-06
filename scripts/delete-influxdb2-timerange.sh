#!/bin/bash
#########################################################################
#Name: delete-influxdb2-timerange.sh
#Subscription: This Script deletes entries in the whole influxDB2 within
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
INFLUXDBAUTH="TkrV8yvsdffffG2Wb1pk4scferrfwevdsTGgtzsb_bffsfsdfsAKBZjE47TCwf8w-jGCFzpChw=="
# Define Timerange
START="2023-02-25T11:55:00.000Z"
STOP="2023-02-25T11:56:00.000Z"

# do the stuff
curl --request POST "http://$INFLUXHOST:8086/api/v2/delete?org=$ORG&bucket=$BUCKET" \
  --header "Authorization: Token $INFLUXDBAUTH" \
  --header 'Content-Type: application/json' \
  --data '{
    "start": "'$START'",
    "stop": "'$STOP'"
  }'
