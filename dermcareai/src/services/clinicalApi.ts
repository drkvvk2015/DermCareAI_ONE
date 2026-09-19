import { API_URL } from '@env';
import { auth } from '../config/firebase';

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
  if (!response.ok) throw new Error(body || `Clinical API error: ${response.status}`);
  return body ? (JSON.parse(body) as T) : (undefined as T);
}

export type ActiveConsent = {
  patient_id: string;
  purpose: string;
  active: boolean;
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

export const encounterApi = {
  create(patientId: string, payload?: {
    complaints?: Record<string, unknown>;
    examination?: Record<string, unknown>;
    assessment?: Record<string, unknown>;
    plan?: Record<string, unknown>;
    appointmentId?: string;
  }) {
    return authorizedRequest<ClinicalEncounter>('/api/v1/clinical/encounters', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: patientId,
        appointment_id: payload?.appointmentId,
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

  listAIReviews(encounterId: string) {
    return authorizedRequest<ClinicalAIReview[]>(
      `/api/v1/clinical/encounters/${encodeURIComponent(encounterId)}/ai-reviews`,
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
