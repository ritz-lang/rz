# Spire

*MVRSPT Web Framework for Ritz. (Zerg Spire — hive-like productivity.)*

Full-stack web application framework with Django/Rails-like productivity and Ritz performance. Design phase.

---

## Overview

Spire is the application framework of the Ritz web stack. It implements the MVRSPT (Model-View-Repository-Service-Presenter-Tests) architecture — an evolution of MVC that explicitly separates data access, business logic, and HTTP concerns.

---

## Where It Fits

```
Your Application
        │
        ▼
     SPIRE (MVRSPT framework)
        │
        ▼
      ZEUS (app server)
        │
        ▼
     VALET (HTTP server)
        │
   ┌────┴────┐
Mausoleum  Tome
```

---

## The Six Layers (MVRSPT)

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| **M** Model | `models/` | Pure data structs. No methods. No database access. |
| **V** View | `views/` | HTML/JSON templates. No business logic. |
| **R** Repository | `repos/` | All database access. Swappable implementations. |
| **S** Service | `services/` | All business logic. No HTTP knowledge. |
| **P** Presenter | `presenters/` | HTTP handlers. Routes requests to services. |
| **T** Tests | `tests/` | Tests at every layer. Mocks at the repo boundary. |

### Why MVRSPT?

Traditional MVC creates "fat models" where models accumulate database access, business logic, validation, and presentation concerns. MVRSPT solves this:

1. **Repository layer** — Services never touch the database directly. Repositories are easily mocked in tests.
2. **Service layer** — Business logic is isolated from HTTP. Services are testable without a web server or database.
3. **Tests as first-class** — Tests are not an afterthought. Every layer has a test directory.

---

## Complete Example

```ritz
// models/task.ritz — Pure data
struct Task
    id: Uuid
    title: String
    completed: bool
    user_id: Uuid

// repos/task_repo.ritz — Data access
struct TaskRepository
    db: @Mausoleum

impl TaskRepository
    fn find_by_user(self, user_id: Uuid) -> Vec<Task>
        self.db.query()
            .kind("task")
            .where("user_id", user_id.to_string())
            .exec()
            .map(|doc| Task.from_doc(doc))
            .collect()

    fn create(self:& TaskRepository, task: Task) -> Result<Task, Error>
        let doc = self.db.insert(task.to_doc())?
        Ok(Task.from_doc(doc))

    fn count_pending(self, user_id: Uuid) -> i32
        self.db.query()
            .kind("task")
            .where("user_id", user_id.to_string())
            .where("completed", "false")
            .count()

// services/task_service.ritz — Business logic
struct TaskService
    repo: TaskRepository

impl TaskService
    fn create_task(self:& TaskService, user: User, title: StrView) -> Result<Task, Error>
        # Business rule: titles must be meaningful
        if title.len() < 3
            return Err(ValidationError("Title must be at least 3 characters"))

        # Business rule: limit active tasks
        let pending = self.repo.count_pending(user.id)
        if pending >= 100
            return Err(LimitError("Cannot have more than 100 pending tasks"))

        let task = Task {
            id: Uuid.new_v4(),
            title: String.from(title),
            completed: false,
            user_id: user.id,
        }
        self.repo.create(task)

    fn complete_task(self:& TaskService, user: User, task_id: Uuid) -> Result<Task, Error>
        let task = self.repo.find(task_id)
            .ok_or(NotFoundError("Task not found"))?

        # Business rule: only the owner can complete a task
        if task.user_id != user.id
            return Err(ForbiddenError("Not your task"))

        self.repo.update(Task { completed: true, ..task })

// presenters/task_presenter.ritz — HTTP handlers
struct TaskPresenter
    service: TaskService

impl TaskPresenter
    [[route("GET", "/tasks")]]
    fn index(self, req: Request) -> Response
        let tasks = self.service.repo.find_by_user(req.user.id)
        Response.json(tasks)

    [[route("POST", "/tasks")]]
    fn create(self:& TaskPresenter, req: Request) -> Response
        let form = req.parse_json::<CreateTaskForm>()?
        match self.service.create_task(req.user, form.title)
            Ok(task) => Response.json(task, status: 201)
            Err(ValidationError(msg)) => Response.bad_request(msg)
            Err(LimitError(msg)) => Response.conflict(msg)
            Err(e) => Response.internal_error(e)

    [[route("PUT", "/tasks/:id/complete")]]
    fn complete(self:& TaskPresenter, req: Request) -> Response
        let id = req.path_param("id")?.parse::<Uuid>()?
        match self.service.complete_task(req.user, id)
            Ok(task) => Response.json(task)
            Err(NotFoundError(msg)) => Response.not_found(msg)
            Err(ForbiddenError(msg)) => Response.forbidden(msg)

// tests/task_service_test.ritz — Unit tests with mock repo
[[test]]
fn test_create_task_validates_title() -> i32
    let service = TaskService { repo: MockTaskRepository.new() }
    let result = service.create_task(mock_user(), "ab")   # Too short
    assert result.is_err()
    assert result.unwrap_err().message.contains("3 characters")
    0

[[test]]
fn test_create_task_enforces_limit() -> i32
    let mock_repo = MockTaskRepository.new()
    mock_repo.pending_count = 100
    let service = TaskService { repo: mock_repo }
    let result = service.create_task(mock_user(), "Valid title")
    assert result.is_err()
    assert result.unwrap_err().message.contains("100 pending")
    0
```

---

## The Repository Trait

Repositories implement a common interface, making them swappable:

```ritz
trait Repository<T>
    fn find(self, id: Uuid) -> Option<T>
    fn find_all(self, query: Query) -> Vec<T>
    fn create(self:& Self, item: T) -> Result<T, Error>
    fn update(self:& Self, item: T) -> Result<T, Error>
    fn delete(self:& Self, id: Uuid) -> Result<(), Error>

# Production: uses Mausoleum
struct MausoleumRepo<T> implements Repository<T>
    db: @Mausoleum

# Testing: fully in-memory
struct MockRepo<T> implements Repository<T>
    items: HashMap<Uuid, T>
    should_fail: bool
```

---

## Project Structure

```
myapp/
├── models/
│   ├── user.ritz
│   └── task.ritz
├── views/
│   ├── layouts/
│   │   └── base.html
│   └── tasks/
│       ├── index.html
│       └── show.html
├── repos/
│   ├── user_repo.ritz
│   └── task_repo.ritz
├── services/
│   ├── user_service.ritz
│   └── task_service.ritz
├── presenters/
│   ├── user_presenter.ritz
│   └── task_presenter.ritz
├── tests/
│   ├── repos/
│   ├── services/
│   └── presenters/
├── config/
│   └── routes.ritz
└── main.ritz
```

---

## Current Status

Design phase. Architecture and patterns defined. Implementation pending Zeus and Valet stabilization.

---

## Related Projects

- [Zeus](zeus.md) — App server Spire runs on
- [Valet](valet.md) — HTTP server Spire uses via Zeus
- [Mausoleum](mausoleum.md) — Primary data store
- [Tome](tome.md) — Cache layer (optional)
- [Nexus](nexus.md) — Reference implementation built on Spire
- [Web Stack Subsystem](../subsystems/web-stack.md)
