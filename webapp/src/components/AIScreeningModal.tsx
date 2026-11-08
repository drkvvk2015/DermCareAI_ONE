import { AlertTriangle, Check, CheckCircle2, ShieldAlert, Sparkles, Upload, X } from 'lucide-react';
import { useState, type ChangeEvent, type FormEvent } from 'react';
import { api, ApiError, type AIPrediction, type AIReviewRecord } from '../api/client';
import { useSession } from '../auth/Session';

type Props = {
  patientId: string;
  encounters: Array<Record<string, unknown>>;
  lesions: Array<Record<string, unknown>>;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
};

export function AIScreeningModal({ encounters, lesions, isOpen, onClose, onSuccess }: Props) {
  const { user } = useSession();
  const [encounterId, setEncounterId] = useState(String(encounters[0]?.id ?? ''));
  const [lesionId, setLesionId] = useState(String(lesions[0]?.id ?? ''));
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [prediction, setPrediction] = useState<AIPrediction | null>(null);
  const [busy, setBusy] = useState(false);
  const [reviewBusy, setReviewBusy] = useState(false);
  const [error, setError] = useState('');
  const [overrideLabel, setOverrideLabel] = useState('');
  const [showOverrideInput, setShowOverrideInput] = useState(false);
  const [reviewResult, setReviewResult] = useState<AIReviewRecord | null>(null);

  if (!isOpen) return null;

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setPrediction(null);
      setReviewResult(null);
      setError('');
      const reader = new FileReader();
      reader.onload = () => setImagePreview(reader.result as string);
      reader.readAsDataURL(file);
    }
  }

  async function handleAnalyze(event: FormEvent) {
    event.preventDefault();
    if (!user || !selectedFile) return;

    setBusy(true);
    setError('');

    try {
      const result = await api.predictImage(selectedFile, user);
      setPrediction(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'AI analysis failed. Please verify the image file.');
    } finally {
      setBusy(false);
    }
  }

  async function handleDecision(decision: 'accepted' | 'overridden' | 'rejected') {
    if (!user || !prediction || !encounterId) return;

    if (decision === 'overridden' && !overrideLabel.trim()) {
      setShowOverrideInput(true);
      setError('Please specify the clinician override diagnosis before confirming.');
      return;
    }

    setReviewBusy(true);
    setError('');

    try {
      // 1. Attach AI review to encounter
      const created = await api.createAIReview(
        encounterId,
        {
          request_id: prediction.request_id,
          model_name: prediction.model_used,
          predicted_label: prediction.class_name,
          confidence: prediction.confidence,
          accepted: decision === 'accepted',
          lesion_id: lesionId || undefined,
        },
        user
      );

      // 2. Record clinician final decision
      const decided = await api.decideAIReview(
        encounterId,
        created.id,
        decision,
        decision === 'overridden' ? overrideLabel.trim() : undefined,
        user
      );

      setReviewResult(decided);
      onSuccess();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to record clinician review decision.');
    } finally {
      setReviewBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="modal-title-screening">
      <div className="modal-card modal-card-large">
        <div className="modal-header">
          <div>
            <p className="eyebrow">CLINICAL DECISION SUPPORT</p>
            <h2 id="modal-title-screening">AI Lesion Review & Screening</h2>
          </div>
          <button className="icon-action" type="button" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          <div className="ai-safety-alert">
            <ShieldAlert size={20} className="ai-safety-icon" />
            <div>
              <strong>Assistive Decision Support Only</strong>
              <p>
                AI analysis is purely suggestive and does NOT constitute a diagnosis. The treating clinician
                must independently evaluate clinical features and retains sole diagnostic authority.
              </p>
            </div>
          </div>

          {!prediction ? (
            <form onSubmit={handleAnalyze} className="modal-form">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label htmlFor="ai-encounter">Encounter *</label>
                  <select
                    id="ai-encounter"
                    className="form-input"
                    value={encounterId}
                    onChange={(e) => setEncounterId(e.target.value)}
                    required
                  >
                    {encounters.map((enc) => (
                      <option key={String(enc.id)} value={String(enc.id)}>
                        {String(enc.id)} ({String(enc.status || 'open')})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="ai-lesion">Linked Lesion (Optional)</label>
                  <select
                    id="ai-lesion"
                    className="form-input"
                    value={lesionId}
                    onChange={(e) => setLesionId(e.target.value)}
                  >
                    <option value="">-- No specific lesion --</option>
                    {lesions.map((les) => (
                      <option key={String(les.id)} value={String(les.id)}>
                        {String(les.lesion_code || les.id)} - {String(les.body_site || '')}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <label htmlFor="ai-image-upload">Dermoscopy / Clinical Image *</label>
              <div className="image-upload-zone">
                <input
                  id="ai-image-upload"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleFileChange}
                  style={{ display: 'none' }}
                  required
                />
                <label htmlFor="ai-image-upload" className="upload-prompt">
                  <Upload size={28} />
                  <span>Click to select lesion photograph (JPEG, PNG, WEBP)</span>
                  <small>Images are decoded, sanitized, and evaluated against safety quality limits</small>
                </label>
              </div>

              {imagePreview && (
                <div className="image-preview-box">
                  <p className="preview-label">Selected Image Preview</p>
                  <img src={imagePreview} alt="Selected lesion" className="lesion-image" />
                </div>
              )}

              {error && <p className="form-error" role="alert">{error}</p>}

              <div className="modal-actions">
                <button className="secondary-button" type="button" onClick={onClose} disabled={busy}>
                  Cancel
                </button>
                <button
                  className="primary-button-inline"
                  type="submit"
                  disabled={busy || !selectedFile || !encounterId}
                >
                  <Sparkles size={16} style={{ marginRight: 6 }} />
                  {busy ? 'Analyzing Image...' : 'Run Clinical AI Analysis'}
                </button>
              </div>
            </form>
          ) : (
            <div className="prediction-results">
              <div className="results-grid">
                <div className="result-card">
                  <p className="card-caption">PREDICTED SIGNAL</p>
                  <h3 className={prediction.accepted ? 'signal-title' : 'signal-title signal-abstain'}>
                    {prediction.class_name}
                  </h3>
                  <div className="metric-row">
                    <span>Confidence:</span>
                    <strong>{(prediction.confidence * 100).toFixed(1)}%</strong>
                  </div>
                  <div className="metric-row">
                    <span>Model:</span>
                    <code>{prediction.model_used}</code>
                  </div>
                  <div className="metric-row">
                    <span>Safety Status:</span>
                    <span className={prediction.accepted ? 'status-pill-ok' : 'status-pill-warning'}>
                      {prediction.accepted ? 'Quality Gate Passed' : prediction.safety_reason || 'Abstained'}
                    </span>
                  </div>
                </div>

                {prediction.visualization ? (
                  <div className="result-card">
                    <p className="card-caption">GRAD-CAM EXPLAINABILITY HEATMAP</p>
                    <img
                      src={`data:image/jpeg;base64,${prediction.visualization}`}
                      alt="Grad-CAM visualization"
                      className="gradcam-image"
                    />
                    <small className="card-note">
                      Heatmap indicates image regions influencing the decision-support signal.
                    </small>
                  </div>
                ) : imagePreview ? (
                  <div className="result-card">
                    <p className="card-caption">INPUT IMAGE</p>
                    <img src={imagePreview} alt="Uploaded lesion" className="gradcam-image" />
                  </div>
                ) : null}
              </div>

              {reviewResult ? (
                <div className="review-confirmed-box">
                  <CheckCircle2 size={24} className="confirmed-icon" />
                  <div>
                    <h4>Clinician Review Recorded</h4>
                    <p>
                      Decision: <strong>{reviewResult.clinician_decision?.toUpperCase()}</strong>
                      {reviewResult.clinician_override_label && ` — Override: "${reviewResult.clinician_override_label}"`}
                    </p>
                    <small>Encounter sign-off requirement for this AI assessment is fulfilled.</small>
                  </div>
                  <button className="primary-button-inline" type="button" onClick={onClose} style={{ marginLeft: 'auto' }}>
                    Done
                  </button>
                </div>
              ) : (
                <div className="clinician-review-panel">
                  <div className="review-prompt">
                    <AlertTriangle size={18} />
                    <strong>Treating Physician Review & Decision:</strong>
                  </div>
                  <p className="review-instructions">
                    You must explicitly record an attestation decision to incorporate or reject this AI suggestion before
                    encounter sign-off:
                  </p>

                  {showOverrideInput && (
                    <div className="override-input-wrap">
                      <label htmlFor="clinician-override">Enter Your Diagnostic Override Label *</label>
                      <input
                        id="clinician-override"
                        className="form-input"
                        value={overrideLabel}
                        onChange={(e) => setOverrideLabel(e.target.value)}
                        placeholder="e.g. Benign Seborrheic Keratosis (Clinical Confirmation)"
                      />
                    </div>
                  )}

                  {error && <p className="form-error" role="alert">{error}</p>}

                  <div className="decision-buttons">
                    <button
                      className="decision-btn btn-accept"
                      type="button"
                      onClick={() => handleDecision('accepted')}
                      disabled={reviewBusy}
                    >
                      <Check size={16} /> Accept Suggestion
                    </button>
                    <button
                      className="decision-btn btn-override"
                      type="button"
                      onClick={() => {
                        if (!showOverrideInput) setShowOverrideInput(true);
                        else handleDecision('overridden');
                      }}
                      disabled={reviewBusy}
                    >
                      Override Diagnosis
                    </button>
                    <button
                      className="decision-btn btn-reject"
                      type="button"
                      onClick={() => handleDecision('rejected')}
                      disabled={reviewBusy}
                    >
                      <X size={16} /> Reject Suggestion
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
