import { AlertCircle, LockKeyhole, RefreshCw } from 'lucide-react';
import { ApiError } from '../api/client';

export function DataState({ error, onRetry }: { error?: unknown; onRetry?: () => void }) {
  const status = error instanceof ApiError ? error.status : undefined;
  const forbidden = status === 403;
  const title = forbidden ? 'Access restricted' : status === 401 ? 'Sign-in required' : 'Unable to load this record';
  const message = error instanceof Error ? error.message : 'A network error prevented this view from loading.';
  const Icon = forbidden ? LockKeyhole : AlertCircle;

  return (
    <section className="state-panel" role="alert">
      <span className="state-icon"><Icon size={19} aria-hidden="true" /></span>
      <div><h2>{title}</h2><p>{message}</p></div>
      {onRetry && status !== 401 && <button className="icon-action" type="button" onClick={onRetry} aria-label="Retry loading" title="Retry"><RefreshCw size={17} /></button>}
    </section>
  );
}

export function LoadingState() {
  return <div className="loading-state" role="status"><span className="spinner" />Loading record...</div>;
}

export function EmptyState({ title, message }: { title: string; message: string }) {
  return <div className="empty-state"><span className="empty-mark" aria-hidden="true">-</span><h2>{title}</h2><p>{message}</p></div>;
}
