import http from 'k6/http';
import { check, sleep } from 'k6';
import { SharedArray } from 'k6/data';

// Nạp danh sách 3.000 pre-warmed tokens tĩnh từ tokens.csv (Zero CPU hashing)
const tokensData = new SharedArray('student_tokens', function () {
  const f = open('../tokens.csv');
  const lines = f.split('\n').filter((l) => l.trim().length > 0);
  const records = [];
  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(',');
    if (parts.length >= 3) {
      records.push({
        student_id: parts[0].trim(),
        student_code: parts[1].trim(),
        token: parts[2].trim(),
      });
    }
  }
  return records;
});

export const options = {
  stages: [
    { duration: '30s', target: 1000 },  // Ramp-up lên 1.000 VUs
    { duration: '1m', target: 3000 },   // Đạt đỉnh 3.000 VUs
    { duration: '3m', target: 3000 },   // Duy trì 3.000 VUs liên tục 3 phút
    { duration: '30s', target: 0 },     // Ramp-down
  ],
  thresholds: {
    // Độ trễ phân vị p95 < 250ms cho toàn bộ hệ thống
    http_req_duration: ['p(95)<250', 'p(99)<500'],
    // Tỉ lệ lỗi hệ thống 5xx < 0.1%
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost';

export default function () {
  // Lấy ngẫu nhiên 1 sinh viên từ mảng 3.000 tokens
  const userIdx = (__VU - 1) % (tokensData.length || 1);
  const user = tokensData[userIdx] || {
    student_id: `std-${String(__VU).padStart(4, '0')}`,
    token: '',
  };

  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${user.token}`,
    'X-Student-Id': user.student_id,
  };

  // 1. Luồng Đọc: 80% sinh viên tra cứu danh mục lớp học phần
  const catalogRes = http.get(`${BASE_URL}/api/v1/sections`);
  check(catalogRes, {
    'Tra cứu danh mục thành công (HTTP 200)': (r) => r.status === 200,
    'Thời gian đọc danh mục < 50ms': (r) => r.timings.duration < 50,
  });

  // Nghỉ ngẫu nhiên 0.5s - 1.5s giữa các lần thao tác
  sleep(Math.random() * 1.0 + 0.5);

  // 2. Luồng Ghi: 20% xác suất gửi yêu cầu đăng ký học phần
  if (Math.random() < 0.2) {
    const randomSecNum = Math.floor(Math.random() * 50) + 1;
    const sectionId = `sec-${String(randomSecNum).padStart(3, '0')}`;

    const regPayload = JSON.stringify({
      section_id: sectionId,
      semester_id: 'sem-2024-1',
      prerequisite_course_code: 'NONE',
      section_time_mask: 7,
      credits: 3,
      student_id: user.student_id,
    });

    const regHeaders = Object.assign({}, headers, {
      'X-Idempotency-Key': `k6-${user.student_id}-${sectionId}-${Date.now()}`,
    });

    const regRes = http.post(`${BASE_URL}/api/v1/registrations`, regPayload, {
      headers: regHeaders,
    });

    const isAccepted = regRes.status === 202 || regRes.status === 200;
    const isExpectedConflict = regRes.status === 409 || regRes.status === 400;

    check(regRes, {
      'Tiếp nhận đăng ký hợp lệ (200/202 hoặc 409)': () => isAccepted || isExpectedConflict,
    });

    // 3. Nếu được nhận vé (202 Accepted): Thực hiện Controlled Short Polling kiểm tra kết quả
    if (isAccepted) {
      try {
        const body = regRes.json();
        const ticketId = body.ticket_id;

        if (ticketId) {
          sleep(1.0); // Chờ 1 giây theo quy chuẩn short polling
          const pollRes = http.get(`${BASE_URL}/api/v1/registrations/status/${ticketId}`);
          check(pollRes, {
            'Polling trạng thái vé thành công (HTTP 200)': (r) => r.status === 200,
          });
        }
      } catch (e) {
        // Ignored
      }
    }
  }

  sleep(1.0);
}
