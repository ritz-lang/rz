# Nexus TODO

## Phase 1: Foundation

- [ ] Project structure
- [ ] Basic Spire application setup
- [ ] Mausoleum schema for wiki pages
- [ ] Development environment (Docker Compose)

## Phase 2: Core Wiki

### Data Model
- [ ] WikiPage model
- [ ] PageLink model (graph edges)
- [ ] User/Author model
- [ ] Version history model

### Repository Layer
- [ ] WikiPageRepository
- [ ] PageLinkRepository
- [ ] SearchRepository

### Service Layer
- [ ] WikiService (CRUD + business rules)
- [ ] SearchService (full-text search)
- [ ] VersionService (history, diff, rollback)

### Presenter Layer
- [ ] PagePresenter (view, edit, create)
- [ ] SearchPresenter
- [ ] HistoryPresenter

### Views
- [ ] Base layout
- [ ] Page view template
- [ ] Page edit template
- [ ] Search results template
- [ ] History/diff template

## Phase 3: Content

### Language Documentation
- [ ] Syntax reference
- [ ] Type system
- [ ] Ownership & borrowing
- [ ] Async/await
- [ ] Error handling

### Standard Library
- [ ] Auto-generate from ritzlib source
- [ ] Module index
- [ ] Function signatures
- [ ] Examples

### Ecosystem Guides
- [ ] Valet (HTTP server)
- [ ] Mausoleum (database)
- [ ] Tome (cache)
- [ ] Spire (framework)
- [ ] Zeus (app server)
- [ ] Squeeze (compression)
- [ ] Cryptosec (crypto)

### Tutorials
- [ ] Hello World
- [ ] Building a web app
- [ ] Database operations
- [ ] Testing guide

## Phase 4: Features

- [ ] Markdown rendering with Ritz syntax highlighting
- [ ] Live code examples (compile & run)
- [ ] Full-text search
- [ ] Backlinks (bidirectional)
- [ ] Table of contents generation
- [ ] API documentation generator

## Phase 5: Deployment

- [ ] Docker Compose configuration
- [ ] Single-binary build
- [ ] TLS/HTTPS setup
- [ ] Systemd units (alternative)
- [ ] Backup/restore scripts

## Future

- [ ] User accounts & permissions
- [ ] Edit history & attribution
- [ ] Comments/discussion
- [ ] RSS feed for changes
- [ ] Export to static HTML
