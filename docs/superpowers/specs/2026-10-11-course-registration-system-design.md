# Đặc tả Thiết kế Kiến trúc: Hệ thống Đăng ký Học phần Trực tuyến (3.000 Sinh viên)

- **Ngày tạo:** 2026-10-11
- **Mục tiêu:** Thiết kế và xây dựng Hệ thống Đăng ký học phần trực tuyến quy mô 3.000 sinh viên đồng thời (Peak Load) theo mô hình Monorepo, áp dụng Clean Architecture, Screaming Architecture và cơ chế chống quá tải / race condition nhiều tầng.

---

## 1. Bối cảnh & Yêu cầu Nghiệp vụ

### 1.1. Miền bài toán
Trong các trường đại học, đợt mở cổng đăng ký tín chỉ là thời điểm phát sinh tải đột biến (flash crowd). Hàng ngàn sinh viên cùng truy cập vào một thời điểm chính xác (ví dụ: 08:00:00 sáng) để tranh slot các lớp học phần có giảng viên hoặc thời khóa biểu mong muốn.
Hệ thống phải đảm bảo:
1. **Không nghẽn mạng / sập máy chủ (High Availability & Fault Tolerance):** Duy trì dịch vụ ổn định dưới áp lực 3.000 sinh viên đồng thời.
2. **Không bán vượt sĩ số (Zero Overselling / No Race Condition):** Lớp 30 chỗ tuyệt đối chỉ chấp nhận đúng 30 lượt đăng ký, kể cả khi 500 yêu cầu ghi danh gửi tới cùng mili-giây.
3. **Phản hồi tức thì (Low Latency):** Phản hồi kết quả tiếp nhận đăng ký trong thời gian ngắn nhất (p95 $\le$ 250ms).
4. **Kiểm tra ràng buộc nghiệp vụ (Business Rules Validation):** Môn học tiên quyết, trùng lịch học, giới hạn tín chỉ tối thiểu/tối đa trong kỳ.

### 1.2. Thông số Tải & Mục tiêu SLA/SLO
- **Quy mô sinh viên:** 3.000 sinh viên đồng thời (Concurrent Active Users - CCU).
- **Hành vi cao điểm:** 80% Read (tra cứu danh mục, xem slot lớp học phần), 20% Write (submit đăng ký / hủy môn).
- **Throughput dự kiến:**
  - Peak Read: ~2.500 - 3.500 QPS.
  - Peak Write: ~500 - 1.000 TPS tại thời điểm mở cổng.
- **Chỉ số độ trễ (Latency SLA):**
  - Read APIs: $p95 \le 150\text{ms}$, $p99 \le 300\text{ms}$.
  - Write APIs (Tiếp nhận & trừ slot Redis): $p95 \le 250\text{ms}$, $p99 \le 500\text{ms}$.
- **Tỉ lệ lỗi (Error Rate):** $\le 0.01\%$ (loại trừ các lỗi nghiệp vụ hợp lệ như hết chỗ, trùng lịch).

---

## 2. Kiến trúc Tổng thể & Hạ tầng Chống Quá tải

### 2.1. Luồng xử lý yêu cầu (Request Flow)
1. **Client (Web/SPA):** Sinh viên gửi yêu cầu đăng ký qua HTTPS.
2. **Nginx Reverse Proxy:**
   - Terminate SSL, nén Gzip/Brotli.
   - Áp dụng Rate Limiting (Token Bucket: 10 req/s/IP) để chống bot/spam script.
   - Cân bằng tải Round-Robin tới các instance Backend.
3. **App Server (FastAPI Async):**
   - Xác thực sinh viên (JWT Token / Session).
   - Kiểm tra sơ bộ các ràng buộc trong bộ nhớ đệm (trùng lịch, giới hạn tín chỉ).
4. **Redis In-Memory Layer (Hot Data & Atomic CAS):**
   - Lưu trữ trạng thái số slot còn lại của từng lớp: `section:{id}:slots`.
   - Chạy **Redis Lua Script** để thực hiện kiểm tra `current_slots > 0` và trừ slot (`DECR`) hoàn toàn **nguyên tử** (Atomic).
   - Nếu hết slot: Trả về lỗi ngay lập tức (HTTP 409 Conflict) trong vòng `< 10ms`, không chạm đến DB.
5. **RabbitMQ Message Queue (Buffer Writes):**
   - Khi trừ slot trên Redis thành công, Backend đẩy message `CourseRegistrationRequestedEvent` vào hàng đợi RabbitMQ `registration_queue`.
   - Trả về mã phản hồi `202 Accepted` hoặc `200 OK (Registration Pending/Reserved)` kèm ticket ID cho client.
6. **Background Worker & PostgreSQL Database:**
   - Worker nhận message từ RabbitMQ theo tốc độ xử lý định mức (Rate Matching).
   - Mở database transaction ghi vào bảng `registrations` và `enrollments`.
   - Bảng DB có Unique Constraint `(student_id, section_id)` để đảm bảo tính Idempotency.
   - Nếu worker gặp lỗi bất khả kháng (ví dụ sinh viên bị khóa tài khoản phút chót), worker hoàn trả lại slot trong Redis (`INCR`).

---

## 3. Cấu trúc Mã nguồn (Clean Architecture & Monorepo)

Mã nguồn tuân thủ nguyên lý Clean Architecture kết hợp Package by Feature:

```
course-registration-system/
├── docs/                                  # Tài liệu phân tích và thiết kế hạ tầng
│   ├── 01_yeu_cau_va_tai_trong/           # 1.1_mo_hinh_tai_trong.md, 1.2_chi_so_hieu_nang.md
│   ├── 02_phuong_an_ha_tang/              # 2.1_so_do_tong_the_ha_tang.md, 2.2_cau_hinh_may_chu.md, 2.3_giai_phap_mo_rong.md
│   ├── 03_phan_tich_hoat_dong/            # 3.1_vong_doi_yeu_cau.md, 3.2_mo_hinh_tien_trinh.md, 3.3_ket_noi_mang.md
│   ├── 04_thiet_ke_luu_tru/               # 4.1_mo_hinh_du_lieu_rdbms.md, 4.2_chien_luoc_caching.md, 4.3_sao_chep_va_phan_vung.md
│   └── 05_giai_phap_chong_qua_tai/        # 5.1_hang_doi_va_dem_tai.md, 5.2_kiem_soat_dong_thoi.md, 5.3_rate_limiting_va_chia_dot.md
├── infra/                                 # Cấu hình máy chủ & IaC
│   ├── terraform/                         # Terraform modules (compute, networking, database)
│   ├── docker/                            # Nginx proxy config, Backend Dockerfile, docker-compose.prod.yml
│   ├── k8s/                               # Ingress, Deployments, HPA
│   └── monitoring/                        # Prometheus config, Grafana dashboards
├── src/backend/                           # Python 3.12 (FastAPI, Redis, RabbitMQ, PostgreSQL)
│   ├── core/                              # Domain & Use Cases độc lập
│   │   ├── domain/entities/               # Student, CourseSection, Registration, Semester
│   │   ├── domain/exceptions/             # SectionFullException, ScheduleConflictException, ...
│   │   └── usecases/                      # register_course, drop_course, view_curriculum
│   ├── adapters/                          # In-bound & Out-bound Ports/Adapters
│   │   ├── in_bound/controllers/          # FastAPI REST API Controllers
│   │   ├── in_bound/consumers/            # RabbitMQ Consumer Workers
│   │   └── out_bound/                     # Gateways (Cache, Queue, Persistence)
│   ├── infrastructure/                    # Frameworks, DB, Redis Lua, RabbitMQ
│   │   ├── webserver/                     # Middlewares (Rate Limiter, Logging, CORS)
│   │   ├── database/                      # Models, Migrations, Repositories
│   │   ├── cache/                         # Redis Connection & Lua Script atomic CAS
│   │   └── messaging/                     # RabbitMQ Producer & Consumer
│   └── main.py                            # DI container & FastAPI app entrypoint
├── src/frontend/                          # React 18, Vite, TypeScript, Tailwind CSS
├── tests/                                 # Unit, Integration & k6 Load Tests
│   ├── unit/                              # Domain business rules tests
│   ├── integration/                       # Redis + DB repository tests
│   └── load_testing/                      # k6 scenarios (3000 users, race condition)
├── scripts/                               # Tiện ích sinh dữ liệu & nạp cache
│   ├── init_db.sh (và .ps1 cho Windows)   # Seed 3.000 SV, 200 lớp học phần
│   └── seed_cache.sh (và .ps1)            # Nạp trước vào Redis
├── docker-compose.yml
└── README.md
```

---

## 4. Thiết kế Chi tiết Dữ liệu & Cơ chế Đồng thời

### 4.1. Lược đồ CSDL PostgreSQL
- `students`: `id (UUID/INT)`, `student_code (VARCHAR, UNIQUE)`, `name`, `major`, `academic_year`, `max_credits`.
- `courses`: `id`, `course_code (VARCHAR, UNIQUE)`, `name`, `credits`, `prerequisite_course_id`.
- `semesters`: `id`, `name`, `is_active (BOOLEAN)`.
- `course_sections`: `id`, `course_id`, `semester_id`, `section_code`, `room`, `schedule_day`, `start_period`, `end_period`, `max_capacity`, `current_enrolled`.
- `registrations`: `id`, `student_id`, `section_id`, `semester_id`, `status ('CONFIRMED', 'CANCELLED', 'PENDING')`, `registered_at (TIMESTAMP)`.
- **Ràng buộc:**
  - `UNIQUE(student_id, section_id)`: Chống sinh viên ghi danh trùng lặp.
  - Index: `idx_sections_semester (semester_id)`, `idx_reg_student (student_id)`.

### 4.2. Redis Data Structure & Atomic Lua Script
- Key `section:{id}:capacity`: Dung lượng tối đa.
- Key `section:{id}:slots`: Số slot khả dụng còn lại.
- Key `section:{id}:enrolled`: Set chứa `student_id` đã giữ slot.
- **Lua Script trừ slot:**
```lua
local section_id = KEYS[1]
local student_id = ARGV[1]

-- 1. Kiểm tra sinh viên đã đăng ký lớp này chưa
if redis.call('SISMEMBER', 'section:' .. section_id .. ':enrolled', student_id) == 1 then
    return -1 -- Already enrolled
end

-- 2. Kiểm tra slot còn trống không
local slots = tonumber(redis.call('GET', 'section:' .. section_id .. ':slots') or 0)
if slots <= 0 then
    return 0 -- Out of capacity
end

-- 3. Trừ slot và thêm sinh viên vào set
redis.call('DECR', 'section:' .. section_id .. ':slots')
redis.call('SADD', 'section:' .. section_id .. ':enrolled', student_id)
return 1 -- Success
```

---

## 5. Chiến lược Kiểm thử Tải & Xác minh (Verification Strategy)
1. **Kiểm thử logic Domain (Unit tests):**
   - Đăng ký hợp lệ -> Thành công.
   - Trùng lịch tiết học -> Bắn `ScheduleConflictException`.
   - Vượt quá tổng số tín chỉ tối đa -> Báo lỗi.
2. **Kiểm thử tranh chấp đồng thời (Race Condition Load Test - k6):**
   - 500 Virtual Users đồng thời gọi POST `/api/v1/registrations` vào 1 lớp duy nhất có 30 chỗ.
   - Kỳ vọng: Đúng 30 phản hồi HTTP 200/202, 470 phản hồi báo hết chỗ (HTTP 409).
   - Kiểm tra DB & Redis: `current_enrolled == 30`, không có 31.
3. **Kiểm thử áp lực toàn diện (3000 Concurrent Users - k6):**
   - 3.000 VUs trong 5 phút.
   - P95 response time duy trì dưới 250ms.
