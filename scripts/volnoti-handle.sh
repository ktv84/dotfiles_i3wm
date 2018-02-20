#!/bin/bash

STEP=5
UNIT="%" 
VOLUME=$(amixer get Master | grep "Playback.*\[.*%\]" | head -1 | awk '{print $4;}' | tr -d "\[\]")
STATE=$(amixer get Master | grep 'Mono:' | awk '{print $6}' | tr -d "\[\]")
SETVOL="/usr/bin/amixer -q -D pulse set Master"
DIRECTION=$1

case "$1" in
    "up")
          $SETVOL $STEP$UNIT+
          ;;
  "down")
          $SETVOL $STEP$UNIT-
          ;;
  "mute")
          $SETVOL toggle
          ;;
esac

# Show volume with volnoti
if [[ "$STATE" == "on" ]]; then
    volnoti-show $VOLUME
else
    volnoti-show -m
fi

exit 0
