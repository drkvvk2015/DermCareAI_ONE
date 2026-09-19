import { Platform } from 'react-native';
import { API_URL } from '@env';

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
      const response = await request('/predict', {
        method: 'POST',
        body: formData,
        headers: { Accept: 'application/json' },
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
        throw new Error(`AI service error (${response.status}): ${message}`);
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
    const response = await request('/self-heal', { method: 'POST' });
    if (!response.ok) throw new Error(`Self-heal failed: ${response.status}`);
    return response.json();
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
