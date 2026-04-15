#!/bin/sh
HOST="$(/bin/hostname)"
echo "Status: 302 Found"
echo "Location: http://${HOST}:8317/"
echo
