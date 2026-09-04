#!/bin/bash
# AGAST #1332: subscript STORES (`g[i] = x` / `p[i] = x`) through typed
# pointers must write at the pointee's width and stride, for globals and
# locals alike. Companion to 90_global_ptr_index, which covers the LOAD side.
./subscript_store
