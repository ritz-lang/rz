# Spire Framework Design Document

This document walks through the design of each Spire component using **Nexus** (the Ritz wiki) as our concrete example. We'll design each layer with real code examples before implementation.

## Architecture Overview

Spire follows **MVRSPT** (Model-View-Repository-Service-Presenter-Tests):

```
┌─────────────────────────────────────────────────────────────┐
│                        HTTP Request                          │
│                             │                                │
│                             ▼                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                     MIDDLEWARE                        │   │
│  │         (Logging, Auth, CORS, Rate Limiting)          │   │
│  └──────────────────────────────────────────────────────┘   │
│                             │                                │
│                             ▼                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                     PRESENTER                         │   │
│  │     (HTTP Handlers - parse request, call service,     │   │
│  │      render response)                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                             │                                │
│              ┌──────────────┼──────────────┐                │
│              ▼              ▼              ▼                │
│  ┌────────────────┐  ┌────────────┐  ┌────────────┐        │
│  │    SERVICE     │  │    VIEW    │  │    JSON    │        │
│  │  (Business     │  │ (Template  │  │ (Serialize │        │
│  │   Logic)       │  │  Rendering)│  │  Response) │        │
│  └────────────────┘  └────────────┘  └────────────┘        │
│           │                                                  │
│           ▼                                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    REPOSITORY                         │   │
│  │          (Data Access - Mausoleum, Tome)              │   │
│  └──────────────────────────────────────────────────────┘   │
│           │                                                  │
│           ▼                                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                      MODEL                            │   │
│  │              (Pure Data Structs)                      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Models - Pure Data Structs

Models are **pure data** with no behavior. They're the domain objects.

### Nexus Example: WikiPage

```ritz
# nexus/models/wiki_page.ritz

import spire.model { Uuid, Timestamp }

# A wiki page in Nexus
pub struct WikiPage
    id: Uuid
    slug: String               # URL-friendly identifier: "getting-started"
    title: String              # Display title: "Getting Started"
    content: String            # Markdown content
    parent_id: Option<Uuid>    # For hierarchy (None = top-level)
    author_id: Uuid
    version: i32               # For optimistic locking
    created_at: Timestamp
    updated_at: Timestamp

# Page link for backlinks/graph
pub struct PageLink
    source_id: Uuid            # Page containing the link
    target_id: Uuid            # Page being linked to
    link_text: String          # The anchor text used

# Page revision for history
pub struct PageRevision
    id: Uuid
    page_id: Uuid
    content: String
    author_id: Uuid
    message: String            # Commit message
    created_at: Timestamp
```

**Design Decision:** Models have no methods. All operations go through Services.

---

## 2. Repository - Data Access Layer

Repositories abstract data storage. They know HOW to store/retrieve data but not WHAT the business rules are.

### Design Questions:

1. **How do we handle different backends?** (Mausoleum for persistence, Tome for caching)
2. **How do we make repositories testable?** (Mock implementations)
3. **What's the query interface?**

### Proposed Design:

```ritz
# spire/repo/mod.ritz

# Error types for repository operations
pub enum RepoError
    NotFound(String)
    DuplicateKey(String)
    ConnectionFailed(String)
    QueryFailed(String)

# Result type alias
pub type RepoResult<T> = Result<T, RepoError>
```

### Nexus Example: WikiPageRepository

```ritz
# nexus/repos/wiki_page_repo.ritz

import spire.repo { RepoResult, RepoError }
import nexus.models { WikiPage }

# Repository trait for wiki pages
# Note: Until Ritz has trait objects (#122), we use concrete types
pub struct WikiPageRepository
    # Storage backend (Mausoleum connection)
    db: *Db
    # Optional cache (Tome)
    cache: Option<*Cache>

pub fn wiki_page_repo_new(db: *Db) -> WikiPageRepository
    var repo: WikiPageRepository
    repo.db = db
    repo.cache = None
    repo

pub fn wiki_page_repo_with_cache(db: *Db, cache: *Cache) -> WikiPageRepository
    var repo: WikiPageRepository
    repo.db = db
    repo.cache = Some(cache)
    repo

# CRUD Operations

pub fn repo_find_by_id(repo: *WikiPageRepository, id: *Uuid) -> Option<WikiPage>
    # 1. Check cache first
    match repo.cache
        Some(cache) =>
            match cache_get(cache, id)
                Some(page) => return Some(page)
                None => ()  # Fall through to DB
        None => ()

    # 2. Query database
    # (Mausoleum query syntax TBD)
    db_query_one(repo.db, "wiki_pages", id)

pub fn repo_find_by_slug(repo: *WikiPageRepository, slug: *StrView) -> Option<WikiPage>
    # Slugs are indexed, so this is efficient
    db_query_by_field(repo.db, "wiki_pages", "slug", slug)

pub fn repo_find_children(repo: *WikiPageRepository, parent_id: *Uuid) -> Vec<WikiPage>
    db_query_where(repo.db, "wiki_pages", "parent_id", parent_id)

pub fn repo_create(repo:& WikiPageRepository, page:& WikiPage) -> RepoResult<WikiPage>
    # Validate slug uniqueness
    match repo_find_by_slug(repo, &string_as_strview(&page.slug))
        Some(_) =>
            let msg: StrView = "Page with this slug already exists"
            Err(DuplicateKey(string_from_strview(&msg)))
        None =>
            let result = db_insert(repo.db, "wiki_pages", page)
            # Invalidate cache
            match repo.cache
                Some(cache) => cache_invalidate(cache, &page.id)
                None => ()
            result

pub fn repo_update(repo:& WikiPageRepository, page:& WikiPage) -> RepoResult<WikiPage>
    # Optimistic locking: check version
    let result = db_update_where(
        repo.db,
        "wiki_pages",
        &page.id,
        "version",
        page.version - 1  # Previous version
    )
    match repo.cache
        Some(cache) => cache_invalidate(cache, &page.id)
        None => ()
    result

pub fn repo_delete(repo:& WikiPageRepository, id: *Uuid) -> RepoResult<()>
    let result = db_delete(repo.db, "wiki_pages", id)
    match repo.cache
        Some(cache) => cache_invalidate(cache, id)
        None => ()
    result
```

### Mock Repository for Testing

```ritz
# nexus/repos/mock_wiki_page_repo.ritz

pub struct MockWikiPageRepository
    pages: Vec<WikiPage>
    next_error: Option<RepoError>

pub fn mock_wiki_page_repo_new() -> MockWikiPageRepository
    var repo: MockWikiPageRepository
    repo.pages = vec_new<WikiPage>()
    repo.next_error = None
    repo

# Set up the mock to return an error on next call
pub fn mock_set_error(repo:& MockWikiPageRepository, err: RepoError)
    repo.next_error = Some(err)

pub fn mock_find_by_id(repo: *MockWikiPageRepository, id: *Uuid) -> Option<WikiPage>
    var i: i64 = 0
    while i < vec_len<WikiPage>(&repo.pages)
        let page: *WikiPage = vec_get_ptr<WikiPage>(&repo.pages, i)
        if uuid_eq(&page.id, id) == 1
            return Some(*page)
        i += 1
    None

pub fn mock_create(repo:& MockWikiPageRepository, page:& WikiPage) -> RepoResult<WikiPage>
    # Check for programmed error
    match repo.next_error
        Some(err) =>
            repo.next_error = None
            Err(err)
        None =>
            var new_page: WikiPage = *page
            new_page.id = uuid_new_v4()
            new_page.created_at = timestamp_now()
            new_page.updated_at = timestamp_now()
            vec_push<WikiPage>(&repo.pages, new_page)
            Ok(new_page)
```

---

## 3. Service - Business Logic Layer

Services contain ALL business rules. They orchestrate between repositories and enforce domain constraints.

### Design Questions:

1. **How do services get their repositories?** (Constructor injection)
2. **What errors do services return?** (ServiceError enum)
3. **How do we handle transactions?** (Transaction context)

### Proposed Design:

```ritz
# spire/service/mod.ritz

pub enum ServiceError
    ValidationError(String)     # 400
    NotFoundError(String)       # 404
    UnauthorizedError(String)   # 401
    ForbiddenError(String)      # 403
    ConflictError(String)       # 409
    InternalError(String)       # 500

pub type ServiceResult<T> = Result<T, ServiceError>

# Convert repo error to service error
pub fn service_error_from_repo(err: RepoError) -> ServiceError
    match err
        NotFound(msg) => NotFoundError(msg)
        DuplicateKey(msg) => ConflictError(msg)
        _ => InternalError(string_from_strview(&"Database error"))
```

### Nexus Example: WikiService

```ritz
# nexus/services/wiki_service.ritz

import spire.service { ServiceResult, ServiceError, validation_error, not_found_error }
import nexus.models { WikiPage, PageRevision }
import nexus.repos { WikiPageRepository, PageRevisionRepository }

pub struct WikiService
    page_repo: *WikiPageRepository
    revision_repo: *PageRevisionRepository

pub fn wiki_service_new(
    page_repo: *WikiPageRepository,
    revision_repo: *PageRevisionRepository
) -> WikiService
    WikiService {
        page_repo: page_repo,
        revision_repo: revision_repo
    }

# ============================================================================
# Business Operations
# ============================================================================

# Create a new wiki page
pub fn service_create_page(
    svc:& WikiService,
    author_id: *Uuid,
    slug: *StrView,
    title: *StrView,
    content: *StrView,
    parent_id: Option<Uuid>
) -> ServiceResult<WikiPage>
    # === VALIDATION ===

    # Slug validation
    if slug.len < 1
        let msg: StrView = "Slug cannot be empty"
        return Err(validation_error(&msg))

    if slug.len > 100
        let msg: StrView = "Slug too long (max 100 chars)"
        return Err(validation_error(&msg))

    if validate_slug_format(slug) == 0
        let msg: StrView = "Slug must be lowercase alphanumeric with hyphens"
        return Err(validation_error(&msg))

    # Title validation
    if title.len < 1
        let msg: StrView = "Title cannot be empty"
        return Err(validation_error(&msg))

    if title.len > 200
        let msg: StrView = "Title too long (max 200 chars)"
        return Err(validation_error(&msg))

    # Parent validation (if specified, must exist)
    match parent_id
        Some(pid) =>
            match repo_find_by_id(svc.page_repo, &pid)
                None =>
                    let msg: StrView = "Parent page not found"
                    return Err(not_found_error(&msg))
                Some(_) => ()
        None => ()

    # === CREATE PAGE ===

    var page: WikiPage
    page.id = uuid_zero()  # Will be set by repo
    page.slug = string_from_strview(slug)
    page.title = string_from_strview(title)
    page.content = string_from_strview(content)
    page.parent_id = parent_id
    page.author_id = *author_id
    page.version = 1
    page.created_at = timestamp_zero()  # Will be set by repo
    page.updated_at = timestamp_zero()

    match repo_create(svc.page_repo, &page)
        Ok(created_page) => Ok(created_page)
        Err(repo_err) => Err(service_error_from_repo(&repo_err))

# Update an existing wiki page
pub fn service_update_page(
    svc:& WikiService,
    page_id: *Uuid,
    editor_id: *Uuid,
    title: Option<StrView>,
    content: Option<StrView>,
    message: *StrView
) -> ServiceResult<WikiPage>
    # Fetch existing page
    let existing = match repo_find_by_id(svc.page_repo, page_id)
        Some(p) => p
        None =>
            let msg: StrView = "Page not found"
            return Err(not_found_error(&msg))

    # === VALIDATION ===

    match title
        Some(t) =>
            if t.len < 1
                let msg: StrView = "Title cannot be empty"
                return Err(validation_error(&msg))
        None => ()

    # === SAVE REVISION (before update) ===

    var revision: PageRevision
    revision.id = uuid_zero()
    revision.page_id = *page_id
    revision.content = existing.content  # Save old content
    revision.author_id = existing.author_id
    revision.message = string_from_strview(message)
    revision.created_at = timestamp_zero()

    match repo_create_revision(svc.revision_repo, &revision)
        Ok(_) => ()
        Err(e) => return Err(service_error_from_repo(&e))

    # === UPDATE PAGE ===

    var updated: WikiPage = existing
    match title
        Some(t) => updated.title = string_from_strview(&t)
        None => ()
    match content
        Some(c) => updated.content = string_from_strview(&c)
        None => ()
    updated.author_id = *editor_id
    updated.version = updated.version + 1
    updated.updated_at = timestamp_now()

    match repo_update(svc.page_repo, &updated)
        Ok(p) => Ok(p)
        Err(e) => Err(service_error_from_repo(&e))

# Get page with children for navigation
pub fn service_get_page_with_nav(
    svc: *WikiService,
    slug: *StrView
) -> ServiceResult<PageWithNav>
    let page = match repo_find_by_slug(svc.page_repo, slug)
        Some(p) => p
        None =>
            let msg: StrView = "Page not found"
            return Err(not_found_error(&msg))

    let children = repo_find_children(svc.page_repo, &page.id)

    let breadcrumbs = build_breadcrumbs(svc, &page)

    Ok(PageWithNav {
        page: page,
        children: children,
        breadcrumbs: breadcrumbs
    })

# Helper: Build breadcrumb trail
fn build_breadcrumbs(svc: *WikiService, page: *WikiPage) -> Vec<BreadcrumbItem>
    var crumbs: Vec<BreadcrumbItem> = vec_new<BreadcrumbItem>()
    var current_id: Option<Uuid> = page.parent_id

    while true
        match current_id
            None => break
            Some(pid) =>
                match repo_find_by_id(svc.page_repo, &pid)
                    None => break
                    Some(parent) =>
                        var crumb: BreadcrumbItem
                        crumb.title = parent.title
                        crumb.slug = parent.slug
                        vec_push<BreadcrumbItem>(&crumbs, crumb)
                        current_id = parent.parent_id

    # Reverse to get root-first order
    vec_reverse<BreadcrumbItem>(&crumbs)
    crumbs

# Validate slug format: lowercase alphanumeric with hyphens
fn validate_slug_format(slug: *StrView) -> i32
    var i: i64 = 0
    while i < slug.len
        let c: u8 = *(slug.ptr + i)
        # a-z, 0-9, or hyphen
        let is_lower: i32 = (c >= 97 and c <= 122) as i32
        let is_digit: i32 = (c >= 48 and c <= 57) as i32
        let is_hyphen: i32 = (c == 45) as i32
        if is_lower == 0 and is_digit == 0 and is_hyphen == 0
            return 0
        i += 1
    1
```

---

## 4. Presenter - HTTP Handler Layer

Presenters handle HTTP concerns: parsing requests, calling services, rendering responses.

### Design Questions:

1. **How are presenters registered with routes?**
2. **How do presenters access services?** (Dependency injection via app state)
3. **How is content negotiation handled?** (Accept header → JSON or HTML)

### Proposed Design:

```ritz
# spire/presenter/mod.ritz

# Handler function signature
pub type Handler = fn(*Request, *AppState) -> Response

# App state holds all services (dependency injection)
pub struct AppState
    # Services
    wiki_service: *WikiService
    user_service: *UserService
    # Config
    config: *AppConfig
```

### Nexus Example: PagePresenter

```ritz
# nexus/presenters/page_presenter.ritz

import spire.http { Request, Response, response_ok, response_not_found }
import spire.http { response_created, response_bad_request }
import spire.presenter { AppState }
import spire.json { json_encode }
import spire.form { form_parse }
import nexus.views { render_page, render_page_edit, render_page_list }
import nexus.services { WikiService, service_get_page_with_nav }

# ============================================================================
# Route Registration
# ============================================================================

pub fn register_page_routes(router:& Router, state: *AppState)
    # Page routes
    router_get(router, "/wiki/:slug", page_show, state)
    router_get(router, "/wiki/:slug/edit", page_edit_form, state)
    router_post(router, "/wiki/:slug/edit", page_edit_submit, state)
    router_get(router, "/wiki/new", page_new_form, state)
    router_post(router, "/wiki/new", page_new_submit, state)

    # API routes (JSON)
    router_get(router, "/api/pages/:slug", api_page_get, state)
    router_post(router, "/api/pages", api_page_create, state)
    router_put(router, "/api/pages/:slug", api_page_update, state)

# ============================================================================
# HTML Handlers
# ============================================================================

# GET /wiki/:slug - Show a wiki page
fn page_show(req: *Request, state: *AppState) -> Response
    let slug = request_param(req, "slug")

    match service_get_page_with_nav(state.wiki_service, &slug)
        Ok(page_nav) =>
            # Render HTML
            let html = render_page(&page_nav)
            var resp = response_ok()
            response_html(&resp, &html)
            resp
        Err(err) =>
            handle_service_error(&err)

# GET /wiki/:slug/edit - Edit form
fn page_edit_form(req: *Request, state: *AppState) -> Response
    # Require authentication
    let user = match require_auth(req, state)
        Ok(u) => u
        Err(resp) => return resp

    let slug = request_param(req, "slug")

    match repo_find_by_slug(state.wiki_service.page_repo, &slug)
        Some(page) =>
            let html = render_page_edit(&page, None)  # No errors
            var resp = response_ok()
            response_html(&resp, &html)
            resp
        None =>
            response_not_found()

# POST /wiki/:slug/edit - Submit edit
fn page_edit_submit(req: *Request, state: *AppState) -> Response
    let user = match require_auth(req, state)
        Ok(u) => u
        Err(resp) => return resp

    let slug = request_param(req, "slug")

    # Parse form data
    let form = form_parse(req)
    let title = form_get(&form, "title")
    let content = form_get(&form, "content")
    let message = form_get_or(&form, "message", "Updated page")

    # Get page ID from slug
    let page = match repo_find_by_slug(state.wiki_service.page_repo, &slug)
        Some(p) => p
        None => return response_not_found()

    # Call service
    match service_update_page(
        state.wiki_service,
        &page.id,
        &user.id,
        Some(title),
        Some(content),
        &message
    )
        Ok(updated) =>
            # Redirect to view page
            let location = format_str("/wiki/{}", &updated.slug)
            response_redirect(&location)
        Err(ValidationError(msg)) =>
            # Re-render form with error
            let html = render_page_edit(&page, Some(&msg))
            var resp = response_bad_request()
            response_html(&resp, &html)
            resp
        Err(err) =>
            handle_service_error(&err)

# ============================================================================
# JSON API Handlers
# ============================================================================

# GET /api/pages/:slug
fn api_page_get(req: *Request, state: *AppState) -> Response
    let slug = request_param(req, "slug")

    match service_get_page_with_nav(state.wiki_service, &slug)
        Ok(page_nav) =>
            var resp = response_ok()
            let json = json_encode_page(&page_nav.page)
            response_json_str(&resp, &json)
            resp
        Err(err) =>
            handle_service_error_json(&err)

# POST /api/pages
fn api_page_create(req: *Request, state: *AppState) -> Response
    let user = match require_auth_api(req, state)
        Ok(u) => u
        Err(resp) => return resp

    # Parse JSON body
    let body = match json_decode_create_page(request_body_str(req))
        Ok(b) => b
        Err(e) =>
            let msg: StrView = "Invalid JSON"
            return response_error_bad_request(&msg)

    match service_create_page(
        state.wiki_service,
        &user.id,
        &body.slug,
        &body.title,
        &body.content,
        body.parent_id
    )
        Ok(page) =>
            var resp = response_created()
            let json = json_encode_page(&page)
            response_json_str(&resp, &json)
            resp
        Err(err) =>
            handle_service_error_json(&err)

# ============================================================================
# Helpers
# ============================================================================

fn require_auth(req: *Request, state: *AppState) -> Result<User, Response>
    # Check session cookie
    match get_session_user(req, state)
        Some(user) => Ok(user)
        None =>
            # Redirect to login
            let location: StrView = "/login"
            Err(response_redirect(&location))

fn require_auth_api(req: *Request, state: *AppState) -> Result<User, Response>
    # Check Authorization header
    match get_bearer_user(req, state)
        Some(user) => Ok(user)
        None =>
            let msg: StrView = "Unauthorized"
            Err(response_error_unauthorized(&msg))

fn handle_service_error(err: *ServiceError) -> Response
    match err
        NotFoundError(_) => response_not_found()
        ValidationError(msg) =>
            # For HTML, redirect to error page or show flash
            response_bad_request()
        ForbiddenError(_) =>
            response_forbidden()
        _ =>
            response_internal_error()

fn handle_service_error_json(err: *ServiceError) -> Response
    let msg = service_error_message(err)
    let code = service_error_status_code(err)
    response_json_error(status_from_code(code), &msg)
```

---

## 5. Middleware - Cross-Cutting Concerns

Middleware wraps handlers to add functionality like logging, auth, CORS, etc.

### Design Questions:

1. **How is middleware chained?** (Stack of functions)
2. **How does middleware pass data to handlers?** (Request context)
3. **Can middleware short-circuit?** (Return early response)

### Proposed Design:

```ritz
# spire/middleware/mod.ritz

# Middleware function signature:
# Takes a request, next handler, and returns response
# Can call next() or return early
pub type Middleware = fn(*Request, Handler, *AppState) -> Response

# Middleware chain
pub struct MiddlewareChain
    middlewares: Vec<Middleware>
    handler: Handler

pub fn chain_new(handler: Handler) -> MiddlewareChain
    var chain: MiddlewareChain
    chain.middlewares = vec_new<Middleware>()
    chain.handler = handler
    chain

pub fn chain_use(chain:& MiddlewareChain, mw: Middleware)
    vec_push<Middleware>(&chain.middlewares, mw)

pub fn chain_run(chain: *MiddlewareChain, req: *Request, state: *AppState) -> Response
    # Build the chain from inside out
    run_middleware_chain(&chain.middlewares, 0, chain.handler, req, state)

fn run_middleware_chain(
    middlewares: *Vec<Middleware>,
    index: i64,
    handler: Handler,
    req: *Request,
    state: *AppState
) -> Response
    if index >= vec_len<Middleware>(middlewares)
        # End of chain, call actual handler
        return handler(req, state)

    let mw = vec_get<Middleware>(middlewares, index)

    # Create "next" function (closure would be nice here...)
    # For now, we pass the chain info through
    mw(req, handler, state)
```

### Example Middlewares:

```ritz
# spire/middleware/logger.ritz

pub fn middleware_logger(req: *Request, next: Handler, state: *AppState) -> Response
    let start = timestamp_now()
    let method = method_to_str(&request_method(req))
    let path = request_path(req)

    # Call next
    let resp = next(req, state)

    let elapsed = timestamp_diff_ms(&start, &timestamp_now())
    let status = response_status_code(&resp)

    # Log: "GET /wiki/hello 200 12ms"
    log_info("{} {} {} {}ms", &method, &path, status, elapsed)

    resp

# spire/middleware/auth.ritz

pub fn middleware_require_auth(req: *Request, next: Handler, state: *AppState) -> Response
    match get_session_user(req, state)
        Some(user) =>
            # Attach user to request context
            request_set_context(req, "user", &user)
            next(req, state)
        None =>
            let msg: StrView = "Unauthorized"
            response_error_unauthorized(&msg)

# spire/middleware/cors.ritz

pub fn middleware_cors(req: *Request, next: Handler, state: *AppState) -> Response
    # Handle preflight
    if request_method(req) == OPTIONS
        var resp = response_ok()
        response_header(&resp, "Access-Control-Allow-Origin", "*")
        response_header(&resp, "Access-Control-Allow-Methods", "GET, POST, PUT, DELETE")
        response_header(&resp, "Access-Control-Allow-Headers", "Content-Type, Authorization")
        return resp

    # Call next and add CORS headers to response
    var resp = next(req, state)
    response_header(&resp, "Access-Control-Allow-Origin", "*")
    resp
```

---

## 6. JSON - Serialization/Deserialization

We need to encode/decode JSON for API responses and request bodies.

### Design Questions:

1. **Code generation or manual?** (Manual for now, codegen later with `@model`)
2. **Streaming or buffered?** (Buffered is simpler, streaming for large payloads)
3. **Error handling?** (Return Result with parse errors)

### Proposed Design:

```ritz
# spire/json/mod.ritz

pub enum JsonValue
    Null
    Bool(bool)
    Number(f64)
    String(String)
    Array(Vec<JsonValue>)
    Object(Vec<JsonKeyValue>)

pub struct JsonKeyValue
    key: String
    value: JsonValue

# Parse JSON string to JsonValue
pub fn json_parse(input: *StrView) -> Result<JsonValue, JsonError>
    # ... parser implementation

# Encode JsonValue to string
pub fn json_stringify(value: *JsonValue) -> String
    # ... encoder implementation

# Builder pattern for creating JSON
pub struct JsonBuilder
    value: JsonValue

pub fn json_object() -> JsonBuilder
    JsonBuilder { value: Object(vec_new<JsonKeyValue>()) }

pub fn json_builder_set(builder:& JsonBuilder, key: *StrView, value: JsonValue)
    match builder.value
        Object(pairs) =>
            var kv: JsonKeyValue
            kv.key = string_from_strview(key)
            kv.value = value
            vec_push<JsonKeyValue>(pairs, kv)
        _ => ()

pub fn json_builder_build(builder: *JsonBuilder) -> String
    json_stringify(&builder.value)
```

### Nexus Example: Encoding WikiPage

```ritz
# nexus/json/page_json.ritz

pub fn json_encode_page(page: *WikiPage) -> String
    var builder = json_object()

    json_builder_set(&builder, "id", String(uuid_to_str(&page.id)))
    json_builder_set(&builder, "slug", String(page.slug))
    json_builder_set(&builder, "title", String(page.title))
    json_builder_set(&builder, "content", String(page.content))

    match page.parent_id
        Some(pid) =>
            json_builder_set(&builder, "parent_id", String(uuid_to_str(&pid)))
        None =>
            json_builder_set(&builder, "parent_id", Null)

    json_builder_set(&builder, "version", Number(page.version as f64))
    json_builder_set(&builder, "created_at", String(timestamp_to_iso8601(&page.created_at)))
    json_builder_set(&builder, "updated_at", String(timestamp_to_iso8601(&page.updated_at)))

    json_builder_build(&builder)

# Decoding request body
pub fn json_decode_create_page(input: *StrView) -> Result<CreatePageRequest, JsonError>
    let value = json_parse(input)?

    match value
        Object(pairs) =>
            var req: CreatePageRequest
            req.slug = json_get_string(&pairs, "slug")?
            req.title = json_get_string(&pairs, "title")?
            req.content = json_get_string(&pairs, "content")?
            req.parent_id = json_get_string_opt(&pairs, "parent_id")
            Ok(req)
        _ =>
            Err(JsonError("Expected object"))
```

---

## 7. Form - HTML Form Parsing

Parse `application/x-www-form-urlencoded` request bodies.

### Proposed Design:

```ritz
# spire/form/mod.ritz

pub struct Form
    fields: Vec<FormField>

pub struct FormField
    name: String
    value: String

pub fn form_parse(req: *Request) -> Form
    let body = request_body_str(req)
    parse_urlencoded(&body)

pub fn form_get(form: *Form, name: *StrView) -> Option<StrView>
    var i: i64 = 0
    while i < vec_len<FormField>(&form.fields)
        let field = vec_get_ptr<FormField>(&form.fields, i)
        let field_name = string_as_strview(&field.name)
        if strview_eq(&field_name, name) == 1
            return Some(string_as_strview(&field.value))
        i += 1
    None

pub fn form_get_or(form: *Form, name: *StrView, default: *StrView) -> StrView
    match form_get(form, name)
        Some(v) => v
        None => *default

fn parse_urlencoded(input: *StrView) -> Form
    var form: Form
    form.fields = vec_new<FormField>()

    # Split by '&', then by '='
    # URL decode values
    # ... implementation

    form
```

---

## 8. View - Template Rendering

For HTML responses, we need a templating system.

### Design Questions:

1. **Compile-time templates?** (Preferred for performance)
2. **Runtime templates?** (More flexible, slower)
3. **DSL or builder pattern?** (Builder for now, DSL later)

### Proposed Design (Builder Pattern):

```ritz
# spire/view/mod.ritz

pub struct Html
    content: String

pub fn html_new() -> Html
    Html { content: string_new() }

pub fn html_raw(content: *StrView) -> Html
    Html { content: string_from_strview(content) }

# Element builder
pub struct Element
    tag: String
    attrs: Vec<Attr>
    children: Vec<Html>
    text: Option<String>

pub struct Attr
    name: String
    value: String

pub fn el(tag: *StrView) -> Element
    var elem: Element
    elem.tag = string_from_strview(tag)
    elem.attrs = vec_new<Attr>()
    elem.children = vec_new<Html>()
    elem.text = None
    elem

pub fn el_class(elem:& Element, class: *StrView)
    var attr: Attr
    attr.name = string_from_strview(&"class")
    attr.value = string_from_strview(class)
    vec_push<Attr>(&elem.attrs, attr)

pub fn el_attr(elem:& Element, name: *StrView, value: *StrView)
    var attr: Attr
    attr.name = string_from_strview(name)
    attr.value = string_from_strview(value)
    vec_push<Attr>(&elem.attrs, attr)

pub fn el_text(elem:& Element, text: *StrView)
    elem.text = Some(string_from_strview(text))

pub fn el_child(elem:& Element, child: Html)
    vec_push<Html>(&elem.children, child)

pub fn el_render(elem: *Element) -> Html
    var html = html_new()

    # Opening tag
    string_push_str(&html.content, "<")
    string_push_strview(&html.content, &string_as_strview(&elem.tag))

    # Attributes
    var i: i64 = 0
    while i < vec_len<Attr>(&elem.attrs)
        let attr = vec_get_ptr<Attr>(&elem.attrs, i)
        string_push_str(&html.content, " ")
        string_push_strview(&html.content, &string_as_strview(&attr.name))
        string_push_str(&html.content, "=\"")
        html_escape_into(&html.content, &string_as_strview(&attr.value))
        string_push_str(&html.content, "\"")
        i += 1

    string_push_str(&html.content, ">")

    # Text content
    match elem.text
        Some(t) =>
            html_escape_into(&html.content, &string_as_strview(&t))
        None => ()

    # Children
    i = 0
    while i < vec_len<Html>(&elem.children)
        let child = vec_get_ptr<Html>(&elem.children, i)
        string_push_strview(&html.content, &string_as_strview(&child.content))
        i += 1

    # Closing tag
    string_push_str(&html.content, "</")
    string_push_strview(&html.content, &string_as_strview(&elem.tag))
    string_push_str(&html.content, ">")

    html
```

### Nexus Example: Page Template

```ritz
# nexus/views/page_view.ritz

pub fn render_page(page_nav: *PageWithNav) -> StrView
    let page = &page_nav.page

    # Build the page
    var container = el("div")
    el_class(&container, "wiki-page")

    # Breadcrumbs
    var breadcrumbs = el("nav")
    el_class(&breadcrumbs, "breadcrumbs")
    var i: i64 = 0
    while i < vec_len<BreadcrumbItem>(&page_nav.breadcrumbs)
        let crumb = vec_get_ptr<BreadcrumbItem>(&page_nav.breadcrumbs, i)
        var link = el("a")
        el_attr(&link, "href", &format_str("/wiki/{}", &crumb.slug))
        el_text(&link, &string_as_strview(&crumb.title))
        el_child(&breadcrumbs, el_render(&link))
        # Add separator
        if i < vec_len<BreadcrumbItem>(&page_nav.breadcrumbs) - 1
            el_child(&breadcrumbs, html_raw(" / "))
        i += 1
    el_child(&container, el_render(&breadcrumbs))

    # Title
    var h1 = el("h1")
    el_text(&h1, &string_as_strview(&page.title))
    el_child(&container, el_render(&h1))

    # Content (rendered markdown)
    var content = el("div")
    el_class(&content, "content")
    let rendered_md = markdown_to_html(&string_as_strview(&page.content))
    el_child(&content, html_raw(&rendered_md))
    el_child(&container, el_render(&content))

    # Child pages
    if vec_len<WikiPage>(&page_nav.children) > 0
        var children = el("div")
        el_class(&children, "child-pages")
        var h2 = el("h2")
        el_text(&h2, "Sub-pages")
        el_child(&children, el_render(&h2))

        var ul = el("ul")
        i = 0
        while i < vec_len<WikiPage>(&page_nav.children)
            let child = vec_get_ptr<WikiPage>(&page_nav.children, i)
            var li = el("li")
            var link = el("a")
            el_attr(&link, "href", &format_str("/wiki/{}", &child.slug))
            el_text(&link, &string_as_strview(&child.title))
            el_child(&li, el_render(&link))
            el_child(&ul, el_render(&li))
            i += 1
        el_child(&children, el_render(&ul))
        el_child(&container, el_render(&children))

    # Wrap in layout
    layout(&string_as_strview(&page.title), el_render(&container))
```

---

## Summary: Implementation Order

Based on dependencies:

1. **JSON** - Needed by Presenter for API responses
2. **Form** - Needed by Presenter for form submission
3. **Service** - Business logic layer
4. **Middleware** - Cross-cutting concerns
5. **Presenter** - HTTP handlers (depends on Service, JSON, Form)
6. **View** - HTML rendering (optional, can use raw strings initially)

### File Structure:

```
lib/
├── mod.ritz              # Re-exports
├── http/                 # ✅ Done
├── model/                # ✅ Done
├── router/               # ✅ Done
├── repo/                 # ✅ Done (types, needs impl)
├── app/                  # ✅ Done
├── utils.ritz            # ✅ Done
├── service/
│   └── mod.ritz          # ServiceError, validation helpers
├── presenter/
│   └── mod.ritz          # Handler type, AppState
├── middleware/
│   ├── mod.ritz          # Chain, Middleware type
│   ├── logger.ritz
│   ├── auth.ritz
│   └── cors.ritz
├── json/
│   ├── mod.ritz          # JsonValue, parse, stringify
│   ├── parser.ritz
│   └── encoder.ritz
├── form/
│   └── mod.ritz          # Form parsing
└── view/
    ├── mod.ritz          # Html, Element builders
    └── escape.ritz       # HTML escaping
```

---

## Open Questions

1. **Closures (#121):** Many patterns (middleware, iterators) would be cleaner with closures. Should we wait or work around?

2. **Trait Objects (#122):** Repository abstraction would be cleaner with `dyn Repository`. For now, using concrete types.

3. **? Operator (#123):** Error propagation is verbose with explicit `match`. Should we implement first?

4. **Markdown Rendering:** Do we build our own or wrap an existing library?

5. **Database Connection Pooling:** How does Mausoleum handle concurrent connections?

---

## Next Steps

1. Review this design document
2. Identify any gaps or concerns
3. Prioritize implementation order
4. Start with JSON (foundation for APIs)
