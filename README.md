# ĐỒ ÁN MÔN HỌC: THIẾT KẾ HỆ THỐNG ĐĂNG KÝ HỌC PHẦN TRỰC TUYẾN
## Phiếu Giao Đề Tài Số 08 — Quy Mô 3.000 Sinh Viên

Hệ thống đăng ký học phần trực tuyến chịu tải cao, giải quyết triệt để bài toán **tranh chấp tài nguyên đồng thời (Race Condition)** và **chống bán vượt sĩ số (Zero Overselling)** khi 3.000 sinh viên cùng truy cập vào thời điểm mở cổng đăng ký đầu giờ.

---

## 1. Bảng Phân Công Nhiệm Vụ Thành Viên (Khung SV1 – SV4)

Theo đúng quy định tại Phiếu giao đề 08 và Quy chế đồ án:

| Vai trò | Họ và Tên | Mã Sinh Viên | Nhiệm vụ kỹ thuật chính | Sản phẩm & Minh chứng nộp |
| :---: | :--- | :---: | :--- | :--- |
| **SV1** | *(Điền họ tên)* | *(Điền MSSV)* | Thiết kế kiến trúc tổng thể, mô hình C4, tính toán giả định tải (3.000 SV, peak 3.500 QPS đọc, 500 QPS ghi), tính toán dự trù CPU/RAM/băng thông. | Báo cáo Chương 1 & 2; Bảng tính toán tài nguyên & dung lượng. |
| **SV2** | *(Điền họ tên)* | *(Điền MSSV)* | Triển khai dịch vụ đăng ký mẫu, Backend FastAPI (2 nodes), xác thực JWT In-Memory, xây dựng giao diện Web React Vite có phòng chờ (Waiting Room). | Thư mục `src/backend/infrastructure/webserver`, `src/frontend/`. |
| **SV3** | *(Điền họ tên)* | *(Điền MSSV)* | Cấu hình lưu trữ và kiểm soát ghi: Redis Atomic Lua Script CAS, chống bán vượt chỗ, RabbitMQ Message Queue, Worker ghi CSDL và Compensating Rollback khi lỗi DB. | `src/backend/infrastructure/cache`, `worker.py`, `reservation_store.py`. |
| **SV4** | **(BẠN)** | **(MSSV CỦA BẠN)** | **Tạo tải, kiểm tra nhất quán và báo cáo:** Viết kịch bản kiểm thử tải tranh chấp 500 SV, thực nghiệm 3 mức tải (300, 1.500, 3.000 VUs), nghiệm thu KT1 - KT3 có Timestamp và dữ liệu đo gốc. | `tests/load_testing/run_all_acceptance_tests.py`, `acceptance_report.json`, `acceptance_report.md`. |

---

## 2. Kiến Trúc Kỹ Thuật & Công Nghệ

```
                                  [ Trình duyệt Web (3.000 Sinh viên) ]
                                                    │
                                                    ▼
                             [ Nginx Reverse Proxy & Load Balancer L7 ]
                                      (Port: 8088 / Round Robin)
                                        │                     │
                        ┌───────────────┴────────┐   ┌────────┴───────────────┐
                        ▼                        ▼   ▼                        ▼
              [ FastAPI Node 1 ]           [ Static UI Assets ]         [ FastAPI Node 2 ]
             (Port 8000, 2 workers)                                    (Port 8000, 2 workers)
                        │                                                         │
                        └────────────────────────┬────────────────────────────────┘
                                                 │
                                                 ▼
                                     [ Redis 7 In-Memory Engine ]
                           ├── Atomic Lua Script (Compare-And-Swap slot & SADD)
                           ├── Idempotency Key Set O(1) & Bitmask Thời khoá biểu
                           └── Active Sections Catalog Cache (< 0.5ms)
                                                 │
                                                 ▼ (Đẩy vé hợp lệ 202 Accepted)
                                    [ RabbitMQ Message Broker ]
                                     (Hấp thụ đột biến tải ghi)
                                                 │
                                                 ▼ (Worker tiêu thụ tuần tự)
                                    [ Async Background Worker ]
                                      (Compensating Rollback)
                                                 │
                                                 ▼ (ACID System of Record)
                                    [ PostgreSQL 16 Database ]
```

* **Backend:** FastAPI (Python 3.12), Pydantic v2, Asyncpg Connection Pool, PyJWT / Python-jose.
* **In-Memory Store:** Redis 7 (Single-threaded Atomic Lua Scripting O(1) CAS).
* **Message Broker:** RabbitMQ 3.13 Management.
* **Database:** PostgreSQL 16 Alpine.
* **Frontend:** React 18, Vite, TypeScript, TailwindCSS.
* **Giám sát:** Prometheus 3.5, Grafana 12, RedisInsight 2.7.

---

## 3. Hướng Dẫn Cài Đặt & Dựng Lại Hệ Thống (Reproducibility)

### Yêu cầu tiên quyết:
- Đã cài đặt **Docker Desktop** (hoặc Docker Engine trên Linux).
- Đã cài đặt **Python 3.12** (để chạy script test tải).

### Bước 1: Khởi động toàn bộ stack 7 container
~~~powershell
docker compose up -d
~~~
Hệ thống sẽ tự động khởi động và kiểm tra sức khỏe (Healthcheck) của toàn bộ các dịch vụ:
- **Ứng dụng Web Đăng ký:** `http://localhost:8088`
- **RabbitMQ Management:** `http://localhost:15682` (guest / guest)
- **Grafana Dashboard:** `http://localhost:3001` (admin / lab-admin)
- **RedisInsight:** `http://localhost:8001`

### Bước 2: Thiết lập môi trường Python ảo (trên máy trạm để test)
~~~powershell
python -m venv .venv
.venv\Scripts\pip install -r src/backend/requirements.txt
~~~

---

## 4. Hướng Dẫn Kiểm Thử Nghiệm Thu & Đo Tải (Dành Riêng Cho SV4)

### 4.1. Lệnh 1-Click Chạy Toàn Bộ Bộ Kiểm Thử (KT1, KT2, KT3 & Đo 3 Mức Tải)
~~~powershell
.venv\Scripts\python tests/load_testing/run_all_acceptance_tests.py
~~~

### 4.2. Ý nghĩa và Kết quả 3 Tiêu chí Nghiệm thu:
1. **KT1 (Đăng ký hợp lệ làm giảm đúng 1 chỗ):** Sinh viên gửi yêu cầu hợp lệ $\rightarrow$ Trả về HTTP 202, vé xác nhận `CONFIRMED`, sĩ số còn trống giảm từ 40 xuống 39.
2. **KT2 (Tranh chấp đồng thời 500 SV cho 30 slot cuối):** 500 sinh viên cùng gửi request dồn dập $\rightarrow$ Chính xác đúng 30 sinh viên nhận slot (HTTP 202), 470 sinh viên nhận thông báo hết chỗ (HTTP 409). **Tuyệt đối không bán vượt sĩ số (Zero Overselling)!**
3. **KT3 (Chống trùng lặp & Idempotency):** Gửi lại cùng Idempotency Key trả về đúng vé ban đầu; cùng sinh viên cố đăng ký lại lớp đã có bị từ chối 409 `ALREADY_REGISTERED`.

### 4.3. Bảng Kết Quả Đo 3 Mức Tải Đạt Được Thực Tế:
| Mức tải | Mô phỏng kịch bản | Tổng Requests (80% Read / 20% Write) | Thông lượng (RPS) | P95 Latency | Tỷ lệ lỗi 5xx |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Mức 1: Thấp** | Đợt đăng ký rải rác | 300 requests | **61.4 req/s** | 2.61s | **0.00%** |
| **Mức 2: Trung bình** | Mở đợt theo khối ngành | 1.500 requests | **66.1 req/s** | 3.02s | **0.00%** |
| **Mức 3: Cao điểm** | 3.000 SV ùa vào lúc 8h00 | 3.000 requests | **83.2 req/s** | 2.56s | **0.00%** |

*Toàn bộ dữ liệu đo gốc (Raw Data) và báo cáo có Timestamp được lưu tại:*
- Dữ liệu thô JSON: [`tests/load_testing/results/acceptance_report.json`](tests/load_testing/results/acceptance_report.json)
- Báo cáo Markdown: [`tests/load_testing/results/acceptance_report.md`](tests/load_testing/results/acceptance_report.md)
