---
name: architecture
description: "Specialist for cross-cutting architectural decisions. Covers system design, service boundaries, Clean Architecture, Hexagonal, DDD, CQRS, event-driven patterns, and decisions that span multiple domains."
---

# Architecture Skill

Cross-cutting architectural specialist. Handles system design, service/module boundaries, application architecture patterns, domain modeling, and decisions that span multiple components or layers.

## Discovery (Mandatory First Step)

Before making any architectural decision, analyze the project to determine:

- **Monorepo or Polyrepo**: Check for Turborepo, Nx, Lerna, or separate repositories.
- **Services**: Identify all existing services/modules and their communication patterns.
- **Database topology**: Check if services share a database or have isolated schemas.
- **Infrastructure**: Check for Docker Compose, Kubernetes, serverless config, CI/CD pipelines.
- **Existing contracts**: Look for proto files, OpenAPI/Swagger specs, GraphQL schemas, or shared type packages.

> Do NOT propose architectural changes without understanding the current architecture first.

## Skills to Activate

| Skill | When |
|---|---|
| `code-quality` | **Always** — any code contracts, schemas, or shared types written |
| `devops` | Docker, CI/CD pipelines, GitHub Actions, environment config, infrastructure |
| `conventional-commits` | Architectural commits, migration PRs, breaking-change changelogs |

> Read the matching skill's `SKILL.md` before producing any code artifacts.

## Core Responsibilities

- System design and architectural diagrams
- API contracts (REST, GraphQL, RPC, etc.)
- High-level database schema design
- Service and module boundary decisions
- Infrastructure and deployment (containers, CI/CD, cloud)
- Authentication and authorization flows
- Data flow, integration, and event patterns
- Domain modeling (DDD, aggregates, bounded contexts)

## Decision Principles

1. **Contracts First**: Always define the data contract (API schema, IDL, Swagger) before starting any implementation.
2. **Separation of Concerns**: Keep presentation logic completely separate from business logic.
3. **Single Source of Truth**: Don't duplicate code, constants, or type definitions across boundaries. Use shared libraries or code generation when possible.
4. **Security by Design**: Ensure security is considered at the architectural level, not as an afterthought.
5. **Minimize Blast Radius**: Prefer changes that affect the smallest number of components. Always assess impact before proposing changes.

## Application Architecture Patterns

### Overview

| Pattern                          | Description                                                                | Best For                                                   |
| -------------------------------- | -------------------------------------------------------------------------- | ---------------------------------------------------------- |
| **Layered (N-Tier)**             | Horizontal layers: Presentation → Business Logic → Data Access             | Traditional monoliths, CRUD-heavy apps                     |
| **Clean Architecture**           | Concentric layers: Entities → Use Cases → Interface Adapters → Frameworks  | Complex business rules, high testability                   |
| **Hexagonal (Ports & Adapters)** | Core logic surrounded by ports (interfaces) and adapters (implementations) | Projects needing easy swapping of DBs, APIs, or frameworks |
| **MVC / MVVM**                   | Model–View–Controller or Model–View–ViewModel separation                   | Web apps, mobile apps, frontend frameworks                 |

### Clean Architecture

Each component follows concentric layers with a strict dependency rule — source code dependencies ONLY point inward:

```
┌─────────────────────────────────────────┐
│  Frameworks & Drivers (outermost)       │
│  Web framework, ORM, external clients   │
├─────────────────────────────────────────┤
│  Interface Adapters                     │
│  Controllers, Repositories, DTOs,       │
│  Mappers, Presenters                    │
├─────────────────────────────────────────┤
│  Application (Use Cases)                │
│  Services — orchestrate domain logic    │
├─────────────────────────────────────────┤
│  Domain (innermost)                     │
│  Entities, Value Objects, Domain Rules  │
└─────────────────────────────────────────┘
```

**Layer Responsibilities**:

| Layer              | Contains                                    | Allowed To Import          |
| ------------------ | ------------------------------------------- | -------------------------- |
| Domain             | Entities, value objects, domain rules        | Nothing from outer layers  |
| Application        | Use case services, command/query handlers    | Domain, repository ports   |
| Interface Adapters | Controllers, resolvers, repos, DTOs, mappers | Application, Domain        |
| Frameworks         | Framework config, ORM schemas, client setup  | Everything                 |

### Hexagonal Architecture — Ports & Adapters

Think of each service or module as a hexagon. The core logic is at the center, surrounded by ports (interfaces) and adapters (implementations):

```
       [API Adapter]
            │
[Database] ──[Service Core]── [Cache]
            │
       [Event Adapter]
```

- **Ports**: Interfaces defined in the Application layer (e.g., `IUserRepository`, `IMailPort`).
- **Adapters**: Concrete implementations (e.g., `SqlUserRepository`, `SmtpMailAdapter`).
- **Rule**: The core service NEVER imports a concrete adapter — it imports the interface (port).

```typescript
// Port (Application layer)
interface IOrderRepository {
  findById(id: string): Promise<Order | null>;
  save(order: Order): Promise<Order>;
}

// Adapter (Frameworks layer — can import ORM)
class SqlOrderRepository implements IOrderRepository {
  constructor(private readonly db: DatabaseClient) {}
  // ... implementation
}

// Service depends on the port, not the adapter
class OrderService {
  constructor(private readonly repo: IOrderRepository) {}
}
```

## System Architecture Patterns

### Overview

| Pattern              | Description                                                    | Best For                                                                |
| -------------------- | -------------------------------------------------------------- | ----------------------------------------------------------------------- |
| **Monolith**         | Single deployable unit containing all functionality            | Small teams, early-stage products, low complexity                       |
| **Microservices**    | Independent services communicating over network protocols      | Large teams, independent scaling, complex domains                       |
| **Modular Monolith** | Single deployment but with strictly enforced module boundaries | Medium complexity — monolith benefits with microservice-like boundaries |
| **Event-Driven**     | Components communicate via events/messages (async)             | Real-time systems, audit trails, loose coupling                         |
| **CQRS**             | Separate models for reading (Query) and writing (Command)      | High-read/low-write systems, complex queries, event sourcing            |
| **Serverless**       | Functions deployed individually, triggered by events           | Bursty workloads, simple APIs, cost optimization                        |

### CQRS (Command Query Responsibility Segregation)

Separate the write model (commands that mutate state) from the read model (queries optimized for display):

```
Command side:                          Query side:
  validate → mutate → emit event         optimized read → return DTO
  (write DB, enforce rules)              (read DB/view, no side effects)
```

**Use when**: A service has complex reporting/dashboards separate from mutation operations, or reads far outnumber writes.
**Don't use when**: Simple CRUD — CQRS adds overhead not justified by simple domains.

### Event-Driven Architecture

Components communicate through domain events instead of direct calls.

**Within a service**: Emit events in-process for fire-and-forget side effects.
**Cross-service**: Use an event bus, message broker, or streaming platform.

**Sync vs Async decision**:

| Use Case                    | Pattern                              |
| --------------------------- | ------------------------------------ |
| Real-time response required | Synchronous call (RPC, REST)         |
| Side effects (audit, notify)| Domain events → async processing     |
| Long-running tasks          | Command queue                        |

**Event naming convention**: `<aggregate>.<past-tense-verb>`

```
order.created
user.deactivated
payment.failed
invoice.sent
```

## Domain-Driven Design (DDD)

Apply DDD within services or modules when the domain is complex.

### Key Concepts

| Concept              | Definition                                                        | Example                                          |
| -------------------- | ----------------------------------------------------------------- | ------------------------------------------------ |
| **Entity**           | Object with a unique identity that persists over time             | `User`, `Order`, `Product`                       |
| **Value Object**     | Immutable, no identity, defined by its attributes                 | `Email`, `Money`, `DateRange`                    |
| **Aggregate**        | Cluster of entities/VOs treated as a single unit                  | `Order` aggregate (Order + LineItems + Discounts) |
| **Aggregate Root**   | The entry point for operations on an aggregate                    | `Order` (access LineItems only through it)       |
| **Domain Service**   | Business logic that doesn't belong to a single entity             | `PricingCalculator`, `ConflictChecker`           |
| **Repository**       | Collection-like interface for persisting/retrieving aggregates    | `IOrderRepository`                               |
| **Domain Event**     | Something significant that happened in the domain                 | `OrderPlaced`, `UserDeactivated`                 |

### Aggregate Rules

- Access child entities ONLY through the aggregate root.
- One transaction = one aggregate. Cross-aggregate consistency should be eventual (via domain events).
- Keep aggregates small — prefer references (IDs) over nested objects.

### Domain Events

Events represent facts that already happened. They are named in past tense and carry enough data for consumers to act without calling back.

```typescript
interface DomainEvent {
  aggregateId: string;
  occurredAt: Date;
}

// Example
interface OrderPlaced extends DomainEvent {
  orderId: string;
  customerId: string;
  totalAmount: number;
}
```

## Communication Patterns

| Pattern                                   | When to Use                                                                     |
| ----------------------------------------- | ------------------------------------------------------------------------------- |
| **REST**                                  | Standard CRUD APIs, public-facing endpoints                                     |
| **GraphQL**                               | Flexible queries, multiple client types (web, mobile) with different data needs |
| **gRPC / RPC**                            | Inter-service communication, high performance, strong typing                    |
| **WebSockets**                            | Real-time bidirectional communication (chat, live updates)                      |
| **Message Queues** (RabbitMQ, Kafka, SQS) | Async processing, decoupling producers from consumers                           |

## Pattern Selection Decision Tree

```
Choosing an architecture:
├── Is this a new project or an existing one?
│   ├── EXISTING → Identify and follow the current pattern. Do NOT change it without explicit user approval.
│   └── NEW → Continue below.
├── How big is the team?
│   ├── 1–3 devs → Monolith or Modular Monolith
│   └── 4+ devs → Consider Microservices or Modular Monolith
├── Does each domain need to scale independently?
│   ├── YES → Microservices
│   └── NO → Modular Monolith
├── Is there heavy async processing?
│   ├── YES → Event-Driven with Message Queues
│   └── NO → Synchronous communication is fine
└── Are reads >> writes?
    ├── YES → Consider CQRS
    └── NO → Standard architecture is fine
```

> **CRITICAL**: Never propose migrating from a monolith to microservices unless the user explicitly asks for it. This is a high-risk transformation that requires deliberate planning.

## Service Boundary Decisions

### Should This Be a New Service/Module?

```
Does the new capability:
├── Have its own data domain (own tables/collections)?
│   ├── YES → Likely a new service/module
│   └── NO  → Extend an existing one
├── Have a different scaling profile?
│   ├── YES → New service (can scale independently)
│   └── NO  → Extend an existing one
├── Have different team ownership?
│   ├── YES → New service
│   └── NO  → Keep together
└── Does it just add a field or endpoint?
    └── YES → Extend the existing service
```

### Service Boundary Rules

A **new service** is justified when:
- It has its own data domain (own database/schema, not shared with other services)
- It scales independently from other services
- It has clear ownership by a team or developer
- It represents a distinct bounded context

A new **module within an existing service** is sufficient when:
- It shares data with the parent service
- It doesn't need independent scaling
- It's managed by the same team

### Anti-Patterns

1. **Shared database**: Service A must NEVER read Service B's database directly.
2. **Circular calls**: Service A calls B which calls A = deadlock risk. Redesign with events.
3. **Fat gateway**: The API gateway is a router/translator only — no business logic lives there.
4. **Missing DTOs at boundaries**: All inter-service inputs/outputs must have typed contracts.
5. **Mega-service**: If a service has 10+ modules and 20+ entities, consider splitting by bounded context.
6. **Synchronous chains**: A → B → C → D call chains create fragile dependencies. Prefer async events for non-critical paths.

## Full-Stack Feature Implementation Flow

When orchestrating a full-stack feature, follow this order:

1. **Architectural Design**: Define the database changes, API contracts, and affected services.
2. **Backend Implementation**: Build the database migrations, business logic, and expose the API endpoint.
3. **Frontend Integration**: Generate/write API clients, fetch data, and build the UI components.
4. **End-to-End Verification**: Test the full cycle from the user interface down to the database and back.
