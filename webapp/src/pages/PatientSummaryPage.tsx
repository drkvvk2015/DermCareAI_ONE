import { ArrowLeft, CheckCircle2, ClipboardList, FileText, Plus, Scissors, Sparkles } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { Link, NavLink, useParams } from 'react-router-dom';
import { api, type ClinicalSummary } from '../api/client';
import { useSession } from '../auth/Session';
import { DataState, EmptyState, LoadingState } from '../components/DataState';
import { GuidelinePanel } from '../components/GuidelinePanel';
import { NewEncounterModal } from '../components/NewEncounterModal';
import { SignoffModal } from '../components/SignoffModal';
import { NewLesionModal } from '../components/NewLesionModal';
import { AIScreeningModal } from '../components/AIScreeningModal';
import { useResource } from '../hooks/useResource';

function text(value: unknown) { return typeof value === 'string' && value.trim() ? value : 'Not recorded'; }
function date(value: unknown) {
  if (typeof value !== 'string') return 'Date not recorded';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(parsed);
}

export function PatientSummaryPage() {
  const { patientId = '' } = useParams();
  const load = useCallback((currentUser: NonNullable<ReturnType<typeof useSession>['user']>) => api.clinicalSummary(patientId, currentUser), [patientId]);
  const { data, error, loading, reload } = useResource<ClinicalSummary>(load, patientId);

  const [showEncounterModal, setShowEncounterModal] = useState(false);
  const [showLesionModal, setShowLesionModal] = useState(false);
  const [showAIModal, setShowAIModal] = useState(false);
  const [signingEncounterId, setSigningEncounterId] = useState<string | null>(null);

  useEffect(() => { document.title = `Patient ${patientId} | DermCare Clinical`; }, [patientId]);

  if (loading) return <section className="content-page"><LoadingState /></section>;
  if (error) return <section className="content-page"><DataState error={error} onRetry={() => void reload()} /></section>;
  if (!data) return null;

  const openEncounters = data.encounters.filter((e) => e.status !== 'signed');

  return (
    <section className="content-page">
      <Link className="back-link" to="/patients"><ArrowLeft size={16} />Patient lookup</Link>
      <div className="patient-heading">
        <div>
          <p className="eyebrow">PATIENT RECORD</p>
          <h1>{data.patient_id}</h1>
          <p>Clinical summary & longitudinal tracking</p>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button
            className="primary-button-inline"
            type="button"
            onClick={() => setShowAIModal(true)}
            disabled={!data.encounters.length}
            title={data.encounters.length ? 'Run Clinical AI Screening' : 'Create an encounter first'}
          >
            <Sparkles size={16} style={{ marginRight: 6 }} /> AI Screening
          </button>
          <div className="record-badge"><span />Record available</div>
        </div>
      </div>

      <nav className="record-tabs" aria-label="Patient record views">
        <NavLink end to={`/patients/${encodeURIComponent(patientId)}`}><ClipboardList size={16} />Summary</NavLink>
        <NavLink to={`/patients/${encodeURIComponent(patientId)}/prescriptions`}><FileText size={16} />Prescriptions</NavLink>
        <NavLink to={`/patients/${encodeURIComponent(patientId)}/procedures`}><Scissors size={16} />Procedures</NavLink>
      </nav>

      <div className="summary-grid">
        <section className="summary-section">
          <div className="section-title">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <h2>Encounters</h2>
              <span>{data.encounters.length}</span>
            </div>
            <button
              className="action-button-pill"
              type="button"
              onClick={() => setShowEncounterModal(true)}
            >
              <Plus size={14} style={{ marginRight: 4 }} /> New Encounter
            </button>
          </div>

          {data.encounters.length ? (
            <ul className="record-list">
              {data.encounters.map((encounter, index) => {
                const encId = String(encounter.id ?? index);
                const isSigned = encounter.status === 'signed';
                const complaintsObj = encounter.complaints as Record<string, unknown> | undefined;
                const examObj = encounter.examination as Record<string, unknown> | undefined;
                const assessObj = encounter.assessment as Record<string, unknown> | undefined;
                return (
                  <li key={encId} className="encounter-list-item">
                    <div className="record-row">
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span className={isSigned ? 'status-pill-signed' : 'status-pill-open'}>
                          {text(encounter.status)}
                        </span>
                        <strong>Encounter {encId}</strong>
                      </div>
                      <time>{date(encounter.opened_at)}</time>
                    </div>

                    <p>
                      <strong>Chief Complaint:</strong> {text(complaintsObj?.chief_complaint)}
                      {Boolean(complaintsObj?.duration) && ` (${text(complaintsObj?.duration)})`}
                    </p>
                    {Boolean(examObj?.morphology) && (
                      <p><strong>Morphology:</strong> {text(examObj?.morphology)}</p>
                    )}
                    {Boolean(assessObj?.summary) && (
                      <p><strong>Assessment:</strong> {text(assessObj?.summary)}</p>
                    )}

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
                      <small>Version {String(encounter.version || 1)}</small>
                      {!isSigned && (
                        <button
                          className="signoff-button-inline"
                          type="button"
                          onClick={() => setSigningEncounterId(encId)}
                        >
                          <CheckCircle2 size={14} style={{ marginRight: 4 }} /> Sign off
                        </button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : (
            <EmptyState title="No encounters" message="No encounter records are available for this patient." />
          )}
        </section>

        <section className="summary-section">
          <div className="section-title">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <h2>Lesions</h2>
              <span>{data.lesions.length}</span>
            </div>
            <button
              className="action-button-pill"
              type="button"
              onClick={() => setShowLesionModal(true)}
              disabled={!openEncounters.length}
              title={openEncounters.length ? 'Record a lesion observation' : 'An open encounter is required to record lesions'}
            >
              <Plus size={14} style={{ marginRight: 4 }} /> Add Lesion
            </button>
          </div>

          {data.lesions.length ? (
            <ul className="record-list">
              {data.lesions.map((lesion, index) => {
                const morphObj = lesion.morphology as Record<string, unknown> | undefined;
                return (
                  <li key={String(lesion.id ?? index)}>
                    <div className="record-row">
                      <strong>
                        {text(lesion.body_site)} {lesion.laterality ? `(${text(lesion.laterality)})` : ''}
                      </strong>
                      <time>{date(lesion.updated_at)}</time>
                    </div>
                    <p>
                      <strong>Impression:</strong> {text(lesion.clinical_impression)}
                    </p>
                    {Boolean(morphObj?.primary) && (
                      <p><strong>Morphology:</strong> {text(morphObj?.primary)}</p>
                    )}
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                      <small>Lesion Code: <strong>{text(lesion.lesion_code)}</strong></small>
                      {lesion.size_mm !== undefined && lesion.size_mm !== null && (
                        <small>Size: {String(lesion.size_mm)} mm</small>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : (
            <EmptyState title="No lesions" message="No lesion records are available for this patient." />
          )}
        </section>

        <section className="summary-section">
          <div className="section-title">
            <h2>Follow-ups</h2>
            <span>{data.followups.length}</span>
          </div>
          {data.followups.length ? (
            <ul className="record-list">
              {data.followups.map((item, index) => (
                <li key={String(item.id ?? index)}>
                  <div className="record-row">
                    <strong>{text(item.status)}</strong>
                    <time>{date(item.due_at)}</time>
                  </div>
                  <p>{text(item.instructions)}</p>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No follow-ups" message="No follow-up records are available for this patient." />
          )}
        </section>

        <section className="summary-section">
          <div className="section-title">
            <h2>Signoffs</h2>
            <span>{data.signoffs.length}</span>
          </div>
          {data.signoffs.length ? (
            <ul className="record-list">
              {data.signoffs.map((item, index) => (
                <li key={String(item.id ?? index)}>
                  <div className="record-row">
                    <strong style={{ color: '#176b58' }}>✓ Clinically Signed</strong>
                    <time>{date(item.signed_at)}</time>
                  </div>
                  <p>{text(item.attestation)}</p>
                  <small>Doctor UID: {text(item.signed_by)}</small>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No signoffs" message="No signoff records are available for this patient." />
          )}
        </section>
      </div>

      <GuidelinePanel />

      <NewEncounterModal
        patientId={patientId}
        isOpen={showEncounterModal}
        onClose={() => setShowEncounterModal(false)}
        onSuccess={() => void reload()}
      />

      <SignoffModal
        encounterId={signingEncounterId || ''}
        isOpen={Boolean(signingEncounterId)}
        onClose={() => setSigningEncounterId(null)}
        onSuccess={() => void reload()}
      />

      <NewLesionModal
        patientId={patientId}
        encounters={openEncounters.length ? openEncounters : data.encounters}
        isOpen={showLesionModal}
        onClose={() => setShowLesionModal(false)}
        onSuccess={() => void reload()}
      />

      <AIScreeningModal
        patientId={patientId}
        encounters={data.encounters}
        lesions={data.lesions}
        isOpen={showAIModal}
        onClose={() => setShowAIModal(false)}
        onSuccess={() => void reload()}
      />
    </section>
  );
}
