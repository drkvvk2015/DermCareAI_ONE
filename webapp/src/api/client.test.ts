import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, api } from './client';

let user: never;

beforeEach(() => {
  user = { getIdToken: vi.fn().mockResolvedValue('synthetic-id-token') } as never;
});

afterEach(() => vi.unstubAllGlobals());

describe('clinical API client', () => {
  it('uses a bearer token and GET for patient summaries', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ patient_id: 'synthetic-patient', encounters: [], lesions: [], followups: [], signoffs: [] }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await api.clinicalSummary('synthetic patient', user);

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/clinical/patients/synthetic%20patient/summary',
      { method: 'GET', headers: { Authorization: 'Bearer synthetic-id-token', Accept: 'application/json' } },
    );
  });

  it('distinguishes unauthorized and forbidden responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401 }));
    await expect(api.prescriptions('synthetic-patient', user)).rejects.toMatchObject({ status: 401 });

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 403 }));
    await expect(api.procedures('synthetic-patient', user)).rejects.toMatchObject({ status: 403 });
    expect(new ApiError(403, 'denied')).toBeInstanceOf(Error);
  });

  it('surfaces a safe network-required error without exposing rejected request details', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('sensitive request detail')));
    await expect(api.clinicalSummary('synthetic-patient', user)).rejects.toMatchObject({
      status: 0,
      message: 'The request needs a network connection. Check your connection and try again.',
    });
  });

  it('surfaces a safe error when the signed-in user cannot obtain a token', async () => {
    const unavailableUser = { getIdToken: vi.fn().mockRejectedValue(new Error('token detail')) } as never;
    await expect(api.procedures('synthetic-patient', unavailableUser)).rejects.toMatchObject({
      status: 0,
      message: 'The request needs a network connection. Check your connection and try again.',
    });
  });

  it('does not expose content from an invalid API response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => { throw new Error('unexpected response detail'); },
    }));
    await expect(api.prescriptions('synthetic-patient', user)).rejects.toMatchObject({
      status: 502,
      message: 'The server returned an unexpected response.',
    });
  });
});
