#!/bin/bash
# Test range requests

PORT=8711
cd "$(dirname "$0")/.."

# Create a larger test file
echo "0123456789ABCDEFGHIJ" > ./public/range_test.txt

# Start server in background (using unique port to avoid conflicts)
./valet -p $PORT &
VALET_PID=$!
sleep 1

echo "=== Test 1: Full file (no Range) ==="
printf "GET /static/range_test.txt HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n" | nc -q 1 localhost $PORT

echo ""
echo "=== Test 2: Range bytes=0-4 ==="
printf "GET /static/range_test.txt HTTP/1.1\r\nHost: localhost\r\nRange: bytes=0-4\r\nConnection: close\r\n\r\n" | nc -q 1 localhost $PORT

echo ""
echo "=== Test 3: Range bytes=5-9 ==="
printf "GET /static/range_test.txt HTTP/1.1\r\nHost: localhost\r\nRange: bytes=5-9\r\nConnection: close\r\n\r\n" | nc -q 1 localhost $PORT

echo ""
echo "=== Test 4: Range bytes=10- (open-ended) ==="
printf "GET /static/range_test.txt HTTP/1.1\r\nHost: localhost\r\nRange: bytes=10-\r\nConnection: close\r\n\r\n" | nc -q 1 localhost $PORT

echo ""
echo "=== Test 5: Range bytes=-5 (suffix) ==="
printf "GET /static/range_test.txt HTTP/1.1\r\nHost: localhost\r\nRange: bytes=-5\r\nConnection: close\r\n\r\n" | nc -q 1 localhost $PORT

# Cleanup
kill $VALET_PID 2>/dev/null
rm -f ./public/range_test.txt
exit 0
