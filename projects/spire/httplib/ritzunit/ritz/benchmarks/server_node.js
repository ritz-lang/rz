#!/usr/bin/env node
/**
 * Node.js HTTP server for benchmarking comparison.
 *
 * Run: node server_node.js
 * Test: curl http://localhost:8082/health
 */

const http = require('http');

const server = http.createServer((req, res) => {
    if (req.url === '/health' || req.url === '/') {
        res.writeHead(200, {
            'Content-Type': 'text/plain',
            'Content-Length': 2
        });
        res.end('OK');
    } else {
        res.writeHead(404, {
            'Content-Type': 'text/plain',
            'Content-Length': 9
        });
        res.end('Not Found');
    }
});

const PORT = 8082;
server.listen(PORT, () => {
    console.log(`Node.js server listening on port ${PORT}`);
});
