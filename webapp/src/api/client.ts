import type { User } from 'firebase/auth';

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

export type ClinicalSummary = {
  patient_id: string;
  encounters: Array<Record<string, unknown>>;
  lesions: Array<Record<string, unknown>>;
  followups: Array<Record<string, unknown>>;
  signoffs: Array<Record<string, unknown>>;
};

export type Prescription = Record<string, unknown> & {
  id?: string;
  status?: string;
  items?: Array<Record<string, unknown>>;
  created_at?: string;
};

export type Procedure = Record<string, unknown> & {
  id?: string;
  procedure_type?: string;
  performed_at?: string;
};

const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export type NewPatient = {
  name: string;
  age: number;
  gender: 'male' | 'female' | 'other';
  phone: string;
  email: string;
  address: string;
  medicalHistory: string;
  allergies: string;
  currentMedications: string;
};

async function createPatientRequest(patient: NewPatient, user: User, idempotencyKey: string): Promise<{ id: string }> {
  const token = await user.getIdToken();
  const response = await fetch(`${apiBase}/api/v1/clinical/patients`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify(patient),
  });

  if (!response.ok) {
    const message = response.status === 401
      ? 'Your session has expired. Sign in again.'
      : response.status === 403
        ? 'You do not have permission to register patients.'
        : response.status === 400 || response.status === 422
          ? 'The patient details were not accepted. Check the fields and try again.'
          : response.status === 409
            ? 'This registration is already being processed. Wait a moment and try again.'
            : response.status === 503
              ? 'The patient registry is temporarily unavailable. Try again shortly.'
              : `The patient could not be registered (${response.status}).`;
    throw new ApiError(response.status, message);
  }
  const payload = await response.json() as unknown;
  if (typeof payload !== 'object' || payload === null || typeof (payload as Record<string, unknown>).id !== 'string') {
    throw new ApiError(502, 'The server returned an unexpected response.');
  }
  return { id: (payload as { id: string }).id };
}

async function getJson(path: string, user: User): Promise<unknown> {
  const token = await user.getIdToken();
  const response = await fetch(`${apiBase}${path}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' },
  });

  if (!response.ok) {
    const message = response.status === 401
      ? 'Your session has expired. Sign in again.'
      : response.status === 403
        ? 'You do not have permission to view this record.'
        : `The request could not be completed (${response.status}).`;
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<unknown>;
}

function asArray<T>(payload: unknown): T[] {
  if (!Array.isArray(payload)) throw new ApiError(502, 'The server returned an unexpected response.');
  return payload as T[];
}

function asClinicalSummary(payload: unknown): ClinicalSummary {
  if (typeof payload !== 'object' || payload === null) {
    throw new ApiError(502, 'The server returned an unexpected response.');
  }
  const value = payload as Record<string, unknown>;
  if (typeof value.patient_id !== 'string' ||
      !Array.isArray(value.encounters) ||
      !Array.isArray(value.lesions) ||
      !Array.isArray(value.followups) ||
      !Array.isArray(value.signoffs)) {
    throw new ApiError(502, 'The server returned an unexpected response.');
  }
  return value as ClinicalSummary;
}

export const api = {
  createPatient: createPatientRequest,
  async clinicalSummary(patientId: string, user: User) {
    return asClinicalSummary(await getJson(`/api/v1/clinical/patients/${encodeURIComponent(patientId)}/summary`, user));
  },
  async prescriptions(patientId: string, user: User) {
    return asArray<Prescription>(await getJson(`/api/v1/prescriptions/patient/${encodeURIComponent(patientId)}`, user));
  },
  async procedures(patientId: string, user: User) {
    return asArray<Procedure>(await getJson(`/api/v1/dermatology/procedures/patients/${encodeURIComponent(patientId)}`, user));
  },
};
