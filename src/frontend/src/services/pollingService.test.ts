import { describe, it, expect, vi, afterEach } from 'vitest';
import { startControlledShortPolling } from './pollingService';
vi.mock('./api', () => ({fetchRegistrationStatus: vi.fn(async () => ({ticket_id:'t', status:'PENDING'}))}));

describe('pending operation', () => {
  afterEach(() => vi.useRealTimers());
  it('never invents confirmation after polling expires', async () => {
    vi.useFakeTimers();
    const success = vi.fn();
    const failed = vi.fn();
    startControlledShortPolling({ticketId:'t', maxAttempts:3, intervalMs:10, onSuccess:success, onFailed:failed});
    await vi.runAllTimersAsync();
    expect(success).not.toHaveBeenCalled();
    expect(failed).not.toHaveBeenCalled();
  });
});
