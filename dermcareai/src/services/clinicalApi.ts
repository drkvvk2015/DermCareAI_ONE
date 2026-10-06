import { API_URL } from '@env';
import { auth } from '../config/firebase';
import { ClinicalApiError } from '../types/clinicalApi';

async function authorizedRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const user = auth.currentUser;
  if (!user) throw new Error('Authentication required');
  const token = await user.getIdToken();
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.headers || {}),
      Authorization: `Bearer ${token}`,
    },
  });
  const body = await response.text();
  if (!response.ok) {
    let detail: unknown = body;
    try { detail = body ? JSON.parse(body).detail ?? body : body; } catch { /* preserve raw body */ }
    const message = typeof detail === 'string' ? detail : JSON.stringify(detail);
    throw new ClinicalApiError(message, response.status, message, response.headers.get('X-Request-ID') ?? undefined);
  }
  return body ? (JSON.parse(body) as T) : (undefined as T);
}

export type ActiveConsent = {
  patient_id: string;
  purpose: string;
  active: boolean;
};

export type NewPatientPayload = {
  name: string;
  age: number;
  gender: string;
  phone: string;
  email: string;
  address: string;
  medicalHistory: string;
  allergies: string;
  currentMedications: string;
};

function safePatientCreateMessage(status: number): string {
  if (status === 401) return 'Your session has expired. Sign in again.';
  if (status === 403) return 'You do not have permission to register patients.';
  if (status === 400 || status === 422) return 'The patient details were not accepted. Check the fields and try again.';
  if (status === 409) return 'This registration is already being processed. Wait a moment and try again.';
  if (status === 503) return 'The patient registry is temporarily unavailable. Try again shortly.';
  return `The patient could not be registered (${status}).`;
}

// Online-only by design: patient data is never written to the offline sync queue.
export const patientRegistrationApi = {
  async create(patient: NewPatientPayload, idempotencyKey: string): Promise<{ id: string }> {
    const user = auth.currentUser;
    if (!user) throw new Error('Authentication required');
    const token = await user.getIdToken();
    let response: Response;
    try {
      response = await fetch(`${API_URL}/api/v1/clinical/patients`, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
          'Idempotency-Key': idempotencyKey,
        },
        body: JSON.stringify(patient),
      });
    } catch {
      throw new ClinicalApiError('Cannot reach the server. The patient was not saved; check your connection and try again.');
    }
    if (!response.ok) {
      throw new ClinicalApiError(
        safePatientCreateMessage(response.status),
        response.status,
        undefined,
        response.headers.get('X-Request-ID') ?? undefined,
      );
    }
    let parsed: unknown;
    try { parsed = await response.json(); } catch { parsed = undefined; }
    const id = (parsed as { id?: unknown } | undefined)?.id;
    if (typeof id !== 'string' || !id) {
      throw new ClinicalApiError('The server returned an unexpected response.', 502);
    }
    return { id };
  },
};

export const clinicalApi = {
  getActiveConsent(patientId: string, purpose = 'clinical-image') {
    return authorizedRequest<ActiveConsent>(
      `/api/v1/clinical/consents/${encodeURIComponent(patientId)}/active?purpose=${encodeURIComponent(purpose)}`,
    );
  },

  recordExistingConsent(payload: {
    patientId: string;
    purpose: string;
    documentVersion: string;
  }) {
    return authorizedRequest('/api/v1/clinical/consents', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: payload.patientId,
        purpose: payload.purpose,
        document_version: payload.documentVersion,
        status: 'granted',
        granted_at: new Date().toISOString(),
      }),
    });
  },

  recordMedia(payload: {
    patientId: string;
    encounterId?: string;
    lesionId?: string;
    consentId?: string;
    consentPurpose?: string;
    objectUrl: string;
    kind: 'original' | 'processed' | 'dermoscopy' | 'histopathology' | 'other';
    sha256: string;
    mimeType: string;
    byteSize: number;
    capturedAt: string;
    retentionUntil?: string;
  }) {
    return authorizedRequest<Record<string, unknown>>('/api/v1/clinical/media', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: payload.patientId,
        encounter_id: payload.encounterId,
        lesion_id: payload.lesionId,
        consent_id: payload.consentId,
        consent_purpose: payload.consentPurpose || 'clinical-image',
        object_url: payload.objectUrl,
        kind: payload.kind,
        sha256: payload.sha256,
        mime_type: payload.mimeType,
        byte_size: payload.byteSize,
        captured_at: payload.capturedAt,
        retention_until: payload.retentionUntil,
      }),
    });
  },
};



export type ClinicalEncounter = {
  id: string;
  patient_id: string;
  appointment_id?: string | null;
  doctor_id: string;
  status: string;
  complaints: Record<string, unknown>;
  examination: Record<string, unknown>;
  assessment: Record<string, unknown>;
  plan: Record<string, unknown>;
  version: number;
  opened_at: string;
  closed_at?: string | null;
};

export type ClinicalFollowup = {
  id: string;
  encounter_id: string;
  patient_id: string;
  due_at: string;
  instructions: string;
  status: string;
};

export type ClinicalPatientSummary = {
  patient_id: string;
  encounters: ClinicalEncounter[];
  lesions: Array<Record<string, unknown>>;
  followups: ClinicalFollowup[];
  signoffs: Array<Record<string, unknown>>;
};

export type ClinicalAIReview = {
  media_id?: string | null;
  lesion_id?: string | null;
  id: string;
  request_id: string;
  model_name: string;
  model_provenance?: string | null;
  predicted_label: string;
  confidence: number;
  accepted: boolean;
  clinician_decision?: string | null;
  clinician_override_label?: string | null;
};

export const patientClinicalApi = {
  getSummary(patientId: string) {
    return authorizedRequest<ClinicalPatientSummary>(
      `/api/v1/clinical/patients/${encodeURIComponent(patientId)}/summary`,
    );
  },
};

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
  missing_information: string[];
  contraindications_flagged: string[];
  alternatives: string[];
  confidence_score: number;
  escalation_required: boolean;
  notes: string[];
};

export const guidelineApi = {
  sources() {
    return authorizedRequest<{ sources: Record<GuidelineSource, number> }>('/api/v1/dermatology/guidelines');
  },
  recommend(query: GuidelineQuery) {
    return authorizedRequest<{ matched: boolean; recommendation: GuidelineRecommendation | null }>(
      '/api/v1/dermatology/guidelines/recommend',
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(query) },
    );
  },
};

export type DermatologyTemplate = {
  condition: string;
  required_sections: string[];
  scoring_tools: string[];
};

export const dermatologyTemplateApi = {
  list() {
    return authorizedRequest<{ templates: DermatologyTemplate[] }>('/api/v1/clinical/templates');
  },
};

export const encounterApi = {
  create(patientId: string, payload?: {
    complaints?: Record<string, unknown>;
    examination?: Record<string, unknown>;
    assessment?: Record<string, unknown>;
    plan?: Record<string, unknown>;
    appointmentId?: string;
    template?: string;
  }) {
    return authorizedRequest<ClinicalEncounter>('/api/v1/clinical/encounters', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: patientId,
        appointment_id: payload?.appointmentId,
        template: payload?.template,
        complaints: payload?.complaints || {},
        examination: payload?.examination || {},
        assessment: payload?.assessment || {},
        plan: payload?.plan || {},
      }),
    });
  },

  get(encounterId: string) {
    return authorizedRequest<ClinicalEncounter>(
      `/api/v1/clinical/encounters/${encodeURIComponent(encounterId)}`,
    );
  },

  update(encounterId: string, expectedVersion: number, patch: {
    status?: string;
    complaints?: Record<string, unknown>;
    examination?: Record<string, unknown>;
    assessment?: Record<string, unknown>;
    plan?: Record<string, unknown>;
  }) {
    return authorizedRequest<ClinicalEncounter>(
      `/api/v1/clinical/encounters/${encodeURIComponent(encounterId)}`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          expected_version: expectedVersion,
          ...patch,
        }),
      },
    );
  },

  sign(encounterId: string, attestation: string) {
    return authorizedRequest(
      `/api/v1/clinical/encounters/${encodeURIComponent(encounterId)}/sign`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ attestation }),
      },
    );
  },

  addFollowup(encounterId: string, dueAt: string, instructions: string) {
    return authorizedRequest<ClinicalFollowup>(
      `/api/v1/clinical/encounters/${encodeURIComponent(encounterId)}/followups`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ due_at: dueAt, instructions }),
      },
    );
  },

  addAIReview(encounterId: string, payload: Omit<ClinicalAIReview, 'id' | 'clinician_decision' | 'clinician_override_label'>) {
    return authorizedRequest<ClinicalAIReview>(
      `/api/v1/clinical/encounters/${encodeURIComponent(encounterId)}/ai-reviews`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
    );
  },

  reviewAI(encounterId: string, reviewId: string, clinicianDecision: 'accepted' | 'overridden' | 'rejected', overrideLabel?: string) {
    return authorizedRequest<ClinicalAIReview>(
      `/api/v1/clinical/encounters/${encodeURIComponent(encounterId)}/ai-reviews/${encodeURIComponent(reviewId)}`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clinician_decision: clinicianDecision,
          clinician_override_label: overrideLabel,
        }),
      },
    );
  },



  recordMedia(payload: {
    patientId: string;
    encounterId?: string;
    lesionId?: string;
    consentId?: string;
    consentPurpose?: string;
    objectUrl: string;
    kind: 'original' | 'processed' | 'dermoscopy' | 'histopathology' | 'other';
    sha256: string;
    mimeType: string;
    byteSize: number;
    capturedAt: string;
    retentionUntil?: string;
  }) {
    return authorizedRequest<Record<string, unknown>>('/api/v1/clinical/media', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: payload.patientId,
        encounter_id: payload.encounterId,
        lesion_id: payload.lesionId,
        consent_id: payload.consentId,
        consent_purpose: payload.consentPurpose || 'clinical-image',
        object_url: payload.objectUrl,
        kind: payload.kind,
        sha256: payload.sha256,
        mime_type: payload.mimeType,
        byte_size: payload.byteSize,
        captured_at: payload.capturedAt,
        retention_until: payload.retentionUntil,
      }),
    });
  },

  listAIReviews(encounterId: string) {
    return authorizedRequest<ClinicalAIReview[]>(
      `/api/v1/clinical/encounters/${encodeURIComponent(encounterId)}/ai-reviews`,
    );
  },

  listMedia(patientId: string, encounterId?: string, lesionId?: string) {
    const params = new URLSearchParams();
    if (encounterId) params.set('encounter_id', encounterId);
    if (lesionId) params.set('lesion_id', lesionId);
    const query = params.toString();
    return authorizedRequest<Array<Record<string, unknown>>>(
      `/api/v1/clinical/patients/${encodeURIComponent(patientId)}/media${query ? `?${query}` : ''}`,
    );
  },

  lesionTimeline(patientId: string, lesionCode: string) {
    return authorizedRequest<Array<Record<string, unknown>>>(
      `/api/v1/clinical/patients/${encodeURIComponent(patientId)}/lesions/${encodeURIComponent(lesionCode)}/timeline`,
    );
  },
  saveLesion(payload: {
    patientId: string;
    encounterId: string;
    lesionCode: string;
    bodySite: string;
    laterality?: string;
    morphology: Record<string, unknown>;
    sizeMm?: number;
    durationDays?: number;
    evolution?: string;
    symptoms?: Record<string, unknown>;
    clinicalImpression?: string;
    differential?: string[];
  }) {
    return authorizedRequest(
      '/api/v1/clinical/lesions',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id: payload.patientId,
          encounter_id: payload.encounterId,
          lesion_code: payload.lesionCode,
          body_site: payload.bodySite,
          laterality: payload.laterality,
          morphology: payload.morphology,
          size_mm: payload.sizeMm,
          duration_days: payload.durationDays,
          evolution: payload.evolution,
          symptoms: payload.symptoms || {},
          clinical_impression: payload.clinicalImpression,
          differential: payload.differential || [],
        }),
      },
    );
  },

};
