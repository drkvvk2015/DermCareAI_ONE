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

export type NewEncounter = {
  patient_id: string;
  template?: string;
  appointment_id?: string;
  complaints: {
    chief_complaint: string;
    duration: string;
    [key: string]: unknown;
  };
  examination: {
    morphology: string;
    distribution: string;
    [key: string]: unknown;
  };
  assessment: {
    summary: string;
    [key: string]: unknown;
  };
  plan: {
    summary: string;
    [key: string]: unknown;
  };
};

export type NewLesion = {
  patient_id: string;
  encounter_id: string;
  lesion_code: string;
  body_site: string;
  laterality?: string;
  size_mm?: number;
  morphology?: Record<string, unknown>;
  clinical_impression?: string;
  differential?: string[];
};

export type AIPrediction = {
  request_id: string;
  class_name: string;
  confidence: number;
  model_used: string;
  visualization?: string;
  accepted: boolean;
  safety_reason: string;
  image_quality: {
    usable: boolean;
    reason?: string;
    [key: string]: unknown;
  };
  governance?: {
    model_name: string;
    model_provenance: string;
    clinical_use: string;
    [key: string]: unknown;
  };
};

export type AIReviewRecord = {
  id: string;
  request_id: string;
  model_name: string;
  predicted_label: string;
  confidence: number;
  accepted: boolean;
  clinician_decision?: 'accepted' | 'overridden' | 'rejected' | null;
  clinician_override_label?: string | null;
  reviewed_by?: string | null;
  created_at: string;
};

export type MedicationItem = {
  medicine_id: string;
  name: string;
  strength: string;
  dose: string;
  route: string;
  frequency: string;
  duration: string;
  quantity: number;
  instructions?: string;
};

export type NewPrescription = {
  patient_id: string;
  encounter_id: string;
  instructions: string;
  items: MedicationItem[];
};

async function parseErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const data = await response.json() as Record<string, unknown>;
    if (typeof data?.detail === 'string') return data.detail;
    if (typeof data?.detail === 'object' && data?.detail !== null) {
      const detailObj = data.detail as Record<string, unknown>;
      if (typeof detailObj.message === 'string') return detailObj.message;
    }
  } catch {
    // ignore parse error
  }
  return fallback;
}

async function postJson<T>(path: string, body: unknown, user: User, idempotencyKey?: string): Promise<T> {
  const token = await user.getIdToken();
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    Accept: 'application/json',
    'Content-Type': 'application/json',
  };
  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey;
  }
  const response = await fetch(`${apiBase}${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const message = await parseErrorMessage(
      response,
      response.status === 401
        ? 'Your session has expired. Sign in again.'
        : response.status === 403
          ? 'You do not have permission to perform this action.'
          : response.status === 409
            ? 'The action could not be completed due to a clinical state conflict.'
            : `The request failed (${response.status}).`
    );
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

async function patchJson<T>(path: string, body: unknown, user: User, idempotencyKey?: string): Promise<T> {
  const token = await user.getIdToken();
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    Accept: 'application/json',
    'Content-Type': 'application/json',
  };
  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey;
  }
  const response = await fetch(`${apiBase}${path}`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const message = await parseErrorMessage(response, `The update failed (${response.status}).`);
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

async function createPatientRequest(patient: NewPatient, user: User, idempotencyKey: string): Promise<{ id: string }> {
  const payload = await postJson<{ id: string }>('/api/v1/clinical/patients', patient, user, idempotencyKey);
  if (typeof payload?.id !== 'string') {
    throw new ApiError(502, 'The server returned an unexpected response.');
  }
  return { id: payload.id };
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

export const GUIDELINE_SOURCES = ['IADVL', 'AAD', 'BAD', 'NICE'] as const;
export type GuidelineSource = (typeof GUIDELINE_SOURCES)[number];

export type GuidelineQuery = {
  symptoms: string[];
  conditions: string[];
  medications: string[];
  allergies: string[];
  sources: GuidelineSource[];
};

export type GuidelineRecommendation = {
  summary: string;
  guideline_id: string;
  guideline_version: string;
  citations: string[];
  evidence_quality: string;
  approved_by: string;
  approved_on: string;
  source_identifier: string;
  publication_date: string;
  retrieved_at: string;
  evidence_status: 'current' | 'superseded' | 'conflicting';
  missing_information: string[];
  contraindications_flagged: string[];
  alternatives: string[];
  heuristic_score: number;
  escalation_required: boolean;
  notes: string[];
};

export type GuidelineResult = { matched: boolean; recommendation: GuidelineRecommendation | null };
export type GuidelineSources = Record<GuidelineSource, number>;

async function recommendGuideline(query: GuidelineQuery, user: User): Promise<GuidelineResult> {
  const token = await user.getIdToken();
  const response = await fetch(`${apiBase}/api/v1/dermatology/guidelines/recommend`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify(query),
  });
  if (!response.ok) {
    const message = response.status === 401
      ? 'Your session has expired. Sign in again.'
      : response.status === 403
        ? 'You do not have permission to use guideline support.'
        : response.status === 422
          ? 'The guideline query was not accepted. Check the terms and sources.'
          : `Guideline support is unavailable (${response.status}).`;
    throw new ApiError(response.status, message);
  }
  const payload = await response.json() as Record<string, unknown>;
  if (typeof payload?.matched !== 'boolean') throw new ApiError(502, 'The server returned an unexpected response.');
  return payload as unknown as GuidelineResult;
}

async function guidelineSources(user: User): Promise<GuidelineSources> {
  const payload = await getJson('/api/v1/dermatology/guidelines', user) as Record<string, unknown>;
  const sources = payload?.sources;
  if (typeof sources !== 'object' || sources === null) throw new ApiError(502, 'The server returned an unexpected response.');
  return sources as GuidelineSources;
}

export const api = {
  createPatient: createPatientRequest,
  recommendGuideline,
  guidelineSources,
  async clinicalSummary(patientId: string, user: User) {
    return asClinicalSummary(await getJson(`/api/v1/clinical/patients/${encodeURIComponent(patientId)}/summary`, user));
  },
  async prescriptions(patientId: string, user: User) {
    return asArray<Prescription>(await getJson(`/api/v1/prescriptions/patient/${encodeURIComponent(patientId)}`, user));
  },
  async procedures(patientId: string, user: User) {
    return asArray<Procedure>(await getJson(`/api/v1/dermatology/procedures/patients/${encodeURIComponent(patientId)}`, user));
  },
  async createEncounter(data: NewEncounter, user: User) {
    return postJson<Record<string, unknown>>('/api/v1/clinical/encounters', data, user);
  },
  async signEncounter(encounterId: string, attestation: string, user: User) {
    return postJson<Record<string, unknown>>(`/api/v1/clinical/encounters/${encodeURIComponent(encounterId)}/sign`, { attestation }, user);
  },
  async createLesion(data: NewLesion, user: User, idempotencyKey?: string) {
    return postJson<Record<string, unknown>>('/api/v1/clinical/lesions', data, user, idempotencyKey);
  },
  async predictImage(file: File, user: User): Promise<AIPrediction> {
    const token = await user.getIdToken();
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${apiBase}/predict`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/json',
      },
      body: formData,
    });
    if (!response.ok) {
      const message = await parseErrorMessage(response, `Prediction failed (${response.status}).`);
      throw new ApiError(response.status, message);
    }
    return response.json() as Promise<AIPrediction>;
  },
  async createAIReview(encounterId: string, data: {
    request_id: string;
    model_name: string;
    predicted_label: string;
    confidence: number;
    accepted: boolean;
    media_id?: string;
    lesion_id?: string;
  }, user: User): Promise<AIReviewRecord> {
    return postJson<AIReviewRecord>(`/api/v1/clinical/encounters/${encodeURIComponent(encounterId)}/ai-reviews`, data, user);
  },
  async decideAIReview(
    encounterId: string,
    reviewId: string,
    decision: 'accepted' | 'overridden' | 'rejected',
    overrideLabel: string | undefined,
    user: User
  ): Promise<AIReviewRecord> {
    return patchJson<AIReviewRecord>(
      `/api/v1/clinical/encounters/${encodeURIComponent(encounterId)}/ai-reviews/${encodeURIComponent(reviewId)}`,
      {
        clinician_decision: decision,
        clinician_override_label: overrideLabel || null,
      },
      user
    );
  },
  async listEncounterAIReviews(encounterId: string, user: User): Promise<AIReviewRecord[]> {
    return asArray<AIReviewRecord>(await getJson(`/api/v1/clinical/encounters/${encodeURIComponent(encounterId)}/ai-reviews`, user));
  },
  async createPrescription(data: NewPrescription, user: User, idempotencyKey?: string): Promise<Prescription> {
    return postJson<Prescription>('/api/v1/prescriptions', data, user, idempotencyKey);
  },
};
