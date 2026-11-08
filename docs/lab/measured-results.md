# Kết quả đo ngày 08/11/2026

Máy Windows, Ryzen 7 4800H (16 logical CPUs), RAM 15,42 GiB, Docker Desktop. Hai API giới hạn **1 CPU + 512 MiB mỗi container**, Nginx 0,5 CPU + 128 MiB. Stack dự án cũ vẫn chạy; stack kiểm thử riêng đã dừng trước phép đo. Đây là môi trường dùng chung, không phải năng lực production hay benchmark độc lập phần cứng.

## Flash: 3.000 lượt đăng ký tranh 60 chỗ

500 VUs × 6 lượt, định danh riêng từng lượt. Warmup mỗi chế độ; ba lượt đo luân phiên mỗi chế độ. Cùng nghiệp vụ, giới hạn tài nguyên và dữ liệu. Không thêm độ trễ giả vào PostgreSQL.

| Chế độ | Trung vị avg phản hồi | Trung vị p95 phản hồi | Trung vị p95 hoàn tất của 60 người thành công |
|---|---:|---:|---:|
| PostgreSQL trực tiếp | 7.125,30 ms | 11.546,14 ms | 4.672,00 ms |
| Redis Lua + RabbitMQ | 704,85 ms | 4.059,81 ms | 2.700,60 ms |

**Cả 6 lượt:** 60 CONFIRMED, 2.940 SECTION_FULL, 0 unexpected. Mỗi lượt Redis có slots 0, owners 60, pending 0, queue rỗng, tín chỉ/lịch giữ chỗ đúng. Thời gian hoàn tất chỉ đo trên 60 người thành công; không so trực tiếp phân vị này với phân vị phản hồi của toàn bộ 3.000 người.

Redis nhanh hơn baseline trong phép đo này, nhưng **không đạt p95 dưới 25 ms**. Cả baseline dùng khóa và Redis đều không vượt sĩ số.

## Tải duy trì

Ramp 30 giây, giữ đỉnh 60 giây, giảm 10 giây; mỗi VU đọc toàn bộ danh mục, 20% vòng lặp thêm đăng ký, nghỉ 1–2 giây. Đây là workload khác flash.

| Đỉnh VUs | Tổng HTTP | HTTP/giây | p95 HTTP | Unexpected | Kết luận |
|---|---:|---:|---:|---:|---|
| 3.000, Nginx 4.096 connections | 84.958 | 727,47 | 3.216,84 ms | 74.559 | Không đạt; nhiều lỗi phản hồi nhanh |
| 3.000, Nginx 8.192 connections | 43.811 | 430,68 | 57.658,43 ms | 32.482 | Không đạt; timeout và 5xx |
| 300, Nginx 8.192 connections | 12.332 | 121,56 | 1.625,96 ms | 0 | Đạt ngưỡng không lỗi của kịch bản |

Lượt đầu có log `4096 worker_connections are not enough`; đã tăng connections lên 8.192 và file limit lên 16.384. Lượt chạy lại hết giới hạn này nhưng hai API dùng khoảng 100% quota 1 CPU mỗi container; Nginx sau timeout báo upstream không khả dụng. Redis/PostgreSQL không chạm quota trong mẫu quan sát đó. **Chưa chứng minh phục vụ ổn định 3.000 người đồng thời.** Mức 300 VUs là mốc đã kiểm chứng, không phải công suất tối đa đã tìm được.

Sau cả hai lượt lỗi, đối soát riêng vẫn có 60 bản ghi, slots 0, owners 60, pending 0 và queue rỗng. Trường `valid` trong verification JSON chỉ nói về **toàn vẹn dữ liệu**, không thay kết quả threshold k6. Trong lượt 300 VUs có thêm một số thao tác kiểm tra giao diện thủ công, không nằm trong bộ đếm k6.

## Bằng chứng

- [Thống kê từng lượt](../../artifacts/benchmarks/comparison.md). Hàng sustained không có metric `phase:register`, nên latency trong báo cáo flash để None; dùng bảng trên và summary sustained.
- [Manifest](../../artifacts/benchmarks/measurement-manifest.json): môi trường, SHA256 summary, thời gian gần đúng và CPU/RAM cực đại theo mẫu Prometheus. Collector lấy mẫu vài giây/lần; không phải cực đại tức thời.
- [Giám sát](../../artifacts/benchmarks/monitoring-targets.json): 7 target UP sau đo.
- File `sustained-300*-verification.json` giữ `run_id` gốc; tên file đã đổi để lưu riêng các mức VUs. Nội dung kết quả không đổi.
- Sáu lượt flash dùng connections 4.096; sustained sau sửa dùng 8.192. CPU/RAM không đổi.

Theo [runbook](README.md) để chạy lại. Không trình bày 500 VUs × 6 iterations như 3.000 kết nối đồng thời. Giao diện đã được kiểm tra đăng ký, reload giữ kết quả, hủy, đăng ký lại và chuyển sinh viên; Grafana đã được quan sát với dữ liệu thật. Header đã sửa lỗi chồng chữ ở viewport hẹp. RedisInsight đang chạy; lần mở đầu còn màn hình điều khoản/cài đặt, sau đó thêm kết nối `redis:6379` theo runbook.
