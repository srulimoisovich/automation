#!/bin/bash
# backup.sh - pack a directory into <dest_dir>/<name>_<date>.tar.gz
set -e

if [ $# -lt 1 ]; then
    echo "error: source directory required" >&2
    echo "usage: $0 <source_dir> [dest_dir]" >&2
    exit 1
fi

SRC=$1
DEST=${2:-/backup}  # default destination

if [ ! -d "$SRC" ]; then
    echo "error: no such directory: $SRC" >&2
    exit 1
fi
if [ ! -d "$DEST" ]; then
    echo "error: destination not found: $DEST" >&2
    exit 1
fi

BASE=$(basename "$SRC")
DATE=$(date +%F)
ARCHIVE="$DEST/${BASE}_${DATE}.tar.gz"

# archive the directory itself, without absolute paths
tar -czf "$ARCHIVE" -C "$(dirname "$SRC")" "$BASE"
echo "saved $ARCHIVE"
