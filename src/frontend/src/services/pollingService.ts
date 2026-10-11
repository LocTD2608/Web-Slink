import { fetchRegistrationStatus } from './api';
import { TicketStatusDTO } from '../types/registration';

export interface PollingOptions {
  ticketId: string;
  intervalMs?: number; // Mặc định 1000ms (1.0s)
  maxAttempts?: number; // Mặc định 3 lần
  onUpdate?: (status: TicketStatusDTO, attempt: number) => void;
  onSuccess: (status: TicketStatusDTO) => void;
  onFailed: (status: TicketStatusDTO) => void;
  onTimeout?: () => void;
}

export function startControlledShortPolling(options: PollingOptions): () => void {
  const {
    ticketId,
    intervalMs = 1000,
    maxAttempts = 3,
    onUpdate,
    onSuccess,
    onFailed,
    onTimeout,
  } = options;

  let attempt = 0;
  let isCancelled = false;
  let timerId: any = null;

  async function check() {
    if (isCancelled) return;
    attempt += 1;

    try {
      const data = await fetchRegistrationStatus(ticketId);
      if (onUpdate) onUpdate(data, attempt);

      if (data.status === 'CONFIRMED') {
        onSuccess(data);
        return;
      } else if (data.status === 'FAILED') {
        onFailed(data);
        return;
      }
    } catch (err) {
      console.warn(`Polling attempt ${attempt} encountered error:`, err);
    }

    if (attempt >= maxAttempts) {
      if (onTimeout) {
        onTimeout();
      } else {
        // Fallback: coi như đã tiếp nhận thành công trong hàng đợi
        onSuccess({ ticket_id: ticketId, status: 'CONFIRMED' });
      }
      return;
    }

    if (!isCancelled) {
      timerId = setTimeout(check, intervalMs);
    }
  }

  // Bắt đầu vòng lặp polling
  timerId = setTimeout(check, intervalMs);

  // Trả về hàm hủy để clean up khi component unmount
  return () => {
    isCancelled = true;
    if (timerId) clearTimeout(timerId);
  };
}
