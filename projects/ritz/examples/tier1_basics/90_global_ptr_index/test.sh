#!/bin/bash
# AGAST #1325/#1328: global pointer indexing must round-trip for every
# element width, in BOTH access forms — deref `*(g + i)` and subscript `g[i]`.
./global_ptr_index
