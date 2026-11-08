import { CourseSectionDTO, StudentProfile, TicketStatusDTO } from '../types/registration';
let token = '';
export function setToken(value: string) { token = value; }
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch('/api/v1' + path, {...init, headers: {
    'Content-Type':'application/json', ...(token ? {Authorization:'Bearer '+token} : {}), ...init.headers,
  }});
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(typeof data.detail === 'string' ? data.detail : 'Yêu cầu không hợp lệ') as Error & {ticket_id?:string};
    err.ticket_id = data.ticket_id;
    throw err;
  }
  return data;
}
export const loginDemo = (student_id: string) => request<{token:string; student:StudentProfile}>('/lab/token', {method:'POST',body:JSON.stringify({student_id})});
export const fetchSections = () => request<CourseSectionDTO[]>('/sections');
export const fetchStudentRegistrations = (id: string) => request<CourseSectionDTO[]>('/registrations/student/'+encodeURIComponent(id));
export const fetchRegistrationStatus = (id: string) => request<TicketStatusDTO>('/registrations/status/'+encodeURIComponent(id));
export const submitRegistration = (section_id: string, key: string) => request<TicketStatusDTO>('/registrations', {
  method:'POST',headers:{'X-Idempotency-Key':key},body:JSON.stringify({section_id}),
});
export const dropRegistration = (registration_id: string, key: string) => request<TicketStatusDTO>('/registrations/'+encodeURIComponent(registration_id), {
  method:'DELETE',headers:{'X-Idempotency-Key':key},
});
