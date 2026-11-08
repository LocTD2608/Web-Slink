# Lab đăng ký học phần có giám sát

Hai FastAPI, PostgreSQL, Redis Lua và RabbitMQ. Hai chế độ ghi: PostgreSQL đồng bộ và Redis giữ chỗ + worker ghi DB. Không có HA đa máy, Redis Cluster, WebSocket/SSE hoặc batch insert. Giao diện polling chỉ báo thành công khi PostgreSQL đã commit.

## Chạy trên Windows

Cần Docker Desktop Linux containers, PowerShell, Python 3.12 cho collector host. Chạy ứng dụng Docker không cần cài Python/Node dependencies trên host.

~~~powershell
./scripts/lab.ps1 -Action Start
~~~

Lệnh build, dừng riêng API/worker lab trong lúc seed/warm cache, bảo toàn dữ liệu cũ, khởi chạy monitoring. Nếu có pending, warmup từ chối; chạy Recover rồi Start lại. Không dùng docker compose down -v.

| Công cụ | URL | Truy cập lab |
|---|---|---|
| Ứng dụng | http://localhost:8088 | Chọn sinh viên mẫu |
| Grafana | http://localhost:3001/d/course-lab | admin / lab-admin |
| Prometheus | http://localhost:9090/targets | Các target phải UP |
| RedisInsight | http://localhost:8001 | Thêm database host redis, port 6379 |
| RabbitMQ | http://localhost:15682 | guest / guest |

Cổng khác bản cũ để tránh xung đột. Mật khẩu/token lab chỉ dành cho dữ liệu mẫu trên máy cá nhân. Ngoài LAB_MODE, token demo bị tắt, bắt buộc JWT_SECRET riêng và JWT hợp lệ. Chưa có trang đăng nhập/SSO production.

Mở terminal thứ hai:

~~~powershell
./scripts/collect_container_metrics.ps1
~~~

Collector đọc Docker stats, xuất CPU theo số core, bộ nhớ theo bytes, RX/TX tích lũy. Grafana dùng rate cho tốc độ mạng. Panel tuổi mẫu cho biết collector còn hoạt động; thiếu dữ liệu không phải CPU bằng 0. Đây là số liệu container trong VM Linux, không phải toàn bộ Windows.

## Đo tải

~~~powershell
./scripts/lab.ps1 -Action Smoke -Mode RedisQueue
./scripts/lab.ps1 -Action Smoke -Mode Postgres
./scripts/lab.ps1 -Action Benchmark -Mode Both
./scripts/lab.ps1 -Action Sustained -Mode RedisQueue -VUs 3000
~~~

Flash: 500 VUs × 6 lượt = 3.000 yêu cầu từ 3.000 danh tính, tranh 60 chỗ. Không phải 3.000 VUs đồng thời. Sustained tăng đến 3.000 VUs riêng. Load generator và dịch vụ cùng chia sẻ laptop; máy có thể không đạt tải mục tiêu.

Benchmark chỉ làm sạch lớp bench-section/học kỳ bench-sem. Đóng admission trước reset, từ chối khi còn pending/ready/unacked, tăng generation mỗi lượt. Đừng chạy hai benchmark hoặc sửa dữ liệu học tập trong lúc đo. Nhánh Redis cache dữ liệu học tập từ DB; sau sửa dữ liệu gốc cần dừng API/worker và warm cache bằng Start.

Mỗi chế độ có warmup và ba lượt đo luân phiên. Cùng limits CPU/RAM, cùng Nginx/monitoring; baseline dùng transaction/khóa hàng, không thêm delay giả. JWT fixture khác nhau giúp rate limiter không gộp mọi người vào một IP; đây chưa phải cơ chế chống giả mạo production ở Nginx.

Kết quả ở artifacts/benchmarks: summary.json từ k6, verification.json từ DB/Redis, comparison.csv/md và manifest môi trường. fixture.json chứa JWT tạm, gitignore, không đưa vào slide hoặc commit.

Tách latency phản hồi đầu (phase register) và completion_duration (đã xác nhận DB). 409 chỉ tính hết chỗ khi error_code là SECTION_FULL. 400/401/429/5xx, timeout, đăng ký trùng được phân loại riêng. Ngưỡng p95 30 giây chỉ phát hiện treo, không phải SLA. Không dùng 25ms/CPU 12%/tiết kiệm 60% làm kết luận khi chưa đo.

## Đối soát và phục hồi

~~~powershell
./scripts/lab.ps1 -Action Verify
./scripts/lab.ps1 -Action Recover
docker compose exec -T redis redis-cli GET lab:section:bench-section:slots
docker compose exec -T redis redis-cli HLEN lab:section:bench-section:owners
docker compose exec -T postgres psql -U postgres -d course_reg -c "SELECT status, count(*) FROM registrations WHERE section_id='bench-section' GROUP BY status;"
docker compose exec -T postgres psql -U postgres -d course_reg -c "SELECT max_capacity,current_enrolled FROM course_sections WHERE id='bench-section';"
~~~

Sau flash: 60 CONFIRMED, enrolled 60; Redis thêm slots 0, owners 60, pending 0. HTTP 202 không thay phép kiểm này. Smoke 10 người dùng verify --expected 10 trong container.

Lua giữ chỗ cùng metadata PENDING nguyên tử; worker idempotent theo ticket. Publish timeout giữ trạng thái chưa rõ để đối soát. Worker retry lỗi hạ tầng ba lần rồi đưa thông tin lỗi vào DLQ, giữ pending để phục hồi. Lỗi nghiệp vụ xác định được ghi FAILED bền vững rồi trả chỗ theo ticket. Redis lỗi sau DB commit không được rollback DB.

Metadata vé và idempotency đã kết thúc trong Redis có TTL mặc định 7 ngày (OPERATION_RETENTION_SECONDS, tối thiểu 60 giây); pending không hết hạn tự động. Lịch sử operation trong PostgreSQL được giữ để đối soát và bảo vệ khỏi job cũ. Runner PowerShell giữ mutex toàn phiên; lệnh lab thứ hai bị từ chối.

Hủy chỉ cho CONFIRMED; DB CANCELLED trước, Redis trả chỗ sau. Hủy lặp không tăng sĩ số lần nữa. Chưa tự tái dựng pending sau mất toàn bộ Redis; không cam kết exactly-once xuyên ba hệ thống.

## Kiểm thử

~~~powershell
docker compose -p course-lab-test -f docker-compose.test.yml up -d --wait
$env:RUN_REAL_INTEGRATION='1'
python -m unittest discover -s tests -t .
cd src/frontend
npm ci
npm test -- --run
npm run build
~~~

Python host cần src/backend/requirements.txt; requirements.lock là snapshot Linux Docker đã kiểm chứng. Tests thật dùng PostgreSQL course_test ở 15432, Redis 16379 DB 15, RabbitMQ 15673. Fixture chỉ reset database có tên kết thúc _test. Không trỏ TEST_DATABASE_URL vào dữ liệu thật.

Nguồn .mmd: mở mermaid.live hoặc Insert → Advanced → Mermaid trong Draw.io để xuất SVG. Sơ đồ lab mô tả thực tế; sơ đồ proposed đánh dấu chưa triển khai. register-slide.lua chỉ minh họa, code thật ở reservation_store.py.

peak-shaving.csv mô phỏng chia đều bốn ca, không phải trace đo hoặc chứng cứ giảm chi phí. Hướng dẫn demo ở demo-90-seconds.md.

~~~powershell
./scripts/lab.ps1 -Action Stop
~~~

Stop giữ volumes; các container cũ course-reg-* không bị tác động.
