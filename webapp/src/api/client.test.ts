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
});
