import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate } from 'k6/metrics';

// Custom metrics theo dõi race condition
const successfulRegistrations = new Counter('successful_registrations');
const rejectedSectionFull = new Counter('rejected_section_full');
const unexpectedErrors = new Counter('unexpected_errors');

export const options = {
  // Bắn đồng thời 500 Virtual Users trong một khoảnh khắc để thử thách tính nguyên tử (Atomic CAS)
  scenarios: {
    flash_crowd_race: {
      executor: 'shared-iterations',
      vus: 500,
      iterations: 500,
      maxDuration: '30s',
    },
  },
  thresholds: {
    // Lớp sec-001 có đúng 30 slot: Kỳ vọng đúng 30 thành công và 470 bị từ chối
    'successful_registrations': ['count<=30'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost';

export default function () {
  const vuId = __VU;
  const studentId = `std-${String(vuId).padStart(4, '0')}`;
  const sectionId = 'sec-001'; // Lớp có đúng 30 slots

  const payload = JSON.stringify({
    section_id: sectionId,
    semester_id: 'sem-2024-1',
    prerequisite_course_code: 'NONE',
    section_time_mask: 7,
    credits: 3,
    student_id: studentId,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'X-Student-Id': studentId,
      'X-Idempotency-Key': `race-${studentId}-${sectionId}`,
    },
  };

  const res = http.post(`${BASE_URL}/api/v1/registrations`, payload, params);

  if (res.status === 200 || res.status === 202) {
    successfulRegistrations.add(1);
    check(res, {
      'Thành công giữ slot (HTTP 200/202)': (r) => r.status === 200 || r.status === 202,
    });
  } else if (res.status === 409 || res.status === 400) {
    rejectedSectionFull.add(1);
    check(res, {
      'Bị từ chối do hết chỗ hoặc trùng lặp (HTTP 409)': (r) => r.status === 409 || r.status === 400,
    });
  } else {
    unexpectedErrors.add(1);
  }

  sleep(0.1);
}
