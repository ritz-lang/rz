#!/bin/bash
# Test echo: should echo arguments
test "$(./echo hello world)" = "hello world"
