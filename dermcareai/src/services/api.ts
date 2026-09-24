import { Platform } from 'react-native';
import { auth } from '../config/firebase';
import { API_URL } from '@env';
import type { AIGovernanceCard } from '../types/platform';
import { ClinicalApiError } from '../types/clinicalApi';
import { flushSyncQueue, enqueuePersistentSync, clearSyncQueue, type SyncOperation, type SyncSendResult } from './syncQueue';

export const ABSTAIN_LABEL = 'Uncertain / Needs Clinical Review';

export type ImageQuality = {
  usable: boolean;
  reason: string;
  width: number;
  height: number;
  mean_luminance: number;
  luminance_variance: number;
  issues: string[];
};

export type PredictionResponse = {
  request_id: string;
  class_name: string;
  confidence: number;
  model_used: string;
  visualization: string;
  accepted: boolean;
  safety_reason: string;
  image_quality: ImageQuality;
  app_version: string;
  governance: AIGovernanceCard;
};

async function request(path: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(`${API_URL}${path}`, init);
  return response;
}

const OFFLINE_REPLAYABLE = new Set<string>([
  'PATCH /api/v1/clinical/encounters/',
  'POST /api/v1/clinical/lesions',
]);

function isReplayableMutation(method: string, path: string): boolean {
  const normalized = `${method.toUpperCase()} ${path}`;
  return [...OFFLINE_REPLAYABLE].some(prefix => normalized.startsWith(prefix));
}

function makeIdempotencyKey(): string {
  return `sync-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export const api = {
  async analyzeSkinImage(imageUri: string): Promise<PredictionResponse> {
    if (!imageUri) throw new Error('No image provided');

    const formData = new FormData();
    const imageUriParsed = Platform.OS === 'ios' ? imageUri.replace('file://', '') : imageUri;
    formData.append('file', {
      uri: imageUriParsed,
      type: 'image/jpeg',
      name: 'screening-image.jpg',
    } as any);

    try {
      const user = auth.currentUser;
      if (!user) throw new Error('Authentication required. Please sign in again.');
      const token = await user.getIdToken();
      const response = await request('/predict', {
        method: 'POST',
        body: formData,
        headers: { Accept: 'application/json', Authorization: `Bearer ${token}` },
      });

      const body = await response.text();
      if (!response.ok) {
        let message = body;
        try {
          const parsed = JSON.parse(body);
          message = parsed.detail || body;
        } catch {
          // Keep raw response text.
        }
        throw new ClinicalApiError(message, response.status, message, response.headers.get('X-Request-ID') ?? undefined);
      }

      const data = JSON.parse(body) as PredictionResponse;
      if (!data.class_name || !data.model_used || typeof data.confidence !== 'number') {
        throw new Error('AI service returned an invalid prediction payload');
      }
      return data;
    } catch (error) {
      if (error instanceof Error && error.message.includes('Network request failed')) {
        throw new Error('Cannot reach the AI service. Check connectivity and the backend health status.');
      }
      throw error instanceof Error ? error : new Error('Unexpected AI service error');
    }
  },

  async getHealth(): Promise<any> {
    const response = await request('/health');
    if (!response.ok) throw new Error(`Health check failed: ${response.status}`);
    return response.json();
  },

  async selfHeal(): Promise<any> {
    const user = auth.currentUser;
    if (!user) throw new Error('Authentication required. Please sign in again.');
    const token = await user.getIdToken();
    const response = await request('/self-heal', { method: 'POST', headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) throw new Error(`Self-heal failed: ${response.status}`);
    return response.json();
  },


  async clinicalRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
    const user = auth.currentUser;
    if (!user) throw new Error('Authentication required. Please sign in again.');
    const token = await user.getIdToken();
    const scope = user.uid;
    const method = (init.method || 'GET').toUpperCase();
    const fullPath = `/api/v1/clinical${path}`;
    const replayable = isReplayableMutation(method, fullPath);
    const idempotencyKey = replayable
      ? String((init.headers as Record<string, string> | undefined)?.['Idempotency-Key'] || makeIdempotencyKey())
      : undefined;

    try {
      const response = await request(fullPath, {
        ...init,
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
          ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}),
          ...(init.headers || {}),
        },
      });
      const body = await response.text();
      let parsed: any;
      try { parsed = body ? JSON.parse(body) : undefined; } catch { parsed = undefined; }
      if (!response.ok) {
        const detail = parsed?.detail ?? body ?? `Clinical API request failed: ${response.status}`;
        const message = typeof detail === 'string' ? detail : JSON.stringify(detail);
        throw new ClinicalApiError(message, response.status, message, response.headers.get('X-Request-ID') ?? undefined);
      }
      return parsed as T;
    } catch (error) {
      const status = error instanceof ClinicalApiError ? error.status : undefined;
      const isNetworkFailure = status === undefined;
      if (replayable && isNetworkFailure) {
        const body = typeof init.body === 'string' ? JSON.parse(init.body) : init.body;
        await enqueuePersistentSync(scope, {
          id: idempotencyKey as string,
          method: method as SyncOperation['method'],
          path: fullPath,
          body,
          createdAt: Date.now(),
          idempotencyKey: idempotencyKey as string,
        });
        throw new Error('Network unavailable. The clinical change was saved to the persistent offline queue and will retry when connectivity returns.');
      }
      throw error;
    }
  },

  async flushClinicalSyncQueue(): Promise<{ sent: number; conflicts: number; remaining: number }> {
    const user = auth.currentUser;
    if (!user) return { sent: 0, conflicts: 0, remaining: 0 };

    const scope = user.uid;
    const token = await user.getIdToken();
    return flushSyncQueue(scope, async (operation): Promise<SyncSendResult> => {
      try {
        const response = await request(operation.path, {
          method: operation.method,
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
            'Idempotency-Key': operation.idempotencyKey,
          },
          body: operation.body === undefined ? undefined : JSON.stringify(operation.body),
        });
        const textBody = await response.text();
        if (response.ok) return { status: 'sent' };
        if (response.status === 409) {
          return { status: 'conflict', message: textBody || 'Clinical concurrency conflict' };
        }
        if (response.status >= 500 || response.status === 408 || response.status === 429) {
          return { status: 'retry', message: textBody || 'Transient server failure' };
        }
        return { status: 'conflict', message: textBody || `Permanent clinical sync failure: ${response.status}` };
      } catch (error) {
        return { status: 'retry', message: error instanceof Error ? error.message : 'Network failure' };
      }
    });
  },

  async createEncounter(input: Record<string, unknown>) {
    return this.clinicalRequest<Record<string, unknown>>('/encounters', { method: 'POST', body: JSON.stringify(input) });
  },
  async getEncounter(encounterId: string) {
    return this.clinicalRequest<Record<string, unknown>>(`/encounters/${encodeURIComponent(encounterId)}`);
  },
  async updateEncounter(encounterId: string, expectedVersion: number, patch: Record<string, unknown>) {
    return this.clinicalRequest<Record<string, unknown>>(`/encounters/${encodeURIComponent(encounterId)}`, { method: 'PATCH', body: JSON.stringify({ expected_version: expectedVersion, ...patch }) });
  },
  async upsertLesion(input: Record<string, unknown>) {
    return this.clinicalRequest<Record<string, unknown>>('/lesions', { method: 'POST', body: JSON.stringify(input) });
  },
  async recordConsent(input: Record<string, unknown>) {
    return this.clinicalRequest<Record<string, unknown>>('/consents', { method: 'POST', body: JSON.stringify(input) });
  },
  async recordClinicalMedia(input: Record<string, unknown>) {
    return this.clinicalRequest<Record<string, unknown>>('/media', { method: 'POST', body: JSON.stringify(input) });
  },
  async patientMedia(patientId: string, encounterId?: string, lesionId?: string) {
    const params = new URLSearchParams();
    if (encounterId) params.set('encounter_id', encounterId);
    if (lesionId) params.set('lesion_id', lesionId);
    const query = params.toString() ? `?${params.toString()}` : '';
    return this.clinicalRequest<Record<string, unknown>[]>(`/patients/${encodeURIComponent(patientId)}/media${query}`);
  },
  async lesionTimeline(patientId: string, lesionCode: string) {
    return this.clinicalRequest<Record<string, unknown>[]>(`/patients/${encodeURIComponent(patientId)}/lesions/${encodeURIComponent(lesionCode)}/timeline`);
  },
  async attachAIReview(encounterId: string, input: Record<string, unknown>) {
    return this.clinicalRequest<Record<string, unknown>>(`/encounters/${encodeURIComponent(encounterId)}/ai-reviews`, { method: 'POST', body: JSON.stringify(input) });
  },
  async reviewAI(encounterId: string, reviewId: string, clinicianDecision: 'accepted' | 'overridden' | 'rejected', overrideLabel?: string) {
    return this.clinicalRequest<Record<string, unknown>>(`/encounters/${encodeURIComponent(encounterId)}/ai-reviews/${encodeURIComponent(reviewId)}`, { method: 'PATCH', body: JSON.stringify({ clinician_decision: clinicianDecision, clinician_override_label: overrideLabel }) });
  },
  async signEncounter(encounterId: string, attestation?: string) {
    return this.clinicalRequest<Record<string, unknown>>(`/encounters/${encodeURIComponent(encounterId)}/sign`, { method: 'POST', body: JSON.stringify({ attestation }) });
  },
  async createFollowup(encounterId: string, dueAt: string, instructions: string) {
    return this.clinicalRequest<Record<string, unknown>>(`/encounters/${encodeURIComponent(encounterId)}/followups`, { method: 'POST', body: JSON.stringify({ due_at: dueAt, instructions }) });
  },
  async patientSummary(patientId: string) {
    return this.clinicalRequest<Record<string, unknown>>(`/patients/${encodeURIComponent(patientId)}/summary`);
  },
  async createPrescription(input: Record<string, unknown>) {
    return this.clinicalRequest<Record<string, unknown>>('/prescriptions', { method: 'POST', body: JSON.stringify(input) });
  },
  async patientPrescriptions(patientId: string) {
    return this.clinicalRequest<Record<string, unknown>[]>(`/prescriptions/patient/${encodeURIComponent(patientId)}`);
  },
  async getPrescription(prescriptionId: string) {
    return this.clinicalRequest<Record<string, unknown>>(`/prescriptions/${encodeURIComponent(prescriptionId)}`);
  },
  async cancelPrescription(prescriptionId: string) {
    return this.clinicalRequest<Record<string, unknown>>(`/prescriptions/${encodeURIComponent(prescriptionId)}/cancel`, { method: 'POST' });
  },

  getRecommendations(condition: string): string[] {
    // These are clinician-facing reference prompts, not autonomous treatment orders.
    const recommendationsMap: { [key: string]: string[] } = {
      Melanoma: [
        'Perform a complete clinical and dermoscopic assessment.',
        'Consider histopathological confirmation according to the lesion and clinical context.',
        'Document lesion site, size, morphology and evolution.',
        'Use established melanoma staging pathways only after diagnostic confirmation.',
      ],
      'Melanoma Risk Signal': [
        'Do not treat this signal as a diagnosis.',
        'Perform focused clinical and dermoscopic assessment.',
        'Consider histopathological confirmation when clinically indicated.',
        'Document the lesion for serial comparison when appropriate.',
      ],
      'Actinic Keratosis': [
        'Correlate the AI suggestion with clinical examination and dermoscopy.',
        'Assess for features concerning for invasive squamous neoplasia.',
        'Select treatment according to lesion burden, site and current guideline-based practice.',
        'Document photoprotection counselling and follow-up when indicated.',
      ],
      'Basal Cell Carcinoma': [
        'Confirm the suspected diagnosis clinically and histopathologically when indicated.',
        'Assess lesion risk category and anatomical site before treatment selection.',
        'Select definitive therapy according to current dermatology/oncology guidance.',
        'Document margins, recurrence risk and follow-up plan where relevant.',
      ],
      'Benign Keratosis': [
        'Correlate with clinical examination and dermoscopy.',
        'No treatment is implied by the AI output alone.',
        'Consider intervention only when clinically or symptomatically indicated.',
        'Monitor atypical or changing lesions appropriately.',
      ],
      Dermatofibroma: [
        'Correlate with examination and dermoscopy.',
        'Investigate lesions with atypical clinical behaviour or diagnostic uncertainty.',
        'Use histopathology when clinically indicated.',
        'Document changes in size, symptoms or morphology.',
      ],
      'Melanocytic Nevus': [
        'Assess with clinical examination and dermoscopy.',
        'Compare with previous images when available.',
        'Evaluate asymmetry, border, colour and evolution in the clinical context.',
        'Consider biopsy/excision only when clinically indicated.',
      ],
      'Vascular Lesion': [
        'Correlate the suggestion with clinical examination and dermoscopy.',
        'Consider alternative vascular and non-vascular diagnoses.',
        'Use imaging or histopathology selectively when depth or diagnosis is uncertain.',
        'Document evolution and symptoms where clinically relevant.',
      ],
    };

    return recommendationsMap[condition] || [
      'The AI result requires clinician interpretation.',
      'Perform appropriate clinical and dermoscopic assessment.',
      'Use histopathology or additional investigations when clinically indicated.',
      'Document the lesion and follow longitudinal change where appropriate.',
    ];
  },
};


export async function clearCurrentUserClinicalSyncQueue(): Promise<void> {
  const user = auth.currentUser;
  if (user) await clearSyncQueue(user.uid);
}
