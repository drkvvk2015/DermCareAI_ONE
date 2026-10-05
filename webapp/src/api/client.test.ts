import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, api } from './client';

const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
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
      `${apiBase}/api/v1/clinical/patients/synthetic%20patient/summary`,
      { method: 'GET', headers: { Authorization: 'Bearer synthetic-id-token', Accept: 'application/json' } },
    );
  });

  it('creates a patient with bearer auth and an idempotency key', async () => {
    const payload = {
      name: 'Synthetic Patient',
      age: 42,
      gender: 'female' as const,
      phone: '',
      email: '',
      address: '',
      medicalHistory: '',
      allergies: '',
      currentMedications: '',
    };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 'synthetic-patient-id' }) });
    vi.stubGlobal('fetch', fetchMock);

    await expect(api.createPatient(payload, user, 'synthetic-idempotency-key')).resolves.toEqual({ id: 'synthetic-patient-id' });

    expect(fetchMock).toHaveBeenCalledWith(`${apiBase}/api/v1/clinical/patients`, {
      method: 'POST',
      headers: {
        Authorization: 'Bearer synthetic-id-token',
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'Idempotency-Key': 'synthetic-idempotency-key',
      },
      body: JSON.stringify(payload),
    });
  });

  it('distinguishes unauthorized and forbidden responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401 }));
    await expect(api.prescriptions('synthetic-patient', user)).rejects.toMatchObject({ status: 401 });

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 403 }));
    await expect(api.procedures('synthetic-patient', user)).rejects.toMatchObject({ status: 403 });
    expect(new ApiError(403, 'denied')).toBeInstanceOf(Error);
  });
});
