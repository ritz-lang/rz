# RERITZ Borrow Cleanup Proposal

## Problem

Kernel code that mutates structs behind pointers is noisy:

```ritz
(*table).fds[i].used = 1
(*table).fds[i].target_fd = i
```

This makes ownership intent harder to read and discourages idiomatic borrow-style APIs.

## Proposed Semantics

1. Mutable borrow parameters:
`fn fd_alloc(table:& FdTable) -> i32`

2. Field auto-deref on borrows/pointers:
`table.fds[i].used = 1`

3. Const borrow by default:
`fn fd_get(table: FdTable, fd: i32) -> Option<&FileDescriptor>`

4. Move only when explicit:
`fn adopt(desc:= FileDescriptor) -> i32`

## Desugaring Model

The compiler can lower these forms without changing backend layout:

- `table:& T` -> internal mutable pointer to `T`
- `table.field` where `table` is pointer/borrow -> `(*table).field`
- method receivers follow same rule (`self:& T`)

## Why This Helps Harland

- FD table and scheduler code become readable and auditable.
- Ownership boundaries become obvious at callsites.
- Fewer accidental aliasing bugs in syscall and process state code.

## Incremental Rollout

1. Parse + typecheck `:&`/`:=` in function params.
2. Add field auto-deref for pointer/borrow lvalues and rvalues.
3. Keep legacy pointer syntax valid for backward compatibility.
4. Gradually migrate kernel modules as they are touched.
