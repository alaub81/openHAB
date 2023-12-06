#!/bin/bash
#########################################################################
#Name: unifi_protect_binding_tools.sh
#Subscription: Restarts the unifi protect Bridge when not running
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

#openHAB URL
OPENHAB=https://localhost:8443
#API Authentification Token for openhab3
AUTH="oh.unifi.jcsada2eWbf23jf31r2sacdasdux2a5syWHTJacfdsfdctCeiwA"
#Unifi Protect NVR Bridge
BRIDGE=unifiprotect:nvr:d8d7c06f9e

# logfile options
# Lines displayed in the output
NUMBER=30
# Where is the openhab.log
LOGFILE=/var/lib/docker/volumes/openhab4_data_openhab_userdata/_data/logs/openhab.log

#do the things
function getstatus {
        FULLSTATUSBRIDGE=$(curl -s -k -X GET "$OPENHAB/rest/things/$BRIDGE/status" -H "accept: application/json" -H "Authorization: Bearer $AUTH")
        STATUSBRIDGE=$(echo $FULLSTATUSBRIDGE | cut -d":" -f2 | cut -d"," -f1 | cut -d'"' -f2)
        STATUSBRIDGEDETAIL=$(echo $FULLSTATUSBRIDGE | cut -d":" -f3 | cut -d"," -f1 | cut -d'"' -f2)
}

function status {
        echo "Bridge Status: $STATUSBRIDGE"
}

function fullstatus {
        echo "Bridge Fullstatus: $FULLSTATUSBRIDGE"
}

function restart {
        echo "Restarting $BRIDGE"
        curl -s -k -X PUT "$OPENHAB/rest/things/$BRIDGE/enable" -H "Content-Type: text/plain" -H "accept: */*" -H "Authorization: Bearer $AUTH" -d "false" > /dev/null
        sleep 3
        curl -s -k -X PUT "$OPENHAB/rest/things/$BRIDGE/enable" -H "Content-Type: text/plain" -H "accept: */*" -H "Authorization: Bearer $AUTH" -d "true" > /dev/null
}

function autorestart {
        if [ "$STATUSBRIDGE" != "ONLINE" ] || [ "$STATUSBRIDGEDETAIL" != "NONE" ]; then
                echo "status is not Online!"
                echo "-------------------------------------"
                fullstatus
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
                if [ "$STATUSBRIDGE" != "ONLINE" ] || [ "$STATUSBRIDGEDETAIL" != "NONE" ]; then
                        echo -e "\nRestart didn't work Bridge Status!"
                        echo "-------------------------------------"
                        fullstatus
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
        *)
                echo "Usage: $0 { status | fullstatus | restart | autorestart }"
                exit 1
                ;;
esac