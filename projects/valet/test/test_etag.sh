#!/bin/bash
# Test ETag/If-None-Match caching

PORT=8712
SCRIPT_DIR="$(dirname "$0")"
cd "$SCRIPT_DIR/.."

# Create a test file
echo "ETag test content" > ./public/etag_test.txt

# Start server in background (using unique port to avoid conflicts)
./valet -p $PORT > /dev/null 2>&1 &
VALET_PID=$!
sleep 1

echo "=== Test 1: Get file and check for ETag header ==="
printf "GET /static/etag_test.txt HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n" | nc -q 2 localhost $PORT

echo ""
echo "=== Test 2: Request with matching If-None-Match (should get 304) ==="
# Get the ETag first
ETAG=$(printf "GET /static/etag_test.txt HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n" | nc -q 2 localhost $PORT | grep -i "^ETag:" | tr -d '\r' | awk '{print $2}')
echo "Using ETag: $ETAG"
if [ -n "$ETAG" ]; then
    printf "GET /static/etag_test.txt HTTP/1.1\r\nHost: localhost\r\nIf-None-Match: %s\r\nConnection: close\r\n\r\n" "$ETAG" | nc -q 2 localhost $PORT
else
    echo "ERROR: No ETag found in first response"
fi

echo ""
echo "=== Test 3: Request with non-matching If-None-Match (should get 200) ==="
printf "GET /static/etag_test.txt HTTP/1.1\r\nHost: localhost\r\nIf-None-Match: \"wrong-etag\"\r\nConnection: close\r\n\r\n" | nc -q 2 localhost $PORT

echo ""
echo "=== Test 4: Range request still includes ETag (should get 206) ==="
printf "GET /static/etag_test.txt HTTP/1.1\r\nHost: localhost\r\nRange: bytes=0-4\r\nConnection: close\r\n\r\n" | nc -q 2 localhost $PORT

# Cleanup
kill $VALET_PID 2>/dev/null
rm -f ./public/etag_test.txt
exit 0
