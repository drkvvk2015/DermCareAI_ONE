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

  it('creates an encounter with core clinical documentation fields', async () => {
    const payload = {
      patient_id: 'P-123',
      complaints: { chief_complaint: 'Rash', duration: '2 weeks' },
      examination: { morphology: 'Plaque', distribution: 'Extensors' },
      assessment: { summary: 'Psoriasis' },
      plan: { summary: 'Topical steroids' },
    };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 'ENC-1', status: 'open' }) });
    vi.stubGlobal('fetch', fetchMock);

    await expect(api.createEncounter(payload, user)).resolves.toEqual({ id: 'ENC-1', status: 'open' });
    expect(fetchMock).toHaveBeenCalledWith(`${apiBase}/api/v1/clinical/encounters`, {
      method: 'POST',
      headers: {
        Authorization: 'Bearer synthetic-id-token',
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
  });

  it('signs an encounter with doctor attestation', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 'SIG-1', status: 'signed' }) });
    vi.stubGlobal('fetch', fetchMock);

    await expect(api.signEncounter('ENC-1', 'I reviewed all clinical documentation.', user)).resolves.toEqual({ id: 'SIG-1', status: 'signed' });
    expect(fetchMock).toHaveBeenCalledWith(`${apiBase}/api/v1/clinical/encounters/ENC-1/sign`, {
      method: 'POST',
      headers: {
        Authorization: 'Bearer synthetic-id-token',
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ attestation: 'I reviewed all clinical documentation.' }),
    });
  });

  it('creates a lesion observation record', async () => {
    const payload = {
      patient_id: 'P-123',
      encounter_id: 'ENC-1',
      lesion_code: 'L-01',
      body_site: 'face',
      laterality: 'left',
      size_mm: 5.5,
      clinical_impression: 'Atypical nevus',
    };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 'LES-1' }) });
    vi.stubGlobal('fetch', fetchMock);

    await expect(api.createLesion(payload, user)).resolves.toEqual({ id: 'LES-1' });
    expect(fetchMock).toHaveBeenCalledWith(`${apiBase}/api/v1/clinical/lesions`, {
      method: 'POST',
      headers: {
        Authorization: 'Bearer synthetic-id-token',
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
  });

  it('submits an image for AI prediction and decision support', async () => {
    const file = new File(['fake-image-bytes'], 'test.jpg', { type: 'image/jpeg' });
    const responsePayload = {
      request_id: 'REQ-1',
      class_name: 'Melanoma Risk Signal',
      confidence: 0.88,
      model_used: 'MobileNetV2',
      accepted: true,
      safety_reason: '',
      image_quality: { usable: true },
    };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => responsePayload });
    vi.stubGlobal('fetch', fetchMock);

    const result = await api.predictImage(file, user);
    expect(result.class_name).toBe('Melanoma Risk Signal');
    expect(fetchMock).toHaveBeenCalledWith(
      `${apiBase}/predict`,
      expect.objectContaining({
        method: 'POST',
        headers: {
          Authorization: 'Bearer synthetic-id-token',
          Accept: 'application/json',
        },
      }),
    );
  });

  it('records an AI assessment and patches clinician decision', async () => {
    const createPayload = {
      request_id: 'REQ-1',
      model_name: 'MobileNetV2',
      predicted_label: 'Melanoma',
      confidence: 0.9,
      accepted: true,
    };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 'AIR-1', ...createPayload }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 'AIR-1', clinician_decision: 'accepted' }) });
    vi.stubGlobal('fetch', fetchMock);

    const created = await api.createAIReview('ENC-1', createPayload, user);
    expect(created.id).toBe('AIR-1');

    const decided = await api.decideAIReview('ENC-1', 'AIR-1', 'accepted', undefined, user);
    expect(decided.clinician_decision).toBe('accepted');
  });

  it('creates an authoritative prescription with medication items', async () => {
    const payload = {
      patient_id: 'P-123',
      encounter_id: 'ENC-1',
      instructions: 'Apply once daily',
      items: [{
        medicine_id: 'MED-1',
        name: 'Mometasone Cream',
        strength: '0.1%',
        dose: 'Thin layer',
        route: 'Topical',
        frequency: 'Daily',
        duration: '7 days',
        quantity: 1,
      }],
    };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 'RX-1', status: 'active' }) });
    vi.stubGlobal('fetch', fetchMock);

    await expect(api.createPrescription(payload, user)).resolves.toEqual({ id: 'RX-1', status: 'active' });
    expect(fetchMock).toHaveBeenCalledWith(`${apiBase}/api/v1/prescriptions`, {
      method: 'POST',
      headers: {
        Authorization: 'Bearer synthetic-id-token',
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
  });

  it('requests guideline suggestions for selected sources with bearer auth', async () => {
    const query = { symptoms: ['itching'], conditions: [], medications: [], allergies: [], sources: ['NICE' as const, 'BAD' as const] };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ matched: false, recommendation: null }) });
    vi.stubGlobal('fetch', fetchMock);

    await expect(api.recommendGuideline(query, user)).resolves.toEqual({ matched: false, recommendation: null });

    expect(fetchMock).toHaveBeenCalledWith(`${apiBase}/api/v1/dermatology/guidelines/recommend`, {
      method: 'POST',
      headers: { Authorization: 'Bearer synthetic-id-token', Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(query),
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
