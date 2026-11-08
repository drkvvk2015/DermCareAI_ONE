import { ArrowLeft, ClipboardPlus, FileText, Plus, Scissors } from 'lucide-react';
import { useCallback, useState } from 'react';
import { Link, NavLink, useParams } from 'react-router-dom';
import { api, type ClinicalSummary, type Prescription } from '../api/client';
import { useSession } from '../auth/Session';
import { DataState, EmptyState, LoadingState } from '../components/DataState';
import { NewPrescriptionModal } from '../components/NewPrescriptionModal';
import { useResource } from '../hooks/useResource';

function label(value: unknown) { return typeof value === 'string' && value.trim() ? value : 'Not recorded'; }
function prettyDate(value: unknown) {
  if (typeof value !== 'string') return 'Date not recorded';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(parsed);
}

export function PrescriptionsPage() {
  const { patientId = '' } = useParams();
  const { user } = useSession();
  const loadRx = useCallback((currentUser: NonNullable<ReturnType<typeof useSession>['user']>) => api.prescriptions(patientId, currentUser), [patientId]);
  const loadSummary = useCallback((currentUser: NonNullable<ReturnType<typeof useSession>['user']>) => api.clinicalSummary(patientId, currentUser), [patientId]);

  const { data, error, loading, reload } = useResource<Prescription[]>(loadRx, patientId);
  const { data: summaryData } = useResource<ClinicalSummary>(loadSummary, patientId);

  const [showRxModal, setShowRxModal] = useState(false);

  if (loading) return <section className="content-page"><LoadingState /></section>;
  if (error) return <section className="content-page"><DataState error={error} onRetry={() => void reload()} /></section>;
  if (!data) return null;

  const encounters = summaryData?.encounters ?? [];

  return (
    <section className="content-page">
      <Link className="back-link" to={`/patients/${encodeURIComponent(patientId)}`}><ArrowLeft size={16} />Patient summary</Link>
      <div className="patient-heading">
        <div>
          <p className="eyebrow">PATIENT RECORD</p>
          <h1>{patientId}</h1>
          <p>Prescription history & pharmacy orders</p>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button
            className="primary-button-inline"
            type="button"
            onClick={() => setShowRxModal(true)}
            disabled={!encounters.length || !user}
            title={encounters.length ? 'Author a new prescription' : 'An encounter is required to author a prescription'}
          >
            <Plus size={16} style={{ marginRight: 6 }} /> Author Prescription
          </button>
          <div className="record-badge"><span />Authoritative</div>
        </div>
      </div>

      <nav className="record-tabs" aria-label="Patient record views">
        <NavLink to={`/patients/${encodeURIComponent(patientId)}`}><ClipboardPlus size={16} />Summary</NavLink>
        <NavLink end to={`/patients/${encodeURIComponent(patientId)}/prescriptions`}><FileText size={16} />Prescriptions</NavLink>
        <NavLink to={`/patients/${encodeURIComponent(patientId)}/procedures`}><Scissors size={16} />Procedures</NavLink>
      </nav>

      <section className="summary-section full-section">
        <div className="section-title">
          <h2>Prescriptions</h2>
          <span>{data.length}</span>
        </div>
        {data.length ? (
          <ul className="record-list">
            {data.map((prescription, index) => (
              <li key={String(prescription.id ?? index)}>
                <div className="record-row">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span className="status-pill-ok">{label(prescription.status)}</span>
                    <strong>Prescription {label(prescription.id)}</strong>
                  </div>
                  <time>{prettyDate(prescription.created_at)}</time>
                </div>
                <p><strong>Instructions:</strong> {label(prescription.instructions)}</p>
                {prescription.items && prescription.items.length > 0 && (
                  <div style={{ margin: '8px 0', padding: '8px 12px', background: '#f8faf9', borderRadius: 4 }}>
                    <small style={{ fontWeight: 700, color: '#33443e' }}>Items ({prescription.items.length}):</small>
                    <ul style={{ margin: '4px 0 0', paddingLeft: 16 }}>
                      {prescription.items.map((item, itemIndex) => (
                        <li key={itemIndex} style={{ fontSize: 12, color: '#44514b', padding: '2px 0' }}>
                          <strong>{label(item.name)}</strong> {item.strength ? `(${label(item.strength)})` : ''} — {label(item.dose)}, {label(item.route)}, {label(item.frequency)} for {label(item.duration)} (Qty: {String(item.quantity ?? 1)})
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <small>Linked Encounter: {label(prescription.encounter_id)}</small>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState title="No prescriptions" message="No prescription records are available for this patient." />
        )}
      </section>

      <NewPrescriptionModal
        patientId={patientId}
        encounters={encounters}
        isOpen={showRxModal}
        onClose={() => setShowRxModal(false)}
        onSuccess={() => void reload()}
      />
    </section>
  );
}
