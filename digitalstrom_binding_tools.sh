#!/bin/bash
#########################################################################
#Name: digitalstrom_binding_tools.sh
#Subscription: This Script tries to get the things with the openHAB digitalstrom
#              binding more stable
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

#openHAB URL
OPENHAB=https://localhost:8443
#API Authentification Token for openhab3
AUTH="oh.tokenname.hkkxsacdfVizb8P82bKQUh7exasd3433pQJuzZlQVdj8BJdzwjTznZQkcK1sIysEWtrWQLf2RhTg"
#digitalSTROM Things UID (%3A is :)
#digitalSTROM Bridge
BRIDGE=digitalstrom:dssBridge:eb907aa7
#digitalSTROM Rolladen
ROLLO=digitalstrom%3AGR%3Aeb907aa7%3A303505d7f8000f00000fb6e7
#digitalSTROM Stromverbrauch
WATT=digitalstrom%3Acircuit%3Aeb907aa7%3A302ed89f43f00e400000cc38
#digitalSTROM ALL Groups for refresh the Sensor Status
ALL="Rolladen_ALL Lichter_DSS_ALL"

# IP of the Digitalstrom Server
DSS=192.168.50.100

# logfile options
# Lines displayed in the output
NUMBER=30
# Where is the openhab.log
LOGFILE=/var/lib/docker/volumes/openhab_data_openhab_userdata/_data/logs/openhab.log

#do the things
function getstatus {
        FULLSTATUSBRIDGE=$(curl -s -k -X GET "$OPENHAB/rest/things/$BRIDGE/status" -H "accept: application/json" -H "Authorization: Bearer $AUTH")
        FULLSTATUSROLLO=$(curl -s -k -X GET "$OPENHAB/rest/things/$ROLLO/status" -H "accept: application/json" -H "Authorization: Bearer $AUTH")
        FULLSTATUSWATT=$(curl -s -k -X GET "$OPENHAB/rest/things/$WATT/status" -H "accept: application/json" -H "Authorization: Bearer $AUTH")
        STATUSBRIDGE=$(echo $FULLSTATUSBRIDGE | cut -d":" -f2 | cut -d"," -f1 | cut -d'"' -f2)
        STATUSROLLO=$(echo $FULLSTATUSROLLO | cut -d":" -f2 | cut -d"," -f1 | cut -d'"' -f2)
        STATUSWATT=$(echo $FULLSTATUSWATT | cut -d":" -f2 | cut -d"," -f1 | cut -d'"' -f2)
        STATUSBRIDGEDETAIL=$(echo $FULLSTATUSWATT | cut -d":" -f3 | cut -d"," -f1 | cut -d'"' -f2)
}

function status {
        echo "Bridge Status: $STATUSBRIDGE"
        echo "Bridge Status Detail: $STATUSBRIDGEDETAIL"
        echo "Rolladen Status: $STATUSROLLO"
        echo "Verbrauch Status: $STATUSWATT"
}

function fullstatus {
        echo "Bridge Fullstatus: $FULLSTATUSBRIDGE"
        echo "Rolladen Fullstatus: $FULLSTATUSROLLO"
        echo "Verbrauch Fullstatus: $FULLSTATUSWATT"
}

function refresh {
        for i in $ALL; do
                curl -s -k -X POST "$OPENHAB/rest/items/$i" -H "Content-Type: text/plain" -H "accept: */*" -H "Authorization: Bearer $AUTH" -d "REFRESH" 
                echo "Refresh $i Done!"
        done
}

function restart {
        echo "Restarting $BRIDGE"
        curl -s -k -X PUT "$OPENHAB/rest/things/$BRIDGE/enable" -H "Content-Type: text/plain" -H "accept: */*" -H "Authorization: Bearer $AUTH" -d "false" > /dev/null
        sleep 3
        curl -s -k -X PUT "$OPENHAB/rest/things/$BRIDGE/enable" -H "Content-Type: text/plain" -H "accept: */*" -H "Authorization: Bearer $AUTH" -d "true" > /dev/null
}

function autorestart {
	if [ "$STATUSBRIDGE" != "ONLINE" ] || [ "$STATUSROLLO" != "ONLINE" ] || [ "$STATUSWATT" != "ONLINE" ] || [ "$STATUSBRIDGEDETAIL" != "NONE" ]; then
		echo "status is not Online!"
		echo "-------------------------------------"
		fullstatus
		echo -e "\nConnection Test"
		echo "-------------------------------------"
		ping -q -c 5 $DSS
		echo -e "\nlast $NUMBER line of $LOGFILE"
		echo "-------------------------------------"
		tail -n $NUMBER $LOGFILE
		echo " "
		restart
		echo "-------------------------------------"
		sleep  10
		echo -e "\n after restart"
		echo "last $NUMBER line of $LOGFILE"
		echo "-------------------------------------"
		tail -n $NUMBER $LOGFILE
		getstatus
		if [ "$STATUSBRIDGE" != "ONLINE" ] || [ "$STATUSROLLO" != "ONLINE" ] || [ "$STATUSWATT" != "ONLINE" ] || [ "$STATUSBRIDGEDETAIL" != "NONE" ]; then
			echo -e "\nRestart didn't work Bridge Status!"
			echo "-------------------------------------"
			fullstatus
		elif [ "$NEWSTATUS" = "ONLINE" ]; then
			refresh
			echo "\n refreshing Item Status "
			echo "-------------------------------------"
		fi
	fi
}

case "$1" in
        status)
		getstatus
                status
                ;;
        fullstatus)
		getstatus
                status
                fullstatus
                ;;
        restart)
                restart
                ;;
        autorestart)
		getstatus
                autorestart
                ;;
        refresh)
                refresh
                ;;
        *)
                echo "Usage: $0 { status | fullstatus | refresh | restart | autorestart }"
                exit 1
                ;;
esac
