# Spire

MVRSPT web application framework for Ritz - Django/Rails-style productivity built on Zeus and Valet.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

## Overview

Spire is the web application framework layer of the Ritz ecosystem. It implements the MVRSPT (Model-View-Repository-Service-Presenter-Tests) architecture pattern, which solves the "fat model" problem of traditional MVC by introducing explicit Repository and Service layers.

Spire runs on Zeus (process isolation) which runs on Valet (HTTP server), providing a complete application framework from HTTP parsing to database persistence. It integrates with Mausoleum for persistent document storage and Tome for in-memory caching. The framework is designed for test-driven development, with mocking support at every layer.

The primary reference implementation built on Spire is Nexus, the Ritz knowledge base wiki.

## Features

- MVRSPT architecture with clean separation of concerns
- Repository pattern abstracts data access (swap Mausoleum for mock in tests)
- Service layer for business logic - fully testable without a database
- Presenter layer handles HTTP request/response routing
- Template engine integration for HTML rendering
- JSON API support
- Mock repositories for unit testing without database
- Route declaration via attributes
- Built-in test utilities for all layers

## Installation

```bash
# As a dependency in ritz.toml:
# [dependencies]
# spire = { path = "../spire" }

# Build from source
export RITZ_PATH=/path/to/ritz
./ritz build .
```

## Usage

```ritz
# models/task.ritz - Pure data structures
struct Task
    id: Uuid
    title: String
    completed: bool
    user_id: Uuid
```

```ritz
# services/task_service.ritz - Business logic
struct TaskService
    repo: TaskRepository

impl TaskService
    fn create_task(self: *TaskService, user: User, title: *u8) -> Result<Task, Error>
        if strlen(title) < 3
            return Err(ValidationError("Title too short"))
        let task = Task { id: uuid_new(), title: title, completed: false, user_id: user.id }
        self.repo.create(task)
```

```ritz
# presenters/task_presenter.ritz - HTTP handlers
struct TaskPresenter
    service: TaskService

impl TaskPresenter
    [[route("POST", "/tasks")]]
    fn create(self: *TaskPresenter, req: *Request) -> Response
        let form = req.parse_json()
        match self.service.create_task(req.user, form.title)
            Ok(task) => Response.json(task, 201)
            Err(e) => Response.bad_request(e.message)
```

```ritz
# tests/task_service_test.ritz - Unit tests with mocks
@test
fn test_title_too_short() -> i32
    let repo = MockTaskRepository.new()
    let service = TaskService { repo: repo }
    let result = service.create_task(mock_user(), "ab")
    if result.is_ok()
        return 1  # FAIL - should have rejected short title
    return 0
```

## Dependencies

- `ritzlib` - Standard library
- `http` - HTTP protocol types (via ritz.toml)
- `mausoleum` - Document storage (optional, for production repositories)
- `tome` - In-memory cache (optional)

## Status

**Alpha** - Architecture and patterns are designed. Core routing, request/response handling, and repository traits are being implemented with TDD. Full Mausoleum and Tome integration is planned once those libraries stabilize.

## License

MIT License - see LICENSE file
