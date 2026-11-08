# Observable Registration Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nâng cấp ứng dụng hiện có thành lab đăng ký đúng nghiệp vụ, benchmark đối chứng và giám sát trực tiếp có thể trình diễn lặp lại.

**Architecture:** Giữ React/FastAPI và hai backend. Dùng PostgreSQL làm nguồn dữ liệu bền vững, Redis Lua giữ chỗ với ticket ownership, RabbitMQ chuyển job; có chế độ PostgreSQL đồng bộ đối chứng. Giữ polling và cung cấp recovery có thể gọi thủ công cho lab.

**Tech Stack:** Python 3.12, React 18/TypeScript, PostgreSQL 16, Redis 7, RabbitMQ, Docker Compose, k6, Prometheus, Grafana, RedisInsight.

**Spec:** `docs/superpowers/specs/2026-11-07-observable-registration-lab-design.md` (đã duyệt).

## Global Constraints

- Windows/Docker Desktop; giữ hai backend, không thêm cloud/HA/SSO/WebSocket/SSE/batch insert.
- Flash: 500 VUs × 6 iterations, 3.000 danh tính hợp lệ, lớp 60 chỗ; sustained là kịch bản riêng đến 3.000 VUs.
- HTTP 202 là tiếp nhận, CONFIRMED chỉ sau DB commit. Hết timeout không phải thành công.
- Không ghi số liệu chưa đo, không làm chậm baseline có chủ ý, không reset dữ liệu ngoài benchmark.
- Benchmark hai chế độ tuần tự, cùng giới hạn tài nguyên và monitoring; ba lượt mỗi chế độ sau warmup, luân phiên thứ tự.
- Dữ liệu lịch truyền dưới dạng `time_slots: list[int]` có phần tử 0..83, không dùng số 84-bit trên JavaScript/Lua.
- Review/test trước commit từng task; không staging file ngoài phạm vi. Không tự xóa volumes.
- Không cần hỏi lại các lựa chọn kỹ thuật nhỏ; dừng chỉ khi có thay đổi lớn về phạm vi hoặc thao tác phá hủy dữ liệu chưa được cho phép.

## Review Focus

1. Publish timeout sau khi broker đã nhận: giữ PENDING, recovery/redelivery không đăng ký hai lần (Task 3).
2. Worker chết sau commit trước cập nhật Redis: đối soát DB trước rollback và tiếp tục phần còn thiếu (Tasks 3–4).
3. Hủy rồi đăng ký lại trong khi message cũ đến muộn: ticket cũ không đổi vòng đăng ký mới (Task 4).
4. Reset benchmark lúc còn job unacked: từ chối reset và không ghi chéo generation (Task 8).
5. Nhiều sinh viên cùng IP, refresh trang lúc đang pending và mất nguồn metrics: không gộp tải sai, không báo thành công hoặc số 0 giả (Tasks 6–8).

## File map và hợp đồng chung

- `core/domain/entities/time_slot.py`: chuyển lịch thành chỉ số tiết; giữ compute_mask chỉ nếu test cũ cần, không dùng cho luồng mới.
- `infrastructure/database/models.py`, `repositories/registration_repository.py`: trạng thái, khóa, dữ liệu học tập và phiên bản ticket.
- New `core/domain/entities/registration_context.py`: dataclass `RegistrationContext(student_id: str, section_id: str, semester_id: str, credits: int, max_credits: int, prerequisite_course_code: str | None, time_slots: list[int], run_id: str | None, generation: int)`.
- New `core/domain/entities/operation.py`: dataclass `Operation(ticket_id: str, student_id: str, section_id: str, kind: str, status: str, generation: int, reason: str = '')`. kind REGISTER/DROP; status PENDING/CONFIRMED/FAILED/CANCEL_PENDING/CANCELLED.
- `adapters/out_bound/*.py`: typed contracts; API serialization uses dicts at controller boundary only.
- New `infrastructure/database/repositories/context_repository.py`: `load_registration_context(student_id: str, section_id: str) -> RegistrationContext`; authoritative DB source, cache populated from it.
- New `infrastructure/database/repositories/operation_repository.py`: DB transactions for idempotency and durable operation state; schema migration is additive.
- New `core/usecases/recover_operations.py`, `adapters/in_bound/consumers/drop_consumer.py`: recovery and cancel job processing.
- New `infrastructure/observability/metrics.py`: metric definitions, middleware and worker exposition.
- New `scripts/benchmark.py`, `scripts/lab.ps1`, `scripts/collect_container_metrics.ps1`: benchmark lifecycle, operator commands and Docker stats fallback.
- New `infra/docker/frontend/Dockerfile`, compose lab/test overlays, exporters and Grafana provisioning: reproducible environment.
- New `tests/real_integration/`: tests against dedicated test services; opt-in flag `RUN_REAL_INTEGRATION=1`, never production/demo database.

## Task 1: Exact schedule and authoritative academic data

**Files:** Modify `time_slot.py`, `models.py`, `registration_repository.py`, `scripts/init_db.py`, `scripts/warmup_cache.py`; create context/operation dataclasses, context_repository.py, `scripts/migrate_lab.py`, `tests/unit/test_registration_context.py`.

**Interfaces:** `TimeSlot.period_indices() -> list[int]`; `load_registration_context(student_id, section_id) -> RegistrationContext`. Add completed-course rows and semester-scoped student academic state in DB. Use `Operation` consistently in later tasks.

- [ ] Write tests: Sunday periods 10..12 returns `[81,82,83]`; invalid day/period raises; context contains real prerequisite code; missing student/class or closed semester rejects with stable error_code.
- [ ] Run `.venv\Scripts\python.exe -m unittest tests.unit.test_registration_context -v`; confirm assertions fail before implementation.
- [ ] Implement schedule/context/model changes. Additive migration runs explicitly, never drop_all; derive exact periods from day/start/end rather than rounded legacy time_mask. Seed completed courses once in DB. Cache warmup reads DB registrations/credits instead of recreating empty registrations.
- [ ] Run unit tests and DB migration on a fresh dedicated test DB plus a seeded old-schema fixture; assert existing registrations survive and warmup preserves occupied slots.
- [ ] Commit task files: `feat: add authoritative registration context and exact schedules`.

## Task 2: Identity, operation ownership and stable API contracts

**Files:** Modify config.py, main.py, auth_middleware.py, controllers `registration_controller.py`, `status_controller.py`, `demo_controller.py`; create `tests/integration/test_api_security.py`, update token generation script.

**Interfaces:** `POST /api/v1/registrations` accepts `{section_id}` and X-Idempotency-Key, returns Operation with status and registration_id when known. `GET /api/v1/registrations/status/{ticket_id}` checks JWT owner. `DELETE /api/v1/registrations/{registration_id}` checks owner and returns cancel Operation. Errors use `{error_code, detail, ticket_id?}`. LAB_MODE defaults false; REGISTRATION_MODE is postgres or redis_queue, fixed at startup.

- [ ] Write failing tests: forged student_id rejected; supplied credits/prerequisite cannot change server context; another student's ticket/list/cancel forbidden; demo token/reset APIs unavailable outside LAB_MODE.
- [ ] Run `.venv\Scripts\python.exe -m unittest tests.integration.test_api_security -v` and confirm failing expectations.
- [ ] Implement JWT-only identity for normal endpoints, lab-only token issuance for seeded identities, validate existing student, update routes and clear API contracts. Preserve no unsigned header bypass in normal mode.
- [ ] Run API security and existing API tests with updated fixtures; verify public health/readiness and protected metrics exposure policy explicitly.
- [ ] Commit: `feat: enforce registration identity and operation ownership`.

## Task 3: Atomic reservations, retries and registration worker recovery

**Files:** Modify cache_gateway.py, redis_cache_gateway.py, lua_scripts.py, register_course.py, idempotency_middleware.py, rabbitmq_client.py, registration_consumer.py; create operation_repository.py, recover_operations.py, `scripts/recover_operations.py`, `tests/unit/test_operation_lifecycle.py`, `tests/real_integration/test_reservation_lifecycle.py`.

**Interfaces:** Cache `reserve(context: RegistrationContext, ticket_id: str, idempotency_key: str, payload_hash: str) -> Operation`; `release(context, ticket_id: str) -> bool`; `get_operation(ticket_id: str) -> Operation | None`. DB `confirm_registration(context, ticket_id: str) -> Operation`; `get_operation(ticket_id) -> Operation | None`. `recover_pending(older_than_seconds: int, limit: int) -> dict[str,int]` reconciles DB then republishes only pending jobs.

- [ ] Write tests: sixty reservations from concurrent valid users never exceed capacity; repeated key returns same ticket; changed payload returns conflict; Sunday overlapping slots reject; unrelated weekend slots succeed; release twice changes slots once.
- [ ] Add fault tests: publisher raises before/after broker acceptance, consumer redelivery, DB commit succeeds then Redis update fails; assert one registration, no erroneous release and recoverable pending state.
- [ ] Run unit and opt-in real integration cases to establish failures.
- [ ] Implement atomic Lua reservation + PENDING metadata + index, ticket-owned enrolled hash and set of occupied periods, no early expiry of unresolved operations. Terminal ticket retention configurable and documented; recovery is bounded. Redis failures fail closed. Explicit publisher confirms, durable messages, bounded retries/DLQ. DB transactions lock student state and section consistently and check operation version. Scope idempotency by identity/operation/hash; remove contradictory middleware-only PROCESSING behavior.
- [ ] Run unit/API suite and real Redis/RabbitMQ/Postgres tests; record skips when engine unavailable. Verify EVALSHA reload handles NOSCRIPT only, not arbitrary Redis errors.
- [ ] Commit: `fix: make reservations and worker recovery idempotent`.

## Task 4: Durable cancellation and re-registration

**Files:** Modify drop_course.py, registration_repository.py, operation_repository.py, worker.py; create drop_consumer.py, `tests/real_integration/test_drop_lifecycle.py`.

**Interfaces:** `request_drop(registration_id: str, student_id: str, idempotency_key: str) -> Operation`; `cancel_registration(registration_id: str, expected_ticket_id: str, cancel_ticket_id: str) -> Operation`; release uses Task 3 registration ticket ownership. Worker consumes both queues with finite concurrency.

- [ ] Write failing tests: cancel only CONFIRMED owned record; repeated cancellation reduces DB count and releases Redis once; cancel then re-register generates new ticket; delayed old cancel/register cannot touch new registration; crash after cancel commit resumes Redis cleanup.
- [ ] Run opt-in `tests.real_integration.test_drop_lifecycle` and confirm failures.
- [ ] Implement CANCEL_PENDING → DB CANCELLED → Redis release → terminal cancel ticket. Forbid re-register until old ownership released; gate stale jobs by ticket/generation. Ensure unique student/section row can transition back to CONFIRMED using a fresh ticket.
- [ ] Run lifecycle/security tests; assert DB enrolled and Redis slots/credits/periods agree after each transition.
- [ ] Commit: `fix: complete cancellation and safe re-registration`.

## Task 5: PostgreSQL baseline with equivalent rules

**Files:** Create `core/usecases/register_course_postgres.py`, `tests/real_integration/test_postgres_baseline.py`; modify main.py and operation_repository.py.

**Interfaces:** `PostgresRegisterCourseUseCase.execute(student_id: str, section_id: str, idempotency_key: str) -> Operation`. Same request, rules and error codes as Task 2, immediate CONFIRMED after commit. Baseline catalog/list/status read DB; baseline cancel is transactional and does not depend on Redis/queue.

- [ ] Write failing tests: 3.000 valid distinct users yield 60 DB registrations; duplicate key returns same operation; two conflicting classes for one student cannot both commit; all normal prerequisite/credit/semester rules apply; baseline works with Redis and RabbitMQ stopped.
- [ ] Run baseline tests; distinguish connection/setup failures from intended assertion failures.
- [ ] Implement row locking in consistent order (academic student state, then section), SQL transaction and durable idempotency record. Wire mode at startup; no artificial delay or Redis middleware on baseline paths.
- [ ] Run same contract suite in both modes and compare final counts and error codes. Confirm resource/pool settings identical where applicable.
- [ ] Commit: `feat: add transactional postgres benchmark baseline`.

## Task 6: Honest frontend async states

**Files:** Modify App.tsx, types/registration.ts, services/api.ts, pollingService.ts, components WaitingRoomModal.tsx, RegisteredList.tsx, Header.tsx, ExceptionModal.tsx; create `services/pollingService.test.ts`, `components/RegistrationFlow.test.tsx` and minimal frontend test setup.

**Interfaces:** `pollOperation(ticketId, callbacks) -> cancel function` uses authenticated API and returns timeout separately; API requests only section_id or real registration_id. DTO includes registration_id, ticket_id, time_slots and statuses from Operation. Store unresolved ticket IDs per selected student locally and reconcile after reload.

- [ ] Write tests with fake timers/mocked transport: PENDING past limit never invokes success; transient network failure remains unknown; CONFIRMED success; cancel pending stays visible; reload resumes ticket; student switch cannot display previous student's result.
- [ ] Run frontend tests and confirm failure before edits.
- [ ] Update UI/API with lab student selector and JWT, stable key per intent/retry, disabled pending action, explicit pending/failed/confirmed/cancel states. Refresh real registration IDs after success. Provide manual check after timeout. Keep existing layout; add demo links and label demo data, no large-load HTTP controller.
- [ ] Run `npm.cmd test -- --run`, `npm.cmd run build`; browser-check full flows after Task 7 supplies services. No success claim based only on mocks.
- [ ] Commit: `fix: show confirmed registration and cancellation states`.

## Task 7: Reproducible Compose and live observability

**Files:** Modify docker-compose.yml, app Dockerfile, nginx.conf, requirements.txt, main.py, worker.py; create frontend Dockerfile, `.dockerignore`, `docker-compose.test.yml`, metrics.py, `infra/monitoring/grafana/provisioning/{datasources,prometheus-dashboards}/*.yml`, exporter configuration, `scripts/collect_container_metrics.ps1`; replace placeholder Prometheus config/dashboard queries.

**Interfaces:** Backend and worker HTTP `/metrics`; route histogram `registration_http_request_duration_seconds`, request counter `registration_http_requests_total`, worker counter `registration_jobs_total{kind,result}` and histogram `registration_job_duration_seconds`; no identity labels. Metrics labels bounded. Docker collector outputs `lab_container_cpu_cores`, `lab_container_memory_bytes`, `lab_container_network_receive_bytes_total`, `lab_container_network_transmit_bytes_total` by container.

- [ ] Add metric tests verifying scrape content, route template rather than ticket path, worker outcome and no secret/identity labels. Verify health distinguishes liveness from actual readiness. Failing tests run before instrumentation.
- [ ] Implement explicit exporter endpoints, RabbitMQ metrics plugin, k6 remote-write receiver, automatic Grafana datasource/dashboard, RedisInsight connection instructions, 2–5s sampling. Pin tested image versions. One uvicorn process per API container simplifies metrics; keep two API replicas. CAdvisor only if platform-compatible; otherwise host Docker stats textfile collector with staleness indicator.
- [ ] Build frontend inside image; enable loopback-only admin ports, application/data networks, monitoring profile and readiness conditions. Bind DB test ports only in test overlay. Add a bounded startup wait, do not open windows or start destructive resets automatically.
- [ ] Run `docker compose config --quiet`, build/start isolated test stack; assert service readiness, Prometheus UP for all expected targets and Grafana datasource health. Run smoke requests and inspect actual non-empty dashboard series including CPU/RAM/network; missing series remains no-data.
- [ ] Commit: `feat: provision observable docker lab`.

## Task 8: Repeatable benchmark and result verification

**Files:** Create scripts/benchmark.py, scripts/lab.ps1, `tests/load_testing/scenarios/flash_sale_test.js`, `tests/unit/test_benchmark_results.py`, `tests/real_integration/test_benchmark_reset.py`; update 3000_concurrent_users.js and replace/redirect obsolete race scripts.

**Interfaces:** `python -m scripts.benchmark prepare|verify|report --run-id ID --mode MODE`; prepare returns dataset manifest with generation, section_id and fixture token mapping; verify outputs counts/violations and exits nonzero on inconsistent or undrained result. `lab.ps1` offers Start, Smoke, Benchmark, Verify, Recover, Stop; Benchmark mode argument Both/Postgres/RedisQueue. Stop preserves volumes.

- [ ] Write failing tests: pending/unacked jobs prevent reset; stale generation cannot mutate new run; unique global iteration mapping covers 3.000 students; 60 accepted but 59 confirmed fails; 409 duplicate is not classified SECTION_FULL; summary never supplies fabricated missing metrics.
- [ ] Implement benchmark-only dataset namespace, admission gate and generation check, drain timeout and fixture tokens; warm cache only in Redis mode. Keep normal data untouched. Runs cannot overlap; host-side orchestration locks and DB run state protect lifecycle.
- [ ] Implement k6 smoke, 500×6 flash and separate sustained 3.000-VU profile. Configure expected statuses per endpoint; count SECTION_FULL, accepted, confirmed, duplicate, 429, 5xx and transport failures distinctly. Separate initial response vs end-to-end latency. Polling metrics get separate request tags. Both modes traverse same Nginx and same policy, with valid per-student lab identity for rate limiting.
- [ ] Implement output JSON and CSV/Markdown report using run artifacts, same-resource manifest, warmup and three alternating measured runs per mode. Record stack and load generator resource consumption and sample interval.
- [ ] Run unit/reset tests, smoke both modes, then flash and sustained within available capacity. Verify Redis/DB invariants after drain, stop measurements on infrastructure failures, and label any incomplete target explicitly.
- [ ] Commit: `feat: add verified repeatable load benchmarks`.

## Task 9: Diagrams, operator runbook and final review

**Files:** Create `docs/lab/README.md`, `docs/lab/demo-90-seconds.md`, `docs/lab/architecture-lab.mmd`, `architecture-proposed.mmd`, `registration-sequence.mmd`, `cancellation-sequence.mmd`, `register-slide.lua`, `peak-shaving.csv`; modify root README. Store actual benchmark artifacts in `artifacts/benchmarks/<run-id>/`, omit tokens/secrets.

- [ ] Write diagrams that match implemented modes and network boundaries. Mark future HA/replication and peak-shaving numbers as proposals/simulation. Explain EVALSHA and actual schema/Redis key inspection. Export SVG if renderer available; do not claim render verification without inspecting output.
- [ ] Write Windows commands for fresh setup, seed, smoke, recovery, benchmark, SQL/Redis assertions and stop without volume deletion. Explain lab auth and missing production guarantees, environment requirements, measuring rather than asserting latency, and four-window demo/video checklist.
- [ ] Run complete unit/API/real integration/frontend suite and actual browser flows; inspect dashboard with live smoke data. Review whole diff against spec, including five Review Focus cases. Resolve findings before declaring done.
- [ ] Confirm no undocumented destructive setup, no secrets in artifacts, no stale README performance claims, test runtime dependencies pinned and documented. Report all skipped/blocked checks accurately; do not claim achieved 3.000 VUs without run artifacts.
- [ ] Commit: `docs: add reproducible lab demonstration and measured results`.

## Self-review and execution handoff

### Execution record — 08/11/2026

Tasks 1–9 implemented on `feature/observable-lab`. Shared operation code and tests were grouped rather than duplicated into the file-per-usecase layout above; the original checklist is retained as the planning record. Actual delivered modules, verification and rulings are documented in `docs/lab/implementation-review.md`; measured acceptance and limits in `docs/lab/measured-results.md`.

Evidence: 46 Python tests (including dedicated PostgreSQL/Redis/RabbitMQ), 2 frontend tests and production build; PowerShell concurrent-runner check; six full flash runs with verified counts; real browser signup/reload/cancel/re-register/student-switch; seven Prometheus targets UP and Grafana inspected. Sustained 300 VUs passed; 3.000 VUs was executed twice and failed the no-error threshold. No production capacity claim follows from this lab. Diagram sources are supplied, without claiming rendered SVG/video verification.

Spec coverage: Sections 1–4 → Tasks 7/9; Section 5 → Tasks 1–5; Section 6 → Task 6; Section 7 → Tasks 5/8; Section 8 → Task 7; Section 9 → Task 9; Section 10 → tests in all tasks and final verification. The five review risks have explicit test owners above.

The subsystems share operation states and benchmark identity, so one sequential plan avoids mismatched contracts. Native implementation is recommended: one implementer retains lifecycle context, with a fresh whole-branch review at the end. No implementation starts until execution handoff required by writing-plans is resolved.
