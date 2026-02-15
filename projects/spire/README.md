# Spire

*MVRSPT Web Framework for Ritz*

Spire is a web application framework built on the MVRSPT (Model-View-Repository-Service-Presenter-Tests) architecture pattern. It runs on Zeus and provides Django/Rails-like productivity with Ritz's performance and safety.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           SPIRE                                      │
│                    MVRSPT Web Framework                              │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────┐│
│  │  Model  │ │  View   │ │  Repo   │ │ Service │ │Presenter│ │Tests││
│  │  Data   │ │Templates│ │  Data   │ │Business │ │ Routes  │ │ TDD ││
│  │ Structs │ │  HTML   │ │ Access  │ │  Logic  │ │ Control │ │     ││
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────┘│
├─────────────────────────────────────────────────────────────────────┤
│                              ZEUS                                    │
│                    (App Server / Process Manager)                    │
├─────────────────────────────────────────────────────────────────────┤
│                             VALET                                    │
│                    (HTTP Server / Reverse Proxy)                     │
└─────────────────────────────────────────────────────────────────────┘
```

## The Six Layers (MVRSPT)

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| **M** - Model | `models/` | Pure data structs, no behavior |
| **V** - View | `views/` | Templates, HTML/JSON rendering |
| **R** - Repository | `repos/` | Data access abstraction (Mausoleum/Tome) |
| **S** - Service | `services/` | Business logic, workflows, rules |
| **P** - Presenter | `presenters/` | HTTP handlers, request/response |
| **T** - Tests | `tests/` | Unit + integration, mocks at every layer |

## Why MVRSPT?

Traditional MVC suffers from "fat model" syndrome where models accumulate business logic, data access, and validation. MVRSPT solves this by:

1. **Repository Layer** - Abstracts data access. Services don't know if data comes from Mausoleum, Tome, or a mock.
2. **Service Layer** - Contains all business logic. Testable without database.
3. **Clear Boundaries** - Each layer has one job. Easy to test, easy to maintain.

## Quick Example

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
    fn find_by_user(self: @TaskRepository, user_id: Uuid) -> Vec<Task>
        self.db.query()
            .kind("task")
            .where("user_id", user_id)
            .exec()

    fn create(self:& TaskRepository, task: Task) -> Result<Task, Error>
        self.db.insert(task)

// services/task_service.ritz — Business logic
struct TaskService
    repo: TaskRepository

impl TaskService
    fn create_task(self:& TaskService, user: User, title: StrView) -> Result<Task, Error>
        // Business rule: title must be meaningful
        if title.len() < 3
            return Err(ValidationError("Title too short"))

        // Business rule: max 100 pending tasks
        let pending = self.repo.count_pending(user.id)
        if pending >= 100
            return Err(LimitError("Too many pending tasks"))

        let task = Task {
            id: Uuid.new_v4(),
            title: String.from(title),
            completed: false,
            user_id: user.id,
        }

        self.repo.create(task)

// presenters/task_presenter.ritz — HTTP handlers
struct TaskPresenter
    service: TaskService

impl TaskPresenter
    [[route("POST", "/tasks")]]
    fn create(self:& TaskPresenter, req: Request) -> Response
        let form = req.parse_json::<CreateTaskForm>()?

        match self.service.create_task(req.user, form.title)
            Ok(task) => Response.json(task, status: 201)
            Err(ValidationError(msg)) => Response.bad_request(msg)
            Err(LimitError(msg)) => Response.conflict(msg)

// tests/task_service_test.ritz — Unit tests with mocks
[[test]]
fn test_title_validation()
    let mock_repo = MockTaskRepository.new()
    let service = TaskService { repo: mock_repo }

    let result = service.create_task(mock_user(), "ab")

    assert(result.is_err())
    assert(result.unwrap_err().message.contains("too short"))
```

## The Repository Trait

All repositories implement a common interface, enabling easy mocking:

```ritz
trait Repository<T>
    fn find(self: @Self, id: Uuid) -> Option<T>
    fn find_all(self: @Self, query: Query) -> Vec<T>
    fn create(self:& Self, item: T) -> Result<T, Error>
    fn update(self:& Self, item: T) -> Result<T, Error>
    fn delete(self:& Self, id: Uuid) -> Result<(), Error>

// Production: uses Mausoleum
struct MausoleumRepo<T> implements Repository<T>
    db: @Mausoleum

// Testing: in-memory mock
struct MockRepo<T> implements Repository<T>
    items: HashMap<Uuid, T>
    should_fail: bool
```

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

## Full Stack Integration

```
                    THE RITZ STACK

    ┌──────────────────────────────────────────┐
    │            YOUR APPLICATION              │
    ├──────────────────────────────────────────┤
    │               SPIRE                      │  ← You are here
    │   Model │ View │ Repo │ Service │ Present│
    ├──────────────────────────────────────────┤
    │               ZEUS                       │  ← App Server
    ├──────────────────────────────────────────┤
    │               VALET                      │  ← HTTP Server
    ├──────────────────────────────────────────┤
    │       MAUSOLEUM  │   TOME               │  ← Storage
    │      (Persist)   │  (Cache)              │
    ├──────────────────────────────────────────┤
    │        CRYPTOSEC │ SQUEEZE              │  ← Security/Compression
    ├──────────────────────────────────────────┤
    │            RITZ + RITZUNIT              │  ← Language + Testing
    └──────────────────────────────────────────┘
```

## Status

**Design Phase** — Architecture and patterns being defined.

## Dependencies

- `ritz` - Core compiler
- `ritzunit` - Testing framework
- `zeus` - App server (runtime)
- `mausoleum` - Persistent storage (optional)
- `tome` - In-memory cache (optional)

## License

MIT
