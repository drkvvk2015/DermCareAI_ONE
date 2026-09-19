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
