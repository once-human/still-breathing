#!/bin/bash
# run.sh <dir> [VAR=val ...]: render one gen.py, one at a time. The renders are small (about 1000 x 1400 px, ~60 MB);
# waits until MINFREE MB (default 400) is available, and runs under a 1.2 GB address-space cap.
d=$1; shift
until [ "$(free -m | awk '/^Mem:/{print $7}')" -ge "${MINFREE:-400}" ]; do sleep 2; done
cd "$(dirname "$0")/../$d" && ulimit -v 1200000 && env "$@" python3 gen.py 2>&1 | tail -6
