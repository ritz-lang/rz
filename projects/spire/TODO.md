# Spire TODO

## Current Status

### Compiling Modules (7)
- [x] `lib/http/headers.ritz` - HTTP headers collection
- [x] `lib/http/mod.ritz` - HTTP module (re-exports from http crate)
- [x] `lib/http/request.ritz` - HTTP request type
- [x] `lib/http/response.ritz` - HTTP response type
- [x] `lib/utils.ritz` - Shared utilities
- [x] `lib/repo/mod.ritz` - Repository pattern

### Blocked by Compiler Issues (12)
- [ ] `lib/mod.ritz` - Main module (import issues)
- [ ] `lib/router/mod.ritz` - Router (Vec<> double-pointer issue)
- [ ] `lib/model/*.ritz` - Models (ownership/String issues)
- [ ] `lib/app/mod.ritz` - App lifecycle (Vec<> issues)
- [ ] `lib/json/mod.ritz` - JSON builder (imports model)
- [ ] `lib/service/mod.ritz` - Service layer (parse errors)
- [ ] `lib/middleware/mod.ritz` - Middleware (string interpolation)
- [ ] `lib/form/mod.ritz` - Form parsing (parse errors)
- [ ] `lib/cli/mod.ritz` - CLI tool (string literals)
- [ ] `lib/test/mod.ritz` - Test utilities (parse errors)
- [ ] `lib/presenter/mod.ritz` - Presenter (parse errors)

### Dependencies
- `http` submodule added - provides METHOD_*, STATUS_* constants
- `ritz` submodule for compiler
- `ritzunit` submodule for tests

## Phase 1: Foundation

- [x] Project structure and build system
- [ ] Core traits (`Repository<T>`, `Service`, `Presenter`) - blocked by trait generics
- [x] Request/Response types (using http crate)
- [ ] Basic routing (`[[route]]` attribute) - partially working
- [ ] Integration with Zeus app server

## Phase 2: MVRSPT Core

### Models
- [ ] Model trait and derive macro
- [ ] Validation attributes
- [ ] Serialization (JSON, form data)

### Views
- [ ] Template engine (HTML templates)
- [ ] Layout inheritance
- [ ] Partials/components
- [ ] Asset pipeline (CSS, JS)

### Repositories
- [x] `Repository<T>` pattern defined (lib/repo/mod.ritz)
- [ ] `MausoleumRepository` implementation
- [ ] `TomeRepository` (cache) implementation
- [ ] `MockRepository` for testing
- [ ] Query builder integration

### Services
- [ ] Service base patterns
- [ ] Transaction support
- [ ] Error types (`ValidationError`, `BusinessRuleViolation`, etc.)

### Presenters
- [ ] Route registration
- [ ] Request parsing (JSON, form, query params)
- [x] Response builders (lib/http/response.ritz)
- [ ] Middleware support

### Tests
- [ ] Mock generation utilities
- [ ] Test fixtures
- [ ] Integration test helpers
- [ ] 231 tests written, blocked on ritzunit integration

## Phase 3: Features

- [ ] Authentication middleware
- [ ] Session management (via Tome)
- [ ] CSRF protection
- [ ] Rate limiting
- [ ] Logging/tracing

## Phase 4: CLI & Tooling

- [ ] `spire new <project>` scaffolding
- [ ] `spire generate model <name>`
- [ ] `spire generate presenter <name>`
- [ ] Development server with hot reload

## Known Compiler Issues Blocking Progress

1. **Vec<T> double-pointer** - `@@Vec<T>` creates double indirection issues
2. **String ownership** - Use of moved String values
3. **String interpolation** - `{` in string literals triggers interpolation
4. **Generic HashMap** - Only `HashMapI64` available, not `HashMap<K,V>`
5. **Option<T> confusion** - Different Option<T> types in same compilation unit

## Future

- [ ] WebSocket support
- [ ] GraphQL layer
- [ ] Admin dashboard generator
- [ ] Database migrations
