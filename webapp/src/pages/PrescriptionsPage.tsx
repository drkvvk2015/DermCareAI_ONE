import { ArrowLeft, ClipboardPlus, FileText, Scissors } from 'lucide-react';
import { useCallback } from 'react';
import { Link, NavLink, useParams } from 'react-router-dom';
import { api, type Prescription } from '../api/client';
import { useSession } from '../auth/Session';
import { DataState, EmptyState, LoadingState } from '../components/DataState';
import { useResource } from '../hooks/useResource';

function label(value: unknown) { return typeof value === 'string' && value.trim() ? value : 'Not recorded'; }
function prettyDate(value: unknown) {
  if (typeof value !== 'string') return 'Date not recorded';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(parsed);
}

export function PrescriptionsPage() {
  const { patientId = '' } = useParams();
  const load = useCallback((currentUser: NonNullable<ReturnType<typeof useSession>['user']>) => api.prescriptions(patientId, currentUser), [patientId]);
  const { data, error, loading, reload } = useResource<Prescription[]>(load, patientId);

  if (loading) return <section className="content-page"><LoadingState /></section>;
  if (error) return <section className="content-page"><DataState error={error} onRetry={() => void reload()} /></section>;
  if (!data) return null;

  return (
    <section className="content-page">
      <Link className="back-link" to={`/patients/${encodeURIComponent(patientId)}`}><ArrowLeft size={16} />Patient summary</Link>
      <div className="patient-heading"><div><p className="eyebrow">PATIENT RECORD</p><h1>{patientId}</h1><p>Prescription history</p></div><div className="record-badge"><span />Read only</div></div>
      <nav className="record-tabs" aria-label="Patient record views">
        <NavLink to={`/patients/${encodeURIComponent(patientId)}`}><ClipboardPlus size={16} />Summary</NavLink>
        <NavLink end to={`/patients/${encodeURIComponent(patientId)}/prescriptions`}><FileText size={16} />Prescriptions</NavLink>
        <NavLink to={`/patients/${encodeURIComponent(patientId)}/procedures`}><Scissors size={16} />Procedures</NavLink>
      </nav>
      <section className="summary-section full-section"><div className="section-title"><h2>Prescriptions</h2><span>{data.length}</span></div>
        {data.length ? <ul className="record-list">{data.map((prescription, index) => <li key={String(prescription.id ?? index)}><div className="record-row"><strong>{label(prescription.status)}</strong><time>{prettyDate(prescription.created_at)}</time></div><p>{label(prescription.instructions)}</p>{prescription.items?.map((item, itemIndex) => <p key={itemIndex}>{[item.name, item.strength, item.dose, item.route, item.frequency, item.duration].filter((value): value is string => typeof value === 'string' && value.length > 0).join(' - ') || 'Medication details not recorded'}</p>)}<small>Prescription {label(prescription.id)} - {prescription.items?.length ?? 0} item(s)</small></li>)}</ul> : <EmptyState title="No prescriptions" message="No prescription records are available for this patient." />}
      </section>
    </section>
  );
}
