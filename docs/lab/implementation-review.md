# Bản nâng cấp lab đăng ký học phần

Dự án phục vụ đăng ký/hủy học phần, kiểm tra sĩ số, tín chỉ, môn tiên quyết và lịch học. Bản nâng cấp biến các thành phần mô phỏng ban đầu thành một lab có thể đối soát kết quả từ trình duyệt đến PostgreSQL.

## Những phần đã triển khai

- Hai chế độ cùng nghiệp vụ: giao dịch PostgreSQL trực tiếp và Redis Lua + RabbitMQ + worker.
- JWT xác định sinh viên; máy chủ tự lấy dữ liệu học vụ. Idempotency và ticket bền vững bảo vệ trước thao tác lặp.
- Giữ chỗ nguyên tử, trạng thái chờ rõ ràng, xác nhận sau commit DB. Hủy và đăng ký lại dùng ticket ownership để job cũ không giải phóng chỗ mới.
- Phục hồi khi publish chưa rõ kết quả, giao lại message, hoặc Redis lỗi sau DB commit. Retry có giới hạn và DLQ để đối soát.
- Giao diện giữ trạng thái pending qua reload, hiển thị đăng ký thật và hủy theo registration ID thật.
- Compose, health/readiness, Prometheus, Grafana 14 panel, RedisInsight, collector CPU/RAM/network từ Docker Desktop.
- k6 flash 3.000 lượt đăng ký/500 VUs và sustained lên 3.000 VUs; reset riêng fixture benchmark, khóa runner và xác minh DB/Redis/hàng đợi.
- Sơ đồ Mermaid, hướng dẫn vận hành và kịch bản trình diễn 90 giây.

## Kiểm thử và rà soát

Ngày 08/11/2026: 46 kiểm thử Python chạy thành công, gồm Redis/PostgreSQL/RabbitMQ thật trong stack test riêng; 2 kiểm thử frontend thành công; TypeScript/Vite production build thành công. Kiểm thử PowerShell xác nhận runner thứ hai bị chặn trước khi gọi Docker.

Rà soát độc lập toàn nhánh phát hiện bốn lỗi quan trọng, đã có kiểm thử tái hiện rồi sửa:

1. Yêu cầu hủy cũ đến sau lần đăng ký mới phải kết thúc FAILED, không treo pending hoặc trả chỗ của ticket mới.
2. Hai yêu cầu hủy đồng thời cùng idempotency key phải trả cùng ticket.
3. Verify không được báo hợp lệ nếu còn message ready/unacked dù số bản ghi đã đúng.
4. Khóa phải bao phủ cả phiên đổi mode, chuẩn bị dữ liệu, bắn tải và đối soát.

Đã bổ sung kiểm thử broker thật nhận message trước khi client gặp timeout, nack/redelivery, Redis lỗi sau commit, và reset bị chặn bởi message unacked. Số đo tải và đối soát nằm ở `artifacts/benchmarks/`; không dùng các con số minh họa 25 ms/CPU 12% làm kết quả thực nghiệm.

## Quyết định triển khai

- Đưa Compose test lên sớm để kiểm chứng lưu trữ thật; phải duy trì cấu hình test cùng cấu hình runtime.
- Gộp triển khai hợp đồng operation của đăng ký/hủy/baseline vì cùng invariant giao dịch; bố cục file khác kế hoạch nhưng chỉ có một nơi quản lý chuyển trạng thái.
- Tính tín chỉ/lịch từ đăng ký CONFIRMED dưới khóa hàng sinh viên, tránh bảng trạng thái học vụ trùng lặp; đánh đổi thêm truy vấn DB và đã đưa vào phép đo.
- Dùng RegistrationService và worker hai queue chung, tránh các wrapper và consumer trùng logic; đánh đổi độ tách biệt theo từng task.
- Cổng lab 8088/15682 để cùng tồn tại stack cũ; các lệnh demo phải dùng đúng cổng mới.
- Thu CPU/RAM/network bằng Docker stats textfile để tương thích Docker Desktop; collector phải chạy riêng và dashboard có thời điểm mẫu để phát hiện số liệu cũ.
- Redis terminal metadata/idempotency có TTL 7 ngày, pending không tự hết hạn; PostgreSQL giữ lịch sử operation để đối soát và chống job cũ. Cần chính sách lưu trữ lịch sử trước khi vận hành lâu dài.
- Mã legacy không còn được mount vào application được giữ lại; không tính các endpoint cũ là tính năng đang hoạt động.

## Giới hạn

Lab trên một máy, Redis/PostgreSQL/RabbitMQ đơn nút; chưa chứng minh HA, replication, phục hồi sau mất toàn bộ Redis hay exactly-once xuyên nhiều hệ thống. JWT lab là công cụ demo, không thay hệ thống đăng nhập sản xuất. Biểu đồ chia ca là mô phỏng, không phải chứng cứ tiết kiệm chi phí. Sơ đồ cung cấp dạng `.mmd` để xuất bằng Mermaid/Draw.io; chưa có video trình diễn tự động.
