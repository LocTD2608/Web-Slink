# Đặc tả Thiết kế Kiến trúc: Hệ thống Đăng ký Học phần Trực tuyến (3.000 Sinh viên)

- **Ngày cập nhật:** 2026-10-11
- **Phiên bản:** 2.2 (Bổ sung Cơ chế Tìm kiếm Danh mục Client-side Filter 3.500 QPS & Giao dịch Bồi hoàn Compensating Rollback)
- **UI/UX Reference:** [Stitch Project 1242719912165769412 - Academic Registrar Grid](https://stitch.withgoogle.com/projects/1242719912165769412)

---

## 1. Bối cảnh & Yêu cầu Nghiệp vụ Cao điểm

### 1.1. Miền bài toán & Thách thức Kỹ thuật
Hệ thống Đăng ký học phần đại học phục vụ quy mô **3.000 sinh viên đồng thời (Concurrent Active Users - CCU)** trong đợt mở cổng tín chỉ (Flash Crowd).
Các thử thách kỹ thuật cốt lõi:
1. **Chống sập nguồn & Chịu tải cao:** Duy trì ổn định dưới áp lực truy cập đồng loạt lúc 08:00:00 sáng.
2. **Không bán vượt sĩ số (Zero Overselling / Strict CAS):** Loại bỏ Race Condition khi hàng trăm sinh viên tranh nhau các slot cuối cùng của một lớp học phần.
3. **Kiểm tra ràng buộc nghiệp vụ trong $O(1)$ In-Memory:** Đưa toàn bộ việc thẩm định điều kiện tiên quyết, trùng lịch học và trần tín chỉ lên Redis, triệt tiêu 100% truy vấn DB quan hệ tại bước thẩm định.
4. **Tìm kiếm & Duyệt danh mục siêu tốc (Zero DB I/O for Search):** Nạp toàn bộ 150-200 lớp học phần vào Redis string; Frontend đảm nhiệm tìm kiếm và lọc dữ liệu (Client-side filtering), bảo vệ máy chủ khỏi các truy vấn `LIKE %...%`.
5. **Giao dịch bồi hoàn (Compensating Rollback Transaction):** Đảm bảo tính nhất quán cuối cùng (Eventual Consistency), tự động hoàn trả slot trên Redis nếu Worker gặp lỗi ghi DB bất khả kháng.
6. **Phản hồi trạng thái bất đồng bộ tin cậy:** Cơ chế tiếp nhận tức thì (202 Accepted) kết hợp luồng **Controlled Short Polling** cực kỳ ổn định, đọc kết quả trực tiếp từ Redis trong $< 2\text{ms}$.
7. **Idempotency tuyệt đối:** Khóa giao dịch bằng `X-Idempotency-Key` ngăn chặn việc spam click đúp hoặc network retry tạo rác vào Queue.

### 1.2. Thông số Tải & Mục tiêu SLA/SLO
- **Quy mô:** 3.000 sinh viên đồng thời (CCU).
- **Phân bố tải:**
  - $80\%$ Read (tra cứu danh mục, xem slot lớp học phần, kiểm tra thời khóa biểu).
  - $20\%$ Write (gửi lệnh ghi danh / hủy môn).
- **Thông số thông lượng (Throughput):**
  - **Peak Read QPS:** $2.500 - 3.500\text{ req/s}$.
  - **Peak Write TPS:** $500 - 1.000\text{ req/s}$ (dồn vào 10 giây đầu tiên).
- **Mục tiêu Độ trễ (Latency SLA):**
  - Read APIs (`/api/v1/sections` từ Redis): $p95 \le 10\text{ms}$, $p99 \le 50\text{ms}$.
  - Write APIs (Tiếp nhận & trừ slot tức thì trên Redis): $p95 \le 150\text{ms}$, $p99 \le 250\text{ms}$.
  - Async DB Persistence Confirmation (qua Polling Redis): $p95 \le 1.000\text{ms}$.
- **Tỉ lệ lỗi (Error Rate):** $\le 0.001\%$ đối với lỗi hệ thống 5xx.

---

## 2. Chiến lược Cắt tỉa Thực chiến: Tránh 3 "Cạm bẫy Kỹ thuật" cho Demo 3 Tuần

Để đảm bảo tiến độ bàn giao sản phẩm chạy thật (Runnable Demo) trong vòng 3 tuần, hệ thống tách bạch rõ ràng giữa **Mô hình Hạ tầng Lý thuyết (Tài liệu báo cáo đồ án)** và **Môi trường Demo Thực tế**:

### 2.1. Cắt tỉa Cạm bẫy 1: Triển khai K8s/Terraform $\rightarrow$ Đóng gói Độc lập trên Docker Compose
* **Thực tế:** Cấu hình Kubernetes, Ingress Controller, HPA, Prometheus/Grafana trên máy cá nhân rất dễ phát sinh lỗi driver mạng ảo, ngốn toàn bộ thời gian của kỹ sư DevOps.
* **Giải pháp Tối ưu Demo:**
  * Toàn bộ hệ sinh thái chạy thực tế được gói gọn trong **duy nhất 1 file `docker-compose.yml`** trên máy tính cá nhân (16GB RAM, Windows/Linux):
    1. `nginx`: Reverse Proxy L7, phân tải Round-Robin tới 2 app nodes, rate limit Token Bucket.
    2. `fastapi-node-1`: Backend app instance 1 (chạy 2-4 async workers).
    3. `fastapi-node-2`: Backend app instance 2 (chạy 2-4 async workers).
    4. `redis`: In-memory store, Atomic Lua script, Pre-warm cache.
    5. `rabbitmq`: Message broker buffer ghi danh.
    6. `postgres`: Relational DB System of Record.
    7. `worker`: Background consumer ghi nhận bền vững (Persisted ACID writes).
  * **Tài liệu lý thuyết:** Thư mục `infra/terraform/` và `infra/k8s/` vẫn cung cấp đầy đủ các file cấu hình và tài liệu kiến trúc mẫu để bảo vệ đồ án đạt điểm tối đa về mặt thiết kế hệ thống lớn.

### 2.2. Cắt tỉa Cạm bẫy 2: Nút thắt Mã hóa Mật khẩu (Bcrypt Bottleneck) khi Test Tải
* **Thực tế:** Khi chạy k6 giả lập 3.000 sinh viên, nếu mỗi request đăng ký đều gọi hàm băm mật khẩu Bcrypt/Argon2 hoặc truy vấn DB xác thực tài khoản, CPU sẽ bị chiếm dụng 100% vì băm mật khẩu chứ không phải do logic đăng ký.
* **Giải pháp Tối ưu Demo:**
  * **Pre-warmed JWT Tokens:** Sinh sẵn 3.000 JWT token tĩnh lưu trong file `tests/load_testing/tokens.csv` tương ứng với 3.000 sinh viên mẫu (`student_0001` đến `student_3000`).
  * **In-Memory JWT Signature Verification:** Tầng Auth của FastAPI chỉ giải mã chữ ký (HMAC-SHA256) với Secret Key ngay trong bộ nhớ ($O(1)$ CPU), tuyệt đối không truy vấn DB kiểm tra mật khẩu trong luồng test tải và ghi danh cao điểm.

### 2.3. Cắt tỉa Cạm bẫy 3: Rủi ro Treo Kết nối SSE qua Nginx $\rightarrow$ Ưu tiên Controlled Short Polling
* **Thực tế:** Giữ hàng ngàn persistent SSE connections qua Nginx cục bộ dễ gặp hiện tượng Nginx buffer dữ liệu (`proxy_buffering`) hoặc timeout, khiến UI bị treo vô thời hạn ở trạng thái "Đang chờ".
* **Giải pháp Tối ưu Demo:**
  * **Luồng chính (Primary - Ổn định 100%):** **Controlled Short Polling**:
    1. Sinh viên bấm "Đăng ký" $\rightarrow$ Nhận mã `202 Accepted` kèm `ticket_id` trong $< 100\text{ms}$.
    2. Frontend gọi `GET /api/v1/registrations/status/{ticket_id}` mỗi $1\text{s}$ (tối đa 3 lần).
    3. API đọc trực tiếp trạng thái từ Redis key `ticket:{ticket_id}:status` (`PENDING`, `CONFIRMED`, `FAILED`).
    4. Trả về kết quả trong $< 2\text{ms}$, triệt tiêu rủi ro đứt socket hay nghẽn buffer Nginx.
  * **Luồng phụ (Optional Phase 2):** Endpoint SSE `/api/v1/registrations/stream/{ticket_id}` chỉ được kích hoạt bổ sung sau khi toàn bộ luồng polling đã hoàn thiện và chạy trơn tru.

---

## 3. Kiến trúc Cốt lõi & Giải pháp Chống Quá tải

### 3.1. In-Memory Business Rule Validation (Redis Lua Script)
Toàn bộ dữ liệu thẩm định được cấu trúc hóa trên Redis trước giờ G:
1. **Môn học tiên quyết (`student:{id}:completed_courses` - Redis SET):**
   - Kiểm tra `SISMEMBER student:{id}:completed_courses {prereq_course_id}` trong $O(1)$.
2. **Trùng lịch thời khóa biểu (`student:{id}:registered_slots` - Redis BITMAP / BITFIELD):**
   - 84 bits (7 ngày $\times$ 12 tiết học). Thực hiện phép `BITOP AND` với mặt nạ lịch của lớp học phần. Nếu $> 0 \rightarrow$ Xung đột lịch học ngay tức thì trong $< 1\text{ms}$.
3. **Hạn mức tín chỉ (`student:{id}:credits` - Redis HASH):**
   - Kiểm tra: `current_credits + section_credits <= max_credits`.
4. **Lua Script All-in-One:**
   Thực thi tuần tự nguyên tử: Kiểm tra Idempotency $\rightarrow$ Tiên quyết $\rightarrow$ Trùng lịch $\rightarrow$ Trần tín chỉ $\rightarrow$ Trừ slot khả dụng (`DECR section:{id}:slots`). Đảm bảo nguyên tử 100%, không bị Race Condition.

### 3.2. Cơ chế Tìm kiếm Danh mục & Lọc Dữ liệu (Catalog Search 3.500 QPS & Client-side Filtering)
* **Phân tích:** Trường học có khoảng 150 – 200 lớp học phần đang mở. Tổng kích thước payload danh mục này chỉ $\approx 100\text{KB}$ JSON (sau khi nén Gzip chỉ còn $\approx 18\text{KB}$).
* **Kiến trúc Tối ưu hóa:**
  1. Trong quy trình Warm-up, toàn bộ mảng JSON 200 lớp học phần được tuần tự hóa và lưu vào duy nhất một key Redis: `catalog:active_sections`.
  2. Endpoint `GET /api/v1/sections` chỉ đọc chuỗi JSON từ key Redis này và trả về trực tiếp (độ trễ $< 1\text{ms}$, băng thông phục vụ hàng ngàn QPS mà CPU App Server gần như bằng 0).
  3. **Client-side Filtering:** Frontend (React) tải mảng 200 lớp này về trình duyệt và lưu vào State. Mọi thao tác tìm kiếm từ khóa tên môn/giảng viên, lọc theo thứ trong tuần, lọc theo khoa/ngành được thực hiện hoàn toàn trong bộ nhớ trình duyệt của sinh viên.
  4. **Kết quả:** Triệt tiêu hoàn toàn các câu lệnh nặng `SELECT ... WHERE name LIKE '%...%'` trên PostgreSQL, bảo vệ 100% tài nguyên DB cho luồng ghi danh quan trọng.

### 3.3. Kịch bản Bồi hoàn Slot khi Worker ghi DB thất bại (Compensating Rollback Transaction)
* **Vấn đề:** Sinh viên đã trừ slot thành công trên Redis (nhận `202 Accepted`), nhưng khi Worker xử lý message để ghi vào PostgreSQL thì gặp sự cố (mất kết nối DB hoặc lỗi ràng buộc bất thường). Nếu không bồi hoàn, slot đó sẽ bị mất vĩnh viễn (Phantom Occupancy).
* **Cơ chế Bồi hoàn Bù trừ (Compensating Transaction):**
  1. Trong Registration Worker, toàn bộ tác vụ ghi DB được đặt trong khối `try...except` với cơ chế Retry có Exponential Backoff (thử lại tối đa 3 lần).
  2. Nếu sau 3 lần vẫn thất bại bất khả kháng:
     - Worker kích hoạt lệnh hoàn trả ngược lại lên Redis:
       * `INCR section:{id}:slots` (hoàn trả 1 slot khả dụng).
       * `SREM section:{id}:enrolled {student_id}` (xóa sinh viên khỏi danh sách đã giữ slot).
       * Xóa bit thời gian đã đặt trước trong `student:{id}:registered_slots` và trừ lại tín chỉ trong `student:{id}:credits`.
     - Cập nhật trạng thái vé `ticket:{ticket_id}:status = "FAILED"` kèm trường `reason: "Lỗi hệ thống ghi nhận cơ sở dữ liệu, slot đã được hoàn trả"`.
     - Đẩy message lỗi vào **Dead-Letter Queue (DLQ)** `registration_dlq` để quản trị viên đối soát lỗi.
  3. Lượt Polling tiếp theo của sinh viên ngay lập tức nhận được trạng thái `FAILED` kèm thông báo minh bạch, cho phép sinh viên bấm đăng ký lại mà không bị kẹt slot.

### 3.4. Chống Cache Stampede & Warm-Up Pipeline
- Tự động chạy `scripts/warmup_cache.py` trước khi mở cổng để nạp trước toàn bộ danh mục lớp (`catalog:active_sections`), số lượng slot, dữ liệu 3.000 sinh viên và mặt nạ thời gian vào Redis.
- Cố định TTL dài trong đợt đăng ký, kết hợp kỹ thuật Single Flight (Mutex Lock) để bảo vệ PostgreSQL.

### 3.5. Idempotency Key
- Frontend gửi header: `X-Idempotency-Key: {student_id}-{section_id}-{timestamp_window}`.
- FastAPI Middleware kiểm tra nguyên tử: `SET idempotency:{key} "PROCESSING" EX 60 NX`. Nếu đã tồn tại thì ngắt ngay lập tức (HTTP 409 Conflict), chặn spam click và bảo vệ RabbitMQ.

### 3.6. Định mức Phần cứng cho Môi trường Demo (Local 16GB RAM)

| Dịch vụ Container | Định mức RAM | Định mức CPU | Ghi chú vận hành |
| :--- | :--- | :--- | :--- |
| `nginx` | 256 MB | 0.5 CPU | Reverse Proxy, Rate Limiter, Load Balancer 2 app nodes |
| `fastapi-node-1` | 512 MB | 1.0 CPU | Uvicorn async worker, xử lý API & in-memory auth |
| `fastapi-node-2` | 512 MB | 1.0 CPU | Uvicorn async worker, phân tải song song |
| `redis` | 1 GB | 1.0 CPU | Chứa cache warm-up, Lua Script engine, catalog, ticket status |
| `rabbitmq` | 1 GB | 1.0 CPU | Queue buffer hấp thụ đột biến ghi danh, DLQ |
| `postgres` | 2 GB | 2.0 CPU | RDBMS lưu trữ dữ liệu bền vững (System of Record) |
| `worker` | 512 MB | 1.0 CPU | RabbitMQ Consumer ghi dữ liệu & Compensating Rollback |
| **Tổng cộng** | **~5.8 GB RAM** | **~7.5 vCPU** | **Hoạt động cực kỳ êm ái trên PC cá nhân 16GB RAM** |

---

## 4. Cấu trúc Thư mục Monorepo & Clean Architecture

```
course-registration-system/
├── docs/                                  # Tài liệu báo cáo phân tích và thiết kế hạ tầng
│   ├── 01_yeu_cau_va_tai_trong/           # 1.1_mo_hinh_tai_trong.md, 1.2_chi_so_hieu_nang.md
│   ├── 02_phuong_an_ha_tang/              # 2.1_so_do_tong_the_ha_tang.md, 2.2_cau_hinh_may_chu.md, 2.3_giai_phap_mo_rong.md
│   ├── 03_phan_tich_hoat_dong/            # 3.1_vong_doi_yeu_cau.md, 3.2_mo_hinh_tien_trinh.md, 3.3_ket_noi_mang.md
│   ├── 04_thiet_ke_luu_tru/               # 4.1_mo_hinh_du_lieu_rdbms.md, 4.2_chien_luoc_caching.md, 4.3_sao_chep_va_phan_vung.md
│   └── 05_giai_phap_chong_qua_tai/        # 5.1_hang_doi_va_dem_tai.md, 5.2_kiem_soat_dong_thoi.md, 5.3_rate_limiting_va_chia_dot.md
│
├── infra/                                 # Infrastructure as Code & Cấu hình máy chủ
│   ├── terraform/                         # Terraform modules lý thuyết cho đồ án
│   │   ├── envs/prod/
│   │   └── modules/ (compute, networking, database)
│   ├── docker/                            # Cấu hình môi trường chạy thực tế
│   │   ├── nginx/                         # nginx.conf (Load balancer, rate limiter)
│   │   ├── app/                           # Dockerfile Backend
│   │   └── docker-compose.prod.yml
│   ├── k8s/                               # Kubernetes manifests lý thuyết cho đồ án
│   │   ├── ingress/
│   │   ├── deployments/
│   │   └── hpa/
│   └── monitoring/                        # Cấu hình Prometheus & Grafana
│       ├── prometheus/
│       └── grafana/
│
├── src/backend/                           # Backend Python 3.12 (FastAPI, Redis, RabbitMQ, PostgreSQL)
│   ├── core/                              # Clean Architecture - Lớp nghiệp vụ độc lập
│   │   ├── domain/
│   │   │   ├── entities/                  # Student, CourseSection, Registration, Semester, TimeSlot
│   │   │   └── exceptions/                # SectionFullException, ScheduleConflictException, PrerequisiteNotMetException, CreditLimitExceededException
│   │   └── usecases/                      # register_course, drop_course, view_curriculum
│   ├── adapters/                          # In-bound & Out-bound Adapters
│   │   ├── in_bound/
│   │   │   ├── controllers/               # REST API Routers (Registration, Catalog Sections, Polling Status)
│   │   │   └── consumers/                 # RabbitMQ Consumer Worker (Retry & Compensating Rollback)
│   │   └── out_bound/                     # Ports/Gateways (CacheGateway, QueueGateway, PersistenceGateway)
│   ├── infrastructure/                    # Frameworks, DB, Redis Lua, RabbitMQ
│   │   ├── webserver/                     # FastAPI App, Middlewares (In-memory JWT, Idempotency, Rate Limit)
│   │   ├── database/                      # SQLAlchemy Async, Migrations Alembic, Repositories
│   │   ├── cache/                         # Redis Client, Lua Scripting Engine, In-memory BITMAP checker, Catalog caching
│   │   └── messaging/                     # RabbitMQ aio-pika Producer, Consumer & DLQ
│   └── main.py                            # DI Container Wiring & Server Entrypoint
│
├── src/frontend/                          # Giao diện Sinh viên (React 18 + Vite + TypeScript + Tailwind CSS)
│   ├── src/
│   │   ├── components/                    # Lịch biểu tuần, Bảng môn học (Client-side Search & Filter), Polling Status Badge, Exception Modals
│   │   ├── services/                      # API Client, Polling Service, Idempotency Generator
│   │   └── store/                         # State Store (Zustand/React Context)
│   └── package.json
│
├── tests/                                 # Kịch bản kiểm thử tự động
│   ├── unit/                              # Kiểm tra nghiệp vụ logic đăng ký Domain/UseCases
│   ├── integration/                       # Kiểm tra tích hợp App, Redis và PostgreSQL
│   └── load_testing/                      # Kịch bản k6
│       ├── tokens.csv                     # 3.000 Pre-warmed JWT tokens tĩnh
│       ├── scenarios/
│       │   ├── 3000_concurrent_users.js   # Giả lập 3.000 SV truy cập trong 5 phút
│       │   └── race_condition_test.js     # Giả lập 500 SV tranh 30 slot của 1 lớp
│       └── reports/                       # Biểu đồ và kết quả kiểm thử tải
│
├── scripts/                               # Tiện ích tự động hóa
│   ├── init_db.sh (và init_db.ps1)        # Khởi tạo DB, sinh 3.000 SV và 200 lớp học phần
│   ├── seed_cache.sh (và seed_cache.ps1)  # Nạp trước thông tin vào Redis
│   ├── generate_tokens.py                 # Sinh 3.000 JWT tokens cho file tokens.csv
│   └── warmup_cache.py                    # Nạp toàn bộ dữ liệu warm-up và catalog vào Redis
├── .gitignore
├── docker-compose.yml                     # Cụm Docker hoàn chỉnh chạy mượt trên máy 16GB RAM
└── README.md                              # Hướng dẫn chi tiết thiết lập và chạy demo
```

---

## 5. Đồng bộ Thiết kế UI/UX theo Google Stitch (Project 1242719912165769412)
- Hệ màu: *Deep Academic Blue* (`#1E3A8A`), *Royal Blue* (`#2563EB`), *Emerald Green* (`#10B981`), *Amber Orange* (`#F59E0B`), *Crimson Red* (`#EF4444`).
- Typography: Font *Inter* kết hợp `font-variant-numeric: tabular-nums lining-nums;` cho mọi con số đếm slot và đồng hồ.
- 5 Màn hình:
  1. `Đăng ký học phần - Cổng Đào tạo Đại học`: Danh mục môn học, Client-side filter tức thì, ma trận thời khóa biểu tuần.
  2. `Kết Quả Đăng Ký & Dashboard Sinh Viên`: Danh sách môn đã ghi danh, tiến độ tín chỉ.
  3. `Feedback & Exception Modals Showcase`: Hộp thoại modal hiển thị thông báo nghiệp vụ (Hết chỗ, Trùng lịch, Đăng ký thành công, Lỗi bồi hoàn).
  4. `Kế hoạch Đăng ký & Trung tâm Xử lý Đồng thời`: Giỏ môn học dự kiến (Course Cart).
  5. `Phòng chờ Ảo & Trạng thái Hàng đợi`: Giao diện hiển thị trạng thái xử lý đăng ký thông qua Controlled Short Polling.
