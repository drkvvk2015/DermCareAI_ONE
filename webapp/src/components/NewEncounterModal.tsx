import { X } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { api, ApiError, type NewEncounter } from '../api/client';
import { useSession } from '../auth/Session';

type Props = {
  patientId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
};

export function NewEncounterModal({ patientId, isOpen, onClose, onSuccess }: Props) {
  const { user } = useSession();
  const [template, setTemplate] = useState('general');
  const [chiefComplaint, setChiefComplaint] = useState('');
  const [duration, setDuration] = useState('');
  const [morphology, setMorphology] = useState('');
  const [distribution, setDistribution] = useState('');
  const [assessment, setAssessment] = useState('');
  const [plan, setPlan] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!user) return;
    if (!chiefComplaint.trim() || !duration.trim() || !morphology.trim() || !distribution.trim() || !assessment.trim() || !plan.trim()) {
      setError('All core clinical documentation fields are required for dermatology encounter integrity.');
      return;
    }

    setBusy(true);
    setError('');

    const encounterPayload: NewEncounter = {
      patient_id: patientId,
      template: template === 'general' ? undefined : template,
      complaints: {
        chief_complaint: chiefComplaint.trim(),
        duration: duration.trim(),
      },
      examination: {
        morphology: morphology.trim(),
        distribution: distribution.trim(),
      },
      assessment: {
        summary: assessment.trim(),
      },
      plan: {
        summary: plan.trim(),
      },
    };

    try {
      await api.createEncounter(encounterPayload, user);
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to create encounter.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="modal-title-encounter">
      <div className="modal-card">
        <div className="modal-header">
          <div>
            <p className="eyebrow">CLINICAL DOCUMENTATION</p>
            <h2 id="modal-title-encounter">New Encounter</h2>
          </div>
          <button className="icon-action" type="button" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          <label htmlFor="encounter-template">Clinical Template</label>
          <select
            id="encounter-template"
            value={template}
            onChange={(e) => setTemplate(e.target.value)}
            className="form-input"
          >
            <option value="general">General Dermatology</option>
            <option value="acne">Acne Vulgaris</option>
            <option value="eczema">Atopic Dermatitis / Eczema</option>
            <option value="psoriasis">Psoriasis</option>
          </select>

          <label htmlFor="encounter-complaint">Chief Complaint *</label>
          <input
            id="encounter-complaint"
            className="form-input"
            value={chiefComplaint}
            onChange={(e) => setChiefComplaint(e.target.value)}
            placeholder="e.g. Itchy red lesions on forearms"
            required
          />

          <label htmlFor="encounter-duration">Duration *</label>
          <input
            id="encounter-duration"
            className="form-input"
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            placeholder="e.g. 3 weeks"
            required
          />

          <label htmlFor="encounter-morphology">Lesion Morphology *</label>
          <input
            id="encounter-morphology"
            className="form-input"
            value={morphology}
            onChange={(e) => setMorphology(e.target.value)}
            placeholder="e.g. Well-demarcated erythematous plaques with silvery scale"
            required
          />

          <label htmlFor="encounter-distribution">Anatomical Distribution *</label>
          <input
            id="encounter-distribution"
            className="form-input"
            value={distribution}
            onChange={(e) => setDistribution(e.target.value)}
            placeholder="e.g. Extensor surfaces, elbows, scalp"
            required
          />

          <label htmlFor="encounter-assessment">Assessment / Provisional Diagnosis *</label>
          <input
            id="encounter-assessment"
            className="form-input"
            value={assessment}
            onChange={(e) => setAssessment(e.target.value)}
            placeholder="e.g. Plaque Psoriasis"
            required
          />

          <label htmlFor="encounter-plan">Management Plan *</label>
          <input
            id="encounter-plan"
            className="form-input"
            value={plan}
            onChange={(e) => setPlan(e.target.value)}
            placeholder="e.g. Topical steroid cream, daily moisturizer, review in 4 weeks"
            required
          />

          {error && <p className="form-error" role="alert">{error}</p>}

          <div className="modal-actions">
            <button className="secondary-button" type="button" onClick={onClose} disabled={busy}>
              Cancel
            </button>
            <button className="primary-button-inline" type="submit" disabled={busy || !user}>
              {busy ? 'Saving...' : 'Create Encounter'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
