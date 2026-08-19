#!/usr/bin/env bash
# Usage: screen-start.sh [session-suffix]
# Creates (or reattaches to) a screen session named <hostname>[-suffix]
# with 5 pre-named windows.

HOST=$(hostname -s)
SUFFIX=${1:+"-$1"}
SESSION="${HOST}${SUFFIX}"

if screen -list | grep -q "${SESSION}"; then
    echo "Reattaching to existing session: ${SESSION}"
    screen -r "${SESSION}"
else
    echo "Starting new screen session: ${SESSION}"
    screen -S "${SESSION}"
fi
