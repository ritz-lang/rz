#!/bin/bash
# Test nohup: should run command immune to hangups
set -e

# Clean up any previous test artifacts
rm -f nohup.out /tmp/nohup_test_output.txt

# Test 1: Basic execution with output redirection
# When stdout is not a tty (piped), output should go to stdout
echo "Test 1: Basic execution"
output=$(./nohup echo "hello from nohup" 2>&1)
if [[ "$output" == "hello from nohup" ]]; then
    echo "PASS: Basic execution works"
else
    echo "FAIL: Expected 'hello from nohup', got '$output'"
    exit 1
fi

# Test 2: Exit code passthrough
echo "Test 2: Exit code passthrough"
./nohup true
if [[ $? -eq 0 ]]; then
    echo "PASS: Exit code 0 passed through"
else
    echo "FAIL: Expected exit code 0"
    exit 1
fi

# Test 3: Non-zero exit code
echo "Test 3: Non-zero exit code"
./nohup false || code=$?
if [[ $code -eq 1 ]]; then
    echo "PASS: Non-zero exit code passed through"
else
    echo "FAIL: Expected exit code 1, got $code"
    exit 1
fi

# Test 4: Missing command error
echo "Test 4: Missing command error"
./nohup 2>/dev/null || code=$?
if [[ $code -eq 125 ]]; then
    echo "PASS: Missing command returns 125"
else
    echo "FAIL: Expected exit code 125, got $code"
    exit 1
fi

# Test 5: Command not found
echo "Test 5: Command not found"
./nohup /nonexistent/command 2>/dev/null || code=$?
if [[ $code -eq 127 ]]; then
    echo "PASS: Command not found returns 127"
else
    echo "FAIL: Expected exit code 127, got $code"
    exit 1
fi

echo "Test 6: Environment passthrough"

# Test 6: the child inherits our environment exactly — same entries, same
# order, '=' inside a value and empty values intact (AGAST #1480: the envp
# handed to execve comes from ritzlib.os.env's env_raw_envp).
expected=$(printf 'A=1\nB==2\nEMPTY=\nPATH=/usr/bin:/bin')
result=$(env -i A=1 B==2 EMPTY= PATH=/usr/bin:/bin ./nohup env 2>&1)
if [ "$result" = "$expected" ]; then
    echo "PASS: Environment passed to command"
else
    echo "FAIL: Expected '$expected', got '$result'"
    exit 1
fi

echo "All tests passed!"
