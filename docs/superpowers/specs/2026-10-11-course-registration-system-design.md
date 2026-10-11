# Đặc tả Thiết kế Kiến trúc: Hệ thống Đăng ký Học phần Trực tuyến (3.000 Sinh viên)

- **Ngày cập nhật:** 2026-10-11
- **Phiên bản:** 2.0 (Giải quyết triệt để 5 nút thắt hạ tầng & Tích hợp thiết kế chuẩn Google Stitch UI/UX)
- **UI/UX Reference:** [Stitch Project 1242719912165769412 - Academic Registrar Grid](https://stitch.withgoogle.com/projects/1242719912165769412)

---

## 1. Bối cảnh & Yêu cầu Nghiệp vụ Cao điểm

### 1.1. Miền bài toán & Thách thức Kỹ thuật
Hệ thống Đăng ký học phần đại học phục vụ quy mô **3.000 sinh viên đồng thời (Concurrent Active Users - CCU)** trong đợt mở cổng tín chỉ (Flash Crowd).
Các thử thách kỹ thuật sống còn:
1. **Chống sập nguồn (Zero Downtime / High Availability):** Chịu được áp lực truy cập đồng loạt lúc 08:00:00 sáng.
2. **Không bán vượt sĩ số (Zero Overselling / Strict CAS):** Tuyệt đối không để xảy ra Race Condition khi hàng trăm sinh viên tranh nhau các slot cuối cùng của một lớp học phần.
3. **Kiểm tra ràng buộc nghiệp vụ trong $O(1)$ In-Memory:** Loại bỏ hoàn toàn truy vấn Database quan hệ trong quá trình xác thực điều kiện tiên quyết, trùng lịch, và trần tín chỉ.
4. **Phản hồi thời gian thực & Giải quyết trạng thái bất đồng bộ:** Hệ thống xử lý hàng đợi bất đồng bộ nhưng sinh viên nhận được kết quả xác nhận ngay lập tức qua Server-Sent Events (SSE) hoặc Polling có kiểm soát.
5. **Idempotency tuyệt đối:** Triệt tiêu hoàn toàn hiện tượng sinh viên click liên tục hoặc mạng lag gây nhân bản request.

### 1.2. Thông số Tải & Mục tiêu SLA/SLO
- **Quy mô:** 3.000 sinh viên đồng thời (CCU).
- **Phân bố tải:**
  - $80\%$ Read (tra cứu danh mục, xem slot lớp học phần, kiểm tra thời khóa biểu).
  - $20\%$ Write (gửi lệnh ghi danh / hủy môn).
- **Thông số thông lượng (Throughput):**
  - **Peak Read QPS:** $2.500 - 3.500\text{ req/s}$.
  - **Peak Write TPS:** $500 - 1.000\text{ req/s}$ (dồn vào 10 giây đầu tiên của đợt mở cổng).
- **Mục tiêu Độ trễ (Latency SLA):**
  - Read APIs: $p95 \le 100\text{ms}$, $p99 \le 200\text{ms}$.
  - Write APIs (Tiếp nhận & trừ slot tức thì trên Redis): $p95 \le 150\text{ms}$, $p99 \le 250\text{ms}$.
  - Async DB Persistence Confirmation: $p95 \le 1.500\text{ms}$ (thông qua SSE / Event push).
- **Tỉ lệ lỗi (Error Rate):** $\le 0.001\%$ đối với lỗi hệ thống 5xx.

---

## 2. Giải pháp Triệt để cho 5 Vấn đề Kiến trúc Hạ tầng

### 2.1. Giải quyết Nút thắt Ràng buộc Nghiệp vụ (In-Memory Business Rule Engine)
* **Vấn đề cũ:** Nếu App Server truy vấn PostgreSQL để kiểm tra môn tiên quyết, trùng thời khóa biểu và hạn mức tín chỉ, $1.000\text{ write req/s}$ cùng hàng ngàn read req/s sẽ khiến PostgreSQL cạn kiệt Connection Pool và sập ngay lập tức.
* **Giải pháp In-Memory:** Toàn bộ dữ liệu thẩm định được cấu trúc hóa trên **Redis** trước giờ G:
  1. **Môn học tiên quyết (`student:{id}:completed_courses` - Redis SET):**
     - Lưu tập hợp các mã môn sinh viên đã vượt qua.
     - Lớp học phần quy định `prereq_course_id`. Kiểm tra: `SISMEMBER student:{id}:completed_courses {prereq_course_id}` trong thời gian $O(1)$.
  2. **Trùng lịch thời khóa biểu (`student:{id}:registered_slots` - Redis BITMAP / BITFIELD):**
     - Mã hóa lịch học trong tuần thành chuỗi 84 bits (7 ngày $\times$ 12 tiết học/ngày).
     - Mỗi lớp học phần có mặt nạ bit thời gian `section:{id}:time_mask` (ví dụ Thứ 2 tiết 1-3 = bit 0, 1, 2 = 1).
     - Khi kiểm tra: Thực hiện phép toán logic `BITOP AND` giữa lịch hiện tại của SV và mặt nạ lớp học. Nếu kết quả $> 0$ $\rightarrow$ Xung đột thời khóa biểu ngay lập tức trong $< 1\text{ms}$ mà không cần join bảng phức tạp.
  3. **Hạn mức tín chỉ (`student:{id}:credits` - Redis HASH):**
     - Hash field: `current_credits`, `max_credits` (thường là 24-28 tín chỉ).
     - Kiểm tra: `current_credits + section_credits <= max_credits`.
  4. **Redis Lua Script Tích hợp Toàn diện (All-in-One Atomic Validation & Slot Decrement):**
     Toàn bộ 4 bước: Kiểm tra Idempotency $\rightarrow$ Môn tiên quyết $\rightarrow$ Trùng lịch $\rightarrow$ Trần tín chỉ $\rightarrow$ Trừ slot khả dụng được thực thi trong **1 lệnh Lua Script duy nhất**. Đảm bảo tính nguyên tử tuyệt đối, loại bỏ 100% round-trip mạng giữa App Server và Redis.

### 2.2. Luồng Truy vấn Kết quả Bất đồng bộ (Async Status Resolution Flow)
1. **Tiếp nhận tức thời (Instant Ingestion):**
   - Khi Lua script trên Redis thực thi thành công: Slot đã được giữ cho sinh viên (`RESERVED`).
   - App Server trả về ngay `HTTP 202 Accepted` kèm `ticket_id` và payload:
     `{"ticket_id": "uuid-...", "status": "PENDING", "estimated_wait_sec": 1}`.
   - App Server đẩy một job vào RabbitMQ `registration_queue`.
2. **Kênh đẩy thời gian thực (Server-Sent Events - SSE):**
   - Client mở một luồng HTTP persistent connection tới `/api/v1/registrations/stream/{ticket_id}`.
   - App Server lắng nghe Redis Pub/Sub trên channel `registration_events:{ticket_id}`.
   - Ngay khi Worker hoàn tất ghi dữ liệu bền vững (Persistence ACID) vào PostgreSQL:
     Worker gửi thông điệp `{"status": "CONFIRMED", "section_id": "...", "timestamp": ...}` lên Redis Pub/Sub.
     SSE Server nhận được và bắn ngay event về trình duyệt sinh viên. Trình duyệt hiển thị Modal xác nhận thành công (màu xanh Emerald `#10B981`) trong chưa đầy 1 giây.
3. **Cơ chế Fallback (Controlled Short Polling):**
   - Nếu kết nối SSE bị ngắt hoặc firewall chặn, Frontend tự động fallback sang polling:
     `GET /api/v1/registrations/status/{ticket_id}` mỗi 1.5 giây (tối đa 4 lần), đọc trạng thái từ Redis key `ticket:{ticket_id}:status`.

### 2.3. Quy trình Chống Nghẽn Tải Lạnh (Cache Warm-Up Pipeline & Stampede Prevention)
1. **Kế hoạch Nạp trước Dữ liệu (Pre-Warming Schedule - $T-30$ phút):**
   - Lúc 07:30:00 (30 phút trước khi mở cổng lúc 08:00:00):
   - Service `scripts/warmup_cache.py` chạy tự động, tải từ PostgreSQL và nạp vào Redis:
     * Toàn bộ danh mục môn học, danh sách lớp học phần và sĩ số (`section:{id}:slots`, `section:{id}:info`).
     * Dữ liệu 3.000 sinh viên: môn đã hoàn thành (`student:{id}:completed_courses`), lịch hiện tại, hạn mức tín chỉ.
     * Mặt nạ bit thời gian của tất cả các lớp học phần (`section:{id}:time_mask`).
2. **Chống Cache Stampede & Thundering Herd:**
   - **No Expiration During Registration:** Tất cả các key phục vụ đợt đăng ký được gán TTL dài (ví dụ 12 giờ) hoặc không set TTL cho tới khi đóng cổng đăng ký.
   - **Single Flight / Mutex Lock:** Nếu xảy ra trường hợp cache miss bất thường, App Server sử dụng Redis Distributed Mutex (`SET lock:warmup:{id} 1 EX 5 NX`) để chỉ cho phép DUY NHẤT 1 luồng truy vấn DB để nạp lại cache, các luồng khác chờ, bảo vệ tuyệt đối cho PostgreSQL.

### 2.4. Cơ chế Idempotency Key & Xử lý Gói tin Trùng (Request Deduplication)
1. **Frontend Signature Generation:**
   - Mỗi khi sinh viên bấm nút "Đăng ký", Frontend sinh header:
     `X-Idempotency-Key: {student_id}-{section_id}-{timestamp_window}` hoặc UUIDv4.
2. **Gateway / Middleware Atomic Check:**
   - Tại FastAPI Middleware, kiểm tra key bằng lệnh Redis:
     `SET idempotency:{key} "IN_PROGRESS" EX 60 NX`
   - Nếu Redis trả về `nil` (Key đã tồn tại):
     * Request này là duplicate do click đúp hoặc network retry!
     * Middleware ngắt request ngay lập tức, trả về `HTTP 409 Conflict` hoặc trả về `ticket_id` cũ đang xử lý:
       `{"message": "Yêu cầu đăng ký đang được xử lý, vui lòng không nhấn liên tục", "ticket_id": "..."}`.
     * Hoàn toàn không tạo thêm bất kỳ message rác nào vào RabbitMQ.

### 2.5. Định lượng Hạ tầng Phần cứng & Kết nối (Infrastructure Sizing)
Bảng định mức hạ tầng cho quy mô **3.000 CCU, Peak 3.500 QPS**:

| Thành phần | Số lượng / Cấu hình | CPU / RAM | Băng thông / Storage | Vai trò & Connection Pooling Limits |
| :--- | :--- | :--- | :--- | :--- |
| **Nginx Reverse Proxy** | 2 Nodes (HA - Keepalived) | 2 vCPU / 4 GB RAM mỗi node | Card mạng 1 Gbps (Peak traffic ~280 Mbps) | SSL Offload, Rate limit 15 req/s/IP, Keep-Alive 65s, `worker_connections 10240` |
| **Backend App (FastAPI)** | 3 Nodes (Docker/K8s Replicas) | 4 vCPU / 4 GB RAM mỗi node (Tổng 12 vCPU, 12 GB RAM) | Mạng nội bộ 10 Gbps VPC | Mỗi node chạy 4 Uvicorn workers bất đồng bộ, gánh ~1.200 req/s/node. Async Redis Pool: 100 kết nối/node |
| **Redis In-Memory** | 1 Primary + 1 Replica (Sentinel) | 4 vCPU / 8 GB RAM | RAM sử dụng thực tế ~1.2 GB, cấp 8 GB buffer | Chứa toàn bộ dữ liệu warm-up, Lua Script engine. Maxclients: 10.000, maxmemory-policy: `volatile-lru` |
| **RabbitMQ Broker** | 1 Cluster (2 Nodes) | 2 vCPU / 4 GB RAM mỗi node | SSD NVMe | Buffer ghi danh cao điểm, dung lượng hàng đợi 100.000 messages. Prefetch count = 20 |
| **Registration Workers**| 4 Workers | 2 vCPU / 2 GB RAM mỗi worker | Mạng nội bộ VPC | Tiêu thụ message với tốc độ định mức 200-300 records/s để bảo vệ PostgreSQL |
| **PostgreSQL (RDBMS)** | 1 Primary (Write) + 1 Replica (Read) | 8 vCPU / 16 GB RAM (Primary), 4 vCPU / 8 GB RAM (Replica)| SSD NVMe Enterprise 5.000 IOPS | System of Record. **PgBouncer** Connection Pool trung gian: `max_connections = 250`, `pool_size = 60`, transaction mode |

* **Tính toán Băng thông (Network Bandwidth):**
  $$\text{Throughput} = 3.500\text{ requests/sec} \times 10\text{ KB/payload} \times 8\text{ bits} \approx 280\text{ Mbps}$$
  Đường truyền 1 Gbps đáp ứng dư tải gấp 3.5 lần, đảm bảo không xảy ra nghẽn I/O card mạng.

---

## 3. Kiến trúc Phần mềm & Cấu trúc Thư mục Clean Architecture

### 3.1. Thiết kế theo Screaming Architecture & Package by Feature
Tuân thủ nghiêm ngặt mô hình Monorepo và Clean Architecture:

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
│   ├── terraform/                         # Tự động hóa hạ tầng mạng, máy ảo, subnet
│   │   ├── envs/prod/                     # Cấu hình môi trường triển khai thực tế
│   │   ├── modules/networking/            # VPC, Subnet, Firewall Rules, Security Groups
│   │   ├── modules/compute/               # Cấu hình cụm máy chủ ứng dụng & cân bằng tải
│   │   └── modules/database/              # Cụm CSDL PostgreSQL & Redis In-Memory cluster
│   ├── docker/                            # Dockerfile và container compose
│   │   ├── nginx/                         # Cấu hình Reverse Proxy, SSL, Gzip, Buffer limits, Rate Limiting
│   │   ├── app/                           # Base image ứng dụng Backend FastAPI
│   │   └── docker-compose.prod.yml        # Kịch bản khởi chạy hệ sinh thái máy chủ
│   ├── k8s/                               # Khởi tạo cụm Kubernetes
│   │   ├── ingress/                       # Cấu hình định tuyến và cân bằng tải L7
│   │   ├── deployments/                   # Quản lý replica pods cho Registration Service
│   │   └── hpa/                           # Horizontal Pod Autoscaler tự động tăng máy chủ theo CPU
│   └── monitoring/                        # Hệ thống giám sát tài nguyên và độ trễ
│       ├── prometheus/                    # Thu thập số liệu máy chủ, socket, connection pool
│       └── grafana/                       # Dashboard theo dõi TPS, thời gian phản hồi p95/p99, RAM/CPU
│
├── src/backend/                           # Mã nguồn Backend (Python 3.12 / FastAPI)
│   ├── core/                              # Lớp trung tâm: Quy tắc nghiệp vụ độc lập ("The Inside")
│   │   ├── domain/                        # Thực thể và mô hình nghiệp vụ bất biến
│   │   │   ├── entities/                  # Student, CourseSection, Registration, Semester, TimeSlot
│   │   │   └── exceptions/                # SectionFullException, ScheduleConflictException, PrerequisiteNotMetException, CreditLimitExceededException
│   │   └── usecases/                      # Các kịch bản sử dụng (Use Case Interactors)
│   │       ├── register_course/           # Nghiệp vụ: Đăng ký môn, xác thực tiên quyết, trừ slot
│   │       ├── drop_course/               # Nghiệp vụ: Hủy môn học, hoàn trả sĩ số
│   │       └── view_curriculum/           # Nghiệp vụ: Tra cứu học phần có sẵn
│   │
│   ├── adapters/                          # Lớp chuyển đổi dữ liệu và cổng giao tiếp (Adapters)
│   │   ├── in_bound/                      # Giao tiếp nhận dữ liệu từ bên ngoài
│   │   │   ├── controllers/               # Xử lý HTTP Request/Response (REST API & SSE Stream)
│   │   │   └── consumers/                 # Consumer nhận thông điệp xử lý đăng ký từ Hàng đợi RabbitMQ
│   │   └── out_bound/                     # Cổng kết nối ra các hệ thống bên ngoài (Gateways/Ports)
│   │       ├── cache_gateway/             # Interface kiểm tra và trừ slot tức thời trên Redis (Lua CAS)
│   │       ├── queue_gateway/             # Interface đẩy tác vụ đăng ký vào Message Broker
│   │       └── persistence_gateway/       # Interface lưu trữ trạng thái đăng ký vào CSDL
│   │
│   ├── infrastructure/                    # Chi tiết công nghệ, framework, drivers ("The Outside")
│   │   ├── webserver/                     # Cấu hình FastAPI, Middlewares (Idempotency, Rate Limiter Token Bucket, CORS)
│   │   ├── database/                      # Kết nối PostgreSQL (SQLAlchemy Async, PgBouncer Pool)
│   │   │   ├── migrations/                # Schema DDL (Alembic)
│   │   │   └── repositories/              # Triển khai truy vấn CSDL, Connection Pooling
│   │   ├── cache/                         # Triển khai Redis (Lua Scripting, In-memory rule validation)
│   │   └── messaging/                     # Triển khai Producer/Consumer cho RabbitMQ (aio-pika)
│   └── main.py                            # Thành phần "Main": Wiring Dependency Injection & Bootstrapping
│
├── src/frontend/                          # Ứng dụng giao diện sinh viên (React 18 + Vite + TypeScript)
│   ├── src/
│   │   ├── components/                    # Lịch biểu thời khóa biểu, Bảng môn học, Queue Waiting Room, Exception Modals
│   │   ├── services/                      # Tầng gọi API đăng ký, SSE listener, Idempotency generator
│   │   └── store/                         # Quản lý trạng thái giao diện và đệm kết quả
│   └── package.json
│
├── tests/                                 # Kịch bản kiểm thử tự động
│   ├── unit/                              # Kiểm tra nghiệp vụ logic đăng ký trong Domain/UseCases
│   ├── integration/                       # Kiểm tra tích hợp giữa App, Redis và PostgreSQL
│   └── load_testing/                      # Kịch bản kiểm thử tải cao điểm (k6)
│       ├── scenarios/
│       │   ├── 3000_concurrent_users.js   # Giả lập 3.000 sinh viên đồng thời truy cập trong 5 phút
│       │   └── race_condition_test.js     # Giả lập 500 sinh viên tranh nhau 30 slot của 1 lớp
│       └── reports/                       # Báo cáo biểu đồ phản hồi dưới áp lực tải
│
├── scripts/                               # Tiện ích khởi tạo và bảo trì
│   ├── init_db.sh (và init_db.ps1)        # Tạo dữ liệu mẫu: 3.000 sinh viên, 200 lớp học phần
│   ├── seed_cache.sh (và seed_cache.ps1)  # Đẩy trước thông tin môn học và sĩ số vào bộ nhớ đệm
│   └── warmup_cache.py                    # Script tự động thực hiện Pre-warming Cache toàn diện
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

## 4. Đặc tả UI/UX Tích hợp theo Chuẩn Google Stitch

Bám sát Design Theme trích xuất trực tiếp từ [Stitch Project 1242719912165769412](https://stitch.withgoogle.com/projects/1242719912165769412):
- **Theme Name:** Academic Registrar Grid
- **Màu sắc chủ đạo:**
  - `Primary (#1E3A8A)`: Deep Academic Blue - Thanh điều hướng, header, khung bố cục chính.
  - `Secondary (#2563EB)`: Royal Blue - Nút thao tác đăng ký "Đăng ký học phần", CTA chính.
  - `Tertiary / Success (#10B981)`: Emerald Green - Lớp còn chỗ, đăng ký thành công, xác nhận SSE.
  - `Warning (#F59E0B)`: Amber Orange - Lớp sắp hết chỗ ($< 5$ slots), trạng thái hàng đợi chờ duyệt.
  - `Danger (#EF4444)`: Crimson Red - Lớp hết chỗ, trùng lịch học, vi phạm môn tiên quyết.
  - `Canvas Background (#F8FAFC)` & Surface Containers Pure White (`#FFFFFF`).
- **Typography & Hiển thị số liệu:**
  - Font: **Inter**.
  - Quy tắc hiển thị: Mọi đồng hồ đếm ngược, số thứ tự hàng đợi (Queue Position), số lượng slot còn lại, số tín chỉ bắt buộc sử dụng CSS:
    `font-variant-numeric: tabular-nums lining-nums;` để triệt tiêu hiện tượng giật rung giao diện (layout shift) khi nhận dữ liệu realtime từ SSE.
- **5 Màn hình Giao diện:**
  1. `Đăng ký học phần - Cổng Đào tạo Đại học`: Bảng danh mục môn học, thanh tìm kiếm tức thì, bộ lọc ngành, ma trận thời khóa biểu tuần trực quan.
  2. `Kết Quả Đăng Ký & Dashboard Sinh Viên`: Tổng hợp các học phần đã ghi danh, tiến độ tín chỉ, in phiếu đăng ký.
  3. `Feedback & Exception Modals Showcase`: Hộp thoại modal hiển thị tức thì khi xảy ra `SectionFullException` hoặc `ScheduleConflictException`.
  4. `Kế hoạch Đăng ký & Trung tâm Xử lý Đồng thời`: Quản lý danh sách môn dự kiến (Course Cart) trước giờ G.
  5. `Phòng chờ Ảo & Trạng thái Hàng đợi (Virtual Waiting Room)`: Giao diện hàng đợi thời gian thực, hiển thị vị trí hàng đợi và tiến trình xử lý thông điệp từ RabbitMQ.
