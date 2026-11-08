// @vitest-environment jsdom
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { App } from '../App';
vi.mock('../services/client', () => ({
  loginDemo:vi.fn(async () => ({token:'demo',student:{id:'std-0001',student_code:'SV1',full_name:'Demo',major:'CS',max_credits:24,current_credits:0}})),
  setToken:vi.fn(),
  fetchSections:vi.fn(async () => []),
  fetchStudentRegistrations:vi.fn(async () => []),
  fetchRegistrationStatus:vi.fn(async () => ({ticket_id:'pending-ticket',status:'PENDING'})),
  submitRegistration:vi.fn(),dropRegistration:vi.fn(),
}));
describe('operation restoration', () => {
  it('keeps an unresolved request visible after reload', async () => {
    localStorage.setItem('pending:std-0001','pending-ticket');
    render(<App />);
    await waitFor(() => expect(screen.getByText(/Yêu cầu đang xử lý/)).toBeTruthy());
    expect(screen.queryByText('Đăng ký thành công')).toBeNull();
  });
});
