import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useSession } from '../auth/Session';

export function ProtectedRoute() {
  const { user, initializing } = useSession();
  const location = useLocation();

  if (initializing) return <div className="screen-state" role="status">Restoring secure session...</div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  return <Outlet />;
}
