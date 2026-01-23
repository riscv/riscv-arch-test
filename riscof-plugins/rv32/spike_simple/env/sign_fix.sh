#!/bin/sh
cat sign | sed 's/.\{8\}/& /g' | awk '{print $4 " " $3 " " $2 " " $1}' | sed 's/ /\n/g' > temp; mv \
temp sign; exit 0
