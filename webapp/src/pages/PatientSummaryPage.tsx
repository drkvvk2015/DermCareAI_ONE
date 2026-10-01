import { ArrowLeft, ClipboardList, FileText, Scissors } from 'lucide-react';
import { useCallback, useEffect } from 'react';
import { Link, NavLink, useParams } from 'react-router-dom';
import { api, type ClinicalSummary } from '../api/client';
import { useSession } from '../auth/Session';
import { DataState, EmptyState, LoadingState } from '../components/DataState';
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

  useEffect(() => { document.title = `Patient ${patientId} | DermCare Clinical`; }, [patientId]);

  if (loading) return <section className="content-page"><LoadingState /></section>;
  if (error) return <section className="content-page"><DataState error={error} onRetry={() => void reload()} /></section>;
  if (!data) return null;

  return (
    <section className="content-page">
      <Link className="back-link" to="/patients"><ArrowLeft size={16} />Patient lookup</Link>
      <div className="patient-heading"><div><p className="eyebrow">PATIENT RECORD</p><h1>{data.patient_id}</h1><p>Clinical summary</p></div><div className="record-badge"><span />Record available</div></div>
      <nav className="record-tabs" aria-label="Patient record views">
        <NavLink end to={`/patients/${encodeURIComponent(patientId)}`}><ClipboardList size={16} />Summary</NavLink>
        <NavLink to={`/patients/${encodeURIComponent(patientId)}/prescriptions`}><FileText size={16} />Prescriptions</NavLink>
        <NavLink to={`/patients/${encodeURIComponent(patientId)}/procedures`}><Scissors size={16} />Procedures</NavLink>
      </nav>
      <div className="summary-grid">
        <section className="summary-section"><div className="section-title"><h2>Encounters</h2><span>{data.encounters.length}</span></div>
          {data.encounters.length ? <ul className="record-list">{data.encounters.map((encounter, index) => <li key={String(encounter.id ?? index)}><div className="record-row"><strong>{text(encounter.status)}</strong><time>{date(encounter.opened_at)}</time></div><p>{text((encounter.complaints as Record<string, unknown> | undefined)?.chief_complaint)}</p><small>Encounter {text(encounter.id)}</small></li>)}</ul> : <EmptyState title="No encounters" message="No encounter records are available for this patient." />}
        </section>
        <section className="summary-section"><div className="section-title"><h2>Lesions</h2><span>{data.lesions.length}</span></div>
          {data.lesions.length ? <ul className="record-list">{data.lesions.map((lesion, index) => <li key={String(lesion.id ?? index)}><div className="record-row"><strong>{text(lesion.body_site)}</strong><time>{date(lesion.updated_at)}</time></div><p>{text(lesion.clinical_impression)}</p><small>Lesion {text(lesion.lesion_code)}</small></li>)}</ul> : <EmptyState title="No lesions" message="No lesion records are available for this patient." />}
        </section>
        <section className="summary-section"><div className="section-title"><h2>Follow-ups</h2><span>{data.followups.length}</span></div>
          {data.followups.length ? <ul className="record-list">{data.followups.map((item, index) => <li key={String(item.id ?? index)}><div className="record-row"><strong>{text(item.status)}</strong><time>{date(item.due_at)}</time></div><p>{text(item.instructions)}</p></li>)}</ul> : <EmptyState title="No follow-ups" message="No follow-up records are available for this patient." />}
        </section>
        <section className="summary-section"><div className="section-title"><h2>Signoffs</h2><span>{data.signoffs.length}</span></div>
          {data.signoffs.length ? <ul className="record-list">{data.signoffs.map((item, index) => <li key={String(item.id ?? index)}><div className="record-row"><strong>Reviewed</strong><time>{date(item.signed_at)}</time></div><p>{text(item.attestation)}</p></li>)}</ul> : <EmptyState title="No signoffs" message="No signoff records are available for this patient." />}
        </section>
      </div>
    </section>
  );
}
