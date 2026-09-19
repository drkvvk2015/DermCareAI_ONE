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
