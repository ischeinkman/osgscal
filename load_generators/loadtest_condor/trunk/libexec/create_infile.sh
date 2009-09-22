#!/bin/bash

function Usage {
    echo "Usage: `basename $0` <filename> <filesize>"
}

if [ $# -lt 2 ]; then
    Usage
    exit 1
fi

filename=$1
filesize=$2

dd if=/dev/urandom of=$filename bs=1k count=$filesize
if [ $? -ne 0 ]; then
    echo "Failed to create $filename" 1>&2
    exit 2
fi

md5sum $filename > ${filename}.md5
if [ $? -ne 0 ]; then
    echo "Failed to create md5 for $filename" 1>&2
    exit 3
fi
exit 0

