import { CourseSectionDTO, RegisterRequestPayload, TicketStatusDTO } from '../types/registration';

const API_BASE = '/api/v1';

export function generateIdempotencyKey(studentId: string, sectionId: string): string {
  const windowTime = Math.floor(Date.now() / 5000); // 5-second window
  return `${studentId}-${sectionId}-${windowTime}-${Math.random().toString(36).substring(2, 7)}`;
}

export async function fetchSections(): Promise<CourseSectionDTO[]> {
  const res = await fetch(`${API_BASE}/sections`);
  if (!res.ok) {
    throw new Error(`Lỗi tải danh mục lớp học phần: ${res.statusText}`);
  }
  return await res.json();
}

export async function submitRegistration(
  payload: RegisterRequestPayload,
  token?: string
): Promise<{ ticket_id: string; status: string; message: string }> {
  const idempotencyKey = generateIdempotencyKey(payload.student_id || 'std-0001', payload.section_id);
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Idempotency-Key': idempotencyKey,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  } else if (payload.student_id) {
    headers['X-Student-Id'] = payload.student_id;
  }

  const res = await fetch(`${API_BASE}/registrations`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const errorMessage = errorData.detail || `Lỗi đăng ký (HTTP ${res.status})`;
    const err = new Error(errorMessage) as any;
    err.status = res.status;
    throw err;
  }

  return await res.json();
}

export async function fetchRegistrationStatus(ticketId: string): Promise<TicketStatusDTO> {
  const res = await fetch(`${API_BASE}/registrations/status/${ticketId}`);
  if (!res.ok) {
    throw new Error(`Lỗi kiểm tra trạng thái vé ${ticketId}`);
  }
  return await res.json();
}

export async function dropRegistration(
  registrationId: string,
  sectionId: string,
  credits: number,
  mask: number,
  studentId: string
): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/registrations/${registrationId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      'X-Student-Id': studentId,
    },
    body: JSON.stringify({
      section_id: sectionId,
      credits,
      section_time_mask: mask,
      student_id: studentId,
    }),
  });

  if (!res.ok) {
    throw new Error(`Lỗi hủy học phần: ${res.statusText}`);
  }
  return await res.json();
}
