# Course Registration System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

This implementation plan delivers a high-concurrency Online Course Registration System (scale 3,000 concurrent students) following Clean Architecture and Monorepo conventions, optimized for a runnable demo on a 16GB RAM PC.

---

## File Structure & Component Mapping

```
course-registration-system/
├── docs/
│   ├── 01_yeu_cau_va_tai_trong/
│   │   ├── 1.1_mo_hinh_tai_trong.md
│   │   └── 1.2_chi_so_hieu_nang.md
│   ├── 02_phuong_an_ha_tang/
│   │   ├── 2.1_so_do_tong_the_ha_tang.md
│   │   ├── 2.2_cau_hinh_may_chu.md
│   │   └── 2.3_giai_phap_mo_rong.md
│   ├── 03_phan_tich_hoat_dong/
│   │   ├── 3.1_vong_doi_yeu_cau.md
│   │   ├── 3.2_mo_hinh_tien_trinh.md
│   │   └── 3.3_ket_noi_mang.md
│   ├── 04_thiet_ke_luu_tru/
│   │   ├── 4.1_mo_hinh_du_lieu_rdbms.md
│   │   ├── 4.2_chien_luoc_caching.md
│   │   └── 4.3_sao_chep_va_phan_vung.md
│   └── 05_giai_phap_chong_qua_tai/
│       ├── 5.1_hang_doi_va_dem_tai.md
│       ├── 5.2_kiem_soat_dong_thoi.md
│       └── 5.3_rate_limiting_va_chia_dot.md
│
├── infra/
│   ├── docker/
│   │   ├── nginx/
│   │   │   ├── nginx.conf
│   │   │   └── conf.d/default.conf
│   │   └── app/
│   │       └── Dockerfile
│   ├── terraform/
│   │   ├── main.tf
│   │   └── modules/ (compute, networking, database)
│   ├── k8s/
│   │   ├── ingress.yaml
│   │   ├── app-deployment.yaml
│   │   └── hpa.yaml
│   └── monitoring/
│       ├── prometheus.yml
│       └── grafana/dashboards/registration_dashboard.json
│
├── src/backend/
│   ├── core/
│   │   ├── domain/
│   │   │   ├── entities/
│   │   │   │   ├── student.py
│   │   │   │   ├── course_section.py
│   │   │   │   ├── registration.py
│   │   │   │   └── time_slot.py
│   │   │   └── exceptions/
│   │   │       └── registration_exceptions.py
│   │   └── usecases/
│   │       ├── register_course.py
│   │       ├── drop_course.py
│   │       └── view_curriculum.py
│   ├── adapters/
│   │   ├── in_bound/
│   │   │   ├── controllers/
│   │   │   │   ├── registration_controller.py
│   │   │   │   ├── catalog_controller.py
│   │   │   │   └── status_controller.py
│   │   │   └── consumers/
│   │   │       └── registration_consumer.py
│   │   └── out_bound/
│   │       ├── cache_gateway.py
│   │       ├── queue_gateway.py
│   │       └── persistence_gateway.py
│   ├── infrastructure/
│   │   ├── webserver/
│   │   │   ├── config.py
│   │   │   └── middlewares/
│   │   │       ├── auth_middleware.py
│   │   │       ├── idempotency_middleware.py
│   │   │       └── rate_limiter.py
│   │   ├── database/
│   │   │   ├── db_connection.py
│   │   │   ├── models.py
│   │   │   └── repositories/
│   │   │       └── registration_repository.py
│   │   ├── cache/
│   │   │   ├── redis_client.py
│   │   │   └── lua_scripts.py
│   │   └── messaging/
│   │       └── rabbitmq_client.py
│   ├── worker.py
│   ├── main.py
│   └── requirements.txt
│
├── src/frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── index.css
│       ├── types/registration.ts
│       ├── services/
│       │   ├── api.ts
│       │   └── pollingService.ts
│       └── components/
│           ├── Header.tsx
│           ├── CourseCatalog.tsx
│           ├── TimetableMatrix.tsx
│           ├── RegisteredList.tsx
│           ├── WaitingRoomModal.tsx
│           └── ExceptionModal.tsx
│
├── tests/
│   ├── unit/
│   │   ├── test_domain_rules.py
│   │   └── test_usecases.py
│   ├── integration/
│   │   ├── test_redis_lua.py
│   │   └── test_registration_flow.py
│   └── load_testing/
│       ├── tokens.csv
│       └── scenarios/
│           ├── race_condition_test.js
│           └── 3000_concurrent_users.js
│
├── scripts/
│   ├── init_db.py
│   ├── generate_tokens.py
│   ├── warmup_cache.py
│   ├── init_db.sh
│   ├── init_db.ps1
│   ├── seed_cache.sh
│   └── seed_cache.ps1
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## Phase 1: Technical & Architectural Documentation (`docs/`)

### Task 1: Comprehensive System Analysis & Sizing Documentation
- [ ] **Step 1:** Create `docs/01_yeu_cau_va_tai_trong/1.1_mo_hinh_tai_trong.md` and `1.2_chi_so_hieu_nang.md` documenting 3,000 CCU, Peak Read 3,500 QPS, Peak Write 1,000 TPS, and latency SLAs ($p95 \le 150\text{ms}$).
- [ ] **Step 2:** Create `docs/02_phuong_an_ha_tang/` (2.1 Network Topology, 2.2 Server Hardware Sizing, 2.3 Horizontal Scaling).
- [ ] **Step 3:** Create `docs/03_phan_tich_hoat_dong/` (3.1 Request Lifecycle, 3.2 Thread/Async Model, 3.3 Network Keep-Alive & Connection Pooling).
- [ ] **Step 4:** Create `docs/04_thiet_ke_luu_tru/` (4.1 RDBMS Schema & Indexes, 4.2 Multi-tier Caching, 4.3 Replication & CQRS).
- [ ] **Step 5:** Create `docs/05_giai_phap_chong_qua_tai/` (5.1 Message Queue buffering, 5.2 Concurrency CAS & Lua script, 5.3 Token Bucket Rate Limiting).
- [ ] **Step 6:** Commit documentation files: `git commit -m "docs: complete system analysis and architecture design papers"`.

---

## Phase 2: Backend Core (Domain & Use Cases with TDD)

### Task 2: Core Domain Entities & Business Exceptions
- [ ] **Step 1:** Write unit test `tests/unit/test_domain_rules.py` covering schedule conflict detection via 84-bit bitmap, credit limit verification, prerequisite course check, and capacity constraints.
- [ ] **Step 2:** Run `pytest tests/unit/test_domain_rules.py` to confirm tests fail before implementation.
- [ ] **Step 3:** Implement `src/backend/core/domain/entities/` (`time_slot.py`, `student.py`, `course_section.py`, `registration.py`).
- [ ] **Step 4:** Implement `src/backend/core/domain/exceptions/registration_exceptions.py` (`SectionFullException`, `ScheduleConflictException`, `PrerequisiteNotMetException`, `CreditLimitExceededException`).
- [ ] **Step 5:** Run tests to verify all domain entities and business rules pass.
- [ ] **Step 6:** Commit: `git commit -m "feat(backend): implement domain entities, bitmap schedule validation, and exceptions"`.

### Task 3: Use Cases Interactors
- [ ] **Step 1:** Write unit test `tests/unit/test_usecases.py` mocking outbound gateways (`ICacheGateway`, `IQueueGateway`, `IPersistenceGateway`).
- [ ] **Step 2:** Run tests to confirm failures.
- [ ] **Step 3:** Define outbound gateway interfaces in `src/backend/adapters/out_bound/`.
- [ ] **Step 4:** Implement `RegisterCourseUseCase`, `DropCourseUseCase`, and `ViewCurriculumUseCase` in `src/backend/core/usecases/`.
- [ ] **Step 5:** Run tests to confirm all use cases pass with mocks.
- [ ] **Step 6:** Commit: `git commit -m "feat(backend): implement clean architecture use case interactors"`.

---

## Phase 3: Infrastructure, Redis Lua Engine & Messaging

### Task 4: Redis In-Memory Lua Script Engine & Catalog Caching
- [ ] **Step 1:** Implement `src/backend/infrastructure/cache/lua_scripts.py` with:
  - Atomic validation & decrement script: Idempotency check $\rightarrow$ Prerequisite SET check $\rightarrow$ Schedule BITMAP `BITOP AND` check $\rightarrow$ Credit limit check $\rightarrow$ `DECR` slot.
  - Compensating rollback script: `INCR` slot, `SREM` enrolled, restore bitmap and credits.
- [ ] **Step 2:** Implement `src/backend/infrastructure/cache/redis_client.py` and `src/backend/adapters/out_bound/cache_gateway.py`.
- [ ] **Step 3:** Write integration test `tests/integration/test_redis_lua.py` using mock/embedded Redis or simulated client.
- [ ] **Step 4:** Run tests and ensure atomic operations work correctly.
- [ ] **Step 5:** Commit: `git commit -m "feat(backend): implement redis atomic lua scripts and cache gateway"`.

### Task 5: Database Layer & Async Repositories
- [ ] **Step 1:** Create `src/backend/infrastructure/database/models.py` (SQLAlchemy async models: `StudentModel`, `CourseModel`, `CourseSectionModel`, `RegistrationModel`).
- [ ] **Step 2:** Implement `src/backend/infrastructure/database/db_connection.py` with AsyncEngine and session maker.
- [ ] **Step 3:** Implement `src/backend/infrastructure/database/repositories/registration_repository.py` implementing `IPersistenceGateway`.
- [ ] **Step 4:** Commit: `git commit -m "feat(backend): implement async database models and registration repository"`.

### Task 6: Messaging & Background Worker with Compensating Rollback
- [ ] **Step 1:** Implement `src/backend/infrastructure/messaging/rabbitmq_client.py` (aio-pika connection, channel, exchanges, dead-letter queue `registration_dlq`).
- [ ] **Step 2:** Implement `src/backend/adapters/out_bound/queue_gateway.py`.
- [ ] **Step 3:** Implement `src/backend/adapters/in_bound/consumers/registration_consumer.py` and entrypoint `src/backend/worker.py`:
  - Fetch job from `registration_queue`.
  - Persist to PostgreSQL with retry backoff (3 attempts).
  - On permanent failure: trigger compensating rollback on Redis (`INCR` slot, remove student, update ticket to `FAILED`, route message to `registration_dlq`).
  - On success: mark ticket `ticket:{ticket_id}:status` as `CONFIRMED`.
- [ ] **Step 4:** Commit: `git commit -m "feat(backend): implement rabbitmq publisher, consumer worker, and compensating rollback"`.

---

## Phase 4: API Controllers, Middlewares & Main Application

### Task 7: Middlewares (In-Memory Auth, Idempotency, Rate Limiting)
- [ ] **Step 1:** Implement `src/backend/infrastructure/webserver/middlewares/auth_middleware.py`:
  - Verify HMAC-SHA256 signature in-memory ($O(1)$ CPU), avoid Bcrypt hashing during load testing.
- [ ] **Step 2:** Implement `src/backend/infrastructure/webserver/middlewares/idempotency_middleware.py`:
  - Intercept `X-Idempotency-Key`, enforce `SET idempotency:{key} "PROCESSING" EX 60 NX` via Redis.
- [ ] **Step 3:** Implement `src/backend/infrastructure/webserver/middlewares/rate_limiter.py` (Token Bucket / Redis Sliding Window).
- [ ] **Step 4:** Commit: `git commit -m "feat(backend): implement high-concurrency middlewares (in-memory auth, idempotency, rate limit)"`.

### Task 8: REST API Controllers & Main Wiring
- [ ] **Step 1:** Implement `src/backend/adapters/in_bound/controllers/catalog_controller.py`:
  - `GET /api/v1/sections`: Read cached JSON string directly from Redis `catalog:active_sections` in $< 1\text{ms}$.
- [ ] **Step 2:** Implement `src/backend/adapters/in_bound/controllers/registration_controller.py`:
  - `POST /api/v1/registrations`: Call `RegisterCourseUseCase` $\rightarrow$ Return `202 Accepted` with `ticket_id`.
  - `DELETE /api/v1/registrations/{registration_id}`: Call `DropCourseUseCase`.
- [ ] **Step 3:** Implement `src/backend/adapters/in_bound/controllers/status_controller.py`:
  - `GET /api/v1/registrations/status/{ticket_id}`: Read `ticket:{ticket_id}:status` from Redis (Controlled Short Polling endpoint).
  - Optional `GET /api/v1/registrations/stream/{ticket_id}`: SSE stream endpoint.
- [ ] **Step 4:** Implement `src/backend/main.py`: Wire Dependency Injection container, mount routers, configure CORS, and lifespan events.
- [ ] **Step 5:** Commit: `git commit -m "feat(backend): assemble fastAPI controllers and DI wiring in main.py"`.

---

## Phase 5: Seeding, Warm-up Scripts & Pre-warmed Tokens

### Task 9: Data Generation & Pre-warming Scripts
- [ ] **Step 1:** Create `scripts/init_db.py` (generate 3,000 students, 30 courses, 200 course sections in PostgreSQL).
- [ ] **Step 2:** Create `scripts/generate_tokens.py` (generate 3,000 pre-warmed JWT tokens into `tests/load_testing/tokens.csv`).
- [ ] **Step 3:** Create `scripts/warmup_cache.py`:
  - Query DB once and populate Redis with:
    * `catalog:active_sections` (full JSON array of 200 sections).
    * `section:{id}:slots` and `section:{id}:time_mask`.
    * `student:{id}:completed_courses`, `student:{id}:credits`, `student:{id}:registered_slots`.
- [ ] **Step 4:** Create shell scripts `scripts/init_db.sh`, `scripts/init_db.ps1`, `scripts/seed_cache.sh`, `scripts/seed_cache.ps1`.
- [ ] **Step 5:** Commit: `git commit -m "feat(scripts): implement database seeder, token pre-warmer, and cache warmup pipeline"`.

---

## Phase 6: Frontend Development (Stitch UI/UX Academic Registrar Grid)

### Task 10: Frontend Scaffolding & Design System
- [ ] **Step 1:** Initialize React 18 + Vite + TypeScript in `src/frontend/` with Tailwind CSS and Lucide icons.
- [ ] **Step 2:** Configure `tailwind.config.js` with Stitch tokens (Deep Academic Blue `#1E3A8A`, Royal Blue `#2563EB`, Emerald `#10B981`, Amber `#F59E0B`, Crimson `#EF4444`, font Inter with `tabular-nums`).
- [ ] **Step 3:** Define TypeScript models in `src/frontend/src/types/registration.ts`.
- [ ] **Step 4:** Implement API client & Idempotency generator in `src/frontend/src/services/api.ts`.
- [ ] **Step 5:** Implement `src/frontend/src/services/pollingService.ts` for controlled short polling (1s interval, max 3 retries).
- [ ] **Step 6:** Commit: `git commit -m "feat(frontend): setup vite react project and stitch design system tokens"`.

### Task 11: Core UI Components
- [ ] **Step 1:** Build `Header.tsx` (Institutional branding, student info badge, credit progress bar).
- [ ] **Step 2:** Build `CourseCatalog.tsx` with **Client-side Filtering & Search** (instant search by keyword, day of week, department; zero server CPU).
- [ ] **Step 3:** Build `TimetableMatrix.tsx` (Weekly timetable grid Monday–Saturday with period slots and conflict visualization).
- [ ] **Step 4:** Build `RegisteredList.tsx` (Summary of confirmed sections and drop actions).
- [ ] **Step 5:** Build `WaitingRoomModal.tsx` and `ExceptionModal.tsx` (Feedback modals for Section Full, Schedule Conflict, Prerequisite Warning, Success).
- [ ] **Step 6:** Assemble `App.tsx` coordinating state, catalog, cart, and registration flow.
- [ ] **Step 7:** Commit: `git commit -m "feat(frontend): implement course catalog with client-side filter, timetable grid, and status modals"`.

---

## Phase 7: Local Docker Compose & IaC Infrastructure

### Task 12: Production-Ready Local Docker Compose Stack
- [ ] **Step 1:** Implement `infra/docker/nginx/nginx.conf` (Rate limiting 15 req/s/IP, upstream load balancer for `fastapi-node-1` and `fastapi-node-2`, gzip, keep-alive 65s).
- [ ] **Step 2:** Implement `infra/docker/app/Dockerfile` (Lightweight Python 3.12-slim base image).
- [ ] **Step 3:** Implement root `docker-compose.yml`:
  - `nginx` (port 80 / 8080)
  - `fastapi-node-1` (port 8001 internal)
  - `fastapi-node-2` (port 8002 internal)
  - `redis` (port 6379, maxmemory 1gb, volatile-lru)
  - `rabbitmq` (port 5672, management 15672)
  - `postgres` (port 5432, db `course_reg`)
  - `worker` (consumes `registration_queue`)
- [ ] **Step 4:** Commit: `git commit -m "feat(infra): create 7-service docker-compose stack optimized for 16GB RAM laptop demo"`.

### Task 13: Academic IaC & Monitoring Manifests
- [ ] **Step 1:** Create Terraform modules in `infra/terraform/` (`networking`, `compute`, `database`) for academic report completeness.
- [ ] **Step 2:** Create Kubernetes manifests in `infra/k8s/` (`ingress.yaml`, `app-deployment.yaml`, `hpa.yaml`).
- [ ] **Step 3:** Create Prometheus & Grafana dashboard configurations in `infra/monitoring/`.
- [ ] **Step 4:** Commit: `git commit -m "feat(infra): create academic terraform, k8s manifests, and grafana dashboards"`.

---

## Phase 8: Load Testing (k6) & Verification

### Task 14: k6 Load Test Scenarios
- [ ] **Step 1:** Implement `tests/load_testing/scenarios/race_condition_test.js`:
  - 500 VUs simultaneously sending registration requests for 1 section with exactly 30 slots.
  - Verify exactly 30 receive 200/202 confirmation, 470 receive 409 conflict.
  - Assert zero overselling in Redis and DB.
- [ ] **Step 2:** Implement `tests/load_testing/scenarios/3000_concurrent_users.js`:
  - 3,000 VUs over 5 minutes with pre-warmed tokens.
  - Assert $p95 \le 150\text{ms}$ response times and error rate $\le 0.01\%$.
- [ ] **Step 3:** Commit: `git commit -m "feat(tests): implement k6 load testing scenarios for race condition and 3000 CCU"`.

### Task 15: Root Documentation & Run Verification
- [ ] **Step 1:** Create comprehensive `README.md` with step-by-step instructions:
  - Prerequisites (Docker, Python 3.12, Node.js).
  - One-command setup (`docker compose up -d`).
  - Seeding & Cache Warmup (`python scripts/init_db.py`, `python scripts/warmup_cache.py`).
  - Running k6 load tests (`k6 run tests/load_testing/scenarios/race_condition_test.js`).
  - Frontend development & demo instructions.
- [ ] **Step 2:** Create root `.gitignore` ignoring virtualenvs, node_modules, logs, and build artifacts.
- [ ] **Step 3:** Final verification: run test suite and verify clean git status.
- [ ] **Step 4:** Commit: `git commit -m "docs: finalize project README with setup instructions and architecture guide"`.
