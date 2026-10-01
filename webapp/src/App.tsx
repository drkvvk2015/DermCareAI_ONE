import { Navigate, Route, Routes } from 'react-router-dom';
import { SessionProvider } from './auth/Session';
import { DashboardShell } from './components/DashboardShell';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { PatientLookupPage } from './pages/PatientLookupPage';
import { PatientSummaryPage } from './pages/PatientSummaryPage';
import { PrescriptionsPage } from './pages/PrescriptionsPage';
import { ProceduresPage } from './pages/ProceduresPage';

export function App() {
  return (
    <SessionProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<DashboardShell />}>
            <Route path="/patients" element={<PatientLookupPage />} />
            <Route path="/patients/:patientId" element={<PatientSummaryPage />} />
            <Route path="/patients/:patientId/prescriptions" element={<PrescriptionsPage />} />
            <Route path="/patients/:patientId/procedures" element={<ProceduresPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/patients" replace />} />
      </Routes>
    </SessionProvider>
  );
}
