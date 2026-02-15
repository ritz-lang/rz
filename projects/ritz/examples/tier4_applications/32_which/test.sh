#!/bin/bash
# Test which: should find executables in PATH
./which ls | grep -q /bin/ls || ./which ls | grep -q /usr/bin/ls
