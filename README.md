# Hệ thống đăng ký học phần — lab thực hành

Ứng dụng React + FastAPI, PostgreSQL, Redis Lua và RabbitMQ. Bản nâng cấp có hai chế độ đăng ký để đo đối chứng, trạng thái bất đồng bộ đúng theo kết quả DB, cùng Prometheus/Grafana/RedisInsight.

- Đăng ký, hủy và đăng ký lại; kiểm tra chủ sở hữu JWT, tiên quyết, tín chỉ, trùng lịch.
- Lua giữ chỗ và ticket nguyên tử; worker xử lý idempotent, có recovery.
- Frontend dùng sinh viên demo, lưu ticket khi tải lại trang; timeout không báo thành công.
- Benchmark 3.000 yêu cầu tranh 60 chỗ; kịch bản 3.000 VUs riêng.
- Dashboard provision sẵn: API, worker, queue, Redis, PostgreSQL, CPU/RAM/network container.

~~~powershell
./scripts/lab.ps1 -Action Start
~~~

Ứng dụng: http://localhost:8088. Grafana: http://localhost:3001 (admin / lab-admin). RedisInsight: http://localhost:8001.

Đọc [hướng dẫn chạy và đo tải](docs/lab/README.md), [kịch bản demo 90 giây](docs/lab/demo-90-seconds.md), [thiết kế được duyệt](docs/superpowers/specs/2026-11-07-observable-registration-lab-design.md).

Đọc [kết quả kiểm thử và quyết định triển khai](docs/lab/implementation-review.md). Số liệu đo nằm trong artifacts/benchmarks khi chạy. Không coi mục tiêu 3.000 VUs là kết quả đã chứng minh nếu không có artifact tương ứng. Các tài liệu phân tích ban đầu trong docs/01_* đến docs/05_* và spec tháng 10 mô tả ý tưởng cũ; docs/lab là hướng dẫn hiện hành. Đây là lab trên một máy, chưa phải hệ thống production HA hoặc cổng SSO trường học.

