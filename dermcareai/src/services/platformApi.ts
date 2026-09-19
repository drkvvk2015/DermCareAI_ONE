import { API_URL } from '@env';

export type PlatformInfo = {
  api_version: string;
  app_version: string;
  service: string;
  environment: string;
  capabilities: string[];
  generated_at: string;
};

export type ReadinessComponent = {
  status: 'ok' | 'degraded' | 'not_configured';
  detail: string;
};

export type ReadinessResponse = {
  status: 'ready' | 'degraded';
  version: string;
  components: Record<string, ReadinessComponent>;
  generated_at: string;
};

export type AIGovernanceCard = {
  decision_type: 'clinical_decision_support';
  intended_use: string;
  diagnostic_status: 'not_a_diagnosis';
  human_review_required: boolean;
  abstention_enabled: boolean;
  confidence_threshold: number;
  model_provenance: string;
  model_name: string;
  research_model: boolean;
  safety_controls: string[];
  limitations: string[];
};

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { Accept: 'application/json' },
  });
  const body = await response.text();
  if (!response.ok) {
    throw new Error(body || `Platform request failed: ${response.status}`);
  }
  return (body ? JSON.parse(body) : {}) as T;
}

export const platformApi = {
  getInfo(): Promise<PlatformInfo> {
    return get<PlatformInfo>('/api/v1/platform');
  },

  getReadiness(): Promise<ReadinessResponse> {
    return get<ReadinessResponse>('/api/v1/health/ready');
  },

  getAIPolicy(): Promise<AIGovernanceCard> {
    return get<AIGovernanceCard>('/api/v1/ai/policy');
  },
};
