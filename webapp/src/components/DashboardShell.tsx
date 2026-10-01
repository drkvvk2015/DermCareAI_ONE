import { Activity, ClipboardList, LogOut, Search, ShieldCheck, Stethoscope } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useSession } from '../auth/Session';

export function DashboardShell() {
  const { user, signOutUser } = useSession();
  const [patientId, setPatientId] = useState('');
  const navigate = useNavigate();

  function openPatient(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = patientId.trim();
    if (value) navigate(`/patients/${encodeURIComponent(value)}`);
  }

  return (
    <div className="app-frame">
      <aside className="sidebar">
        <Link className="brand" to="/patients" aria-label="DermCare Clinical home">
          <span className="brand-symbol"><Stethoscope size={20} /></span>
          <span><strong>DermCare</strong><small>CLINICAL WORKSPACE</small></span>
        </Link>
        <div className="nav-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          <NavLink to="/patients" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}><ClipboardList size={18} />Patient lookup</NavLink>
        </nav>
        <div className="sidebar-foot"><ShieldCheck size={16} /><span>Authenticated workspace</span></div>
      </aside>
      <main className="main-column">
        <header className="topbar">
          <form className="patient-search" onSubmit={openPatient} role="search">
            <Search size={17} aria-hidden="true" />
            <label className="sr-only" htmlFor="patient-id">Patient ID</label>
            <input id="patient-id" value={patientId} onChange={(event) => setPatientId(event.target.value)} placeholder="Open patient by ID" />
            <button type="submit" aria-label="Open patient" title="Open patient"><Activity size={17} /></button>
          </form>
          <div className="user-menu"><span className="user-avatar" aria-hidden="true">{user?.email?.charAt(0).toUpperCase() ?? 'U'}</span><span className="user-email">{user?.email ?? 'Signed in'}</span><button className="icon-action" type="button" onClick={() => void signOutUser()} aria-label="Sign out" title="Sign out"><LogOut size={17} /></button></div>
        </header>
        <Outlet />
      </main>
    </div>
  );
}
