# Getting Started

Valet boots in a fraction of a second on a single core and serves at line rate.

## Run it

    ./valet -p 8080

## Routes

| Route             | Handler        |
| ----------------- | -------------- |
| `GET /`           | "Hello, World!" |
| `GET /hello`      | greeting       |
| `GET /json`       | JSON example   |
| `GET /users/:id`  | path param     |
| `GET /echo/:msg`  | echo           |
| `GET /docs/:slug` | this page      |
| `GET /static/*`   | static files   |
