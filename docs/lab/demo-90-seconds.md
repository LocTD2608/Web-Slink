# Trình diễn 90 giây

Chuẩn bị: Start, chạy collector, smoke hai chế độ; chọn redis_queue, prepare dataset trống, kiểm tra targets UP. Không reset khi đang có tải. Đăng nhập Grafana, cấu hình RedisInsight host redis:6379.

Chia màn hình bốn cửa sổ: Grafana; docker stats; RedisInsight/SQL; k6.

0–15 giây: giới thiệu “3.000 yêu cầu từ 500 kết nối đồng thời tranh 60 chỗ”; chỉ sơ đồ lab hai backend, không gọi là HA đa máy.

15–50 giây:

~~~powershell
docker compose --profile tools run --rm -e RUN_ID=demo k6 run --out experimental-prometheus-rw /scripts/scenarios/flash_sale_test.js
~~~

Quan sát biểu đồ thực tế; 202 là giữ chỗ, confirmed mới là ghi DB. Nếu máy xử lý lâu thì tiếp tục chờ, không cắt video che pending.

50–75 giây:

~~~powershell
docker compose exec -T fastapi-node-1 python -m scripts.benchmark verify --mode redis_queue --run-id demo
~~~

Refresh RedisInsight: slots 0, owners 60. SQL: CONFIRMED = 60, current_enrolled = 60. Đây là chứng cứ không vượt sĩ số trong lần chạy.

75–90 giây: mở comparison.md của ba lượt mỗi chế độ; so sánh latency phản hồi đầu với thời gian hoàn tất. Nếu Redis không nhanh hơn, trình bày nút thắt thật, không thay bằng số minh họa.

Dự phòng: quay nguyên trình tự và kết quả đối soát, lưu video kèm manifest và JSON. Chưa có video tạo tự động trong repo.
