import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from './App';
import { ApiError } from './api/client';

const mocks = vi.hoisted(() => ({
  user: null as null | { email: string; getIdToken: () => Promise<string> },
  clinicalSummary: vi.fn(),
  prescriptions: vi.fn(),
  procedures: vi.fn(),
}));

vi.mock('./auth/Session', () => ({
  SessionProvider: ({ children }: { children: React.ReactNode }) => children,
  useSession: () => ({ user: mocks.user, initializing: false, signIn: vi.fn(), signOutUser: vi.fn() }),
}));
vi.mock('./api/client', () => ({
  ApiError: class ApiError extends Error { constructor(public status: number, message: string) { super(message); } },
  GUIDELINE_SOURCES: ['IADVL', 'AAD', 'BAD', 'NICE'],
  api: {
    clinicalSummary: mocks.clinicalSummary,
    prescriptions: mocks.prescriptions,
    procedures: mocks.procedures,
    guidelineSources: () => Promise.resolve({ IADVL: 0, AAD: 0, BAD: 0, NICE: 0 }),
    recommendGuideline: vi.fn(),
  },
}));

function renderAt(path: string) {
  window.history.replaceState({}, '', path);
  return render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>);
}

beforeEach(() => {
  mocks.user = { email: 'staff@example.test', getIdToken: async () => 'synthetic-token' };
  mocks.clinicalSummary.mockReset();
  mocks.prescriptions.mockReset();
  mocks.procedures.mockReset();
});

describe('dashboard routing and records', () => {
  it('redirects signed-out users to login', () => {
    mocks.user = null;
    renderAt('/patients');
    expect(screen.getByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
  });

  it('renders an empty summary without inferring clinical content', async () => {
    mocks.clinicalSummary.mockResolvedValue({ patient_id: 'synthetic-patient', encounters: [], lesions: [], followups: [], signoffs: [] });
    renderAt('/patients/synthetic-patient');
    expect(await screen.findByRole('heading', { name: 'synthetic-patient' })).toBeInTheDocument();
    expect(screen.getByText('No encounters')).toBeInTheDocument();
    expect(screen.getByText('No lesions')).toBeInTheDocument();
  });

  it('shows a distinct forbidden state', async () => {
    mocks.clinicalSummary.mockRejectedValue(new ApiError(403, 'You do not have permission to view this record.'));
    renderAt('/patients/synthetic-patient');
    expect(await screen.findByRole('heading', { name: 'Access restricted' })).toBeInTheDocument();
  });

  it('renders empty prescription and procedure views', async () => {
    mocks.prescriptions.mockResolvedValue([]);
    const prescriptions = renderAt('/patients/synthetic-patient/prescriptions');
    expect(await screen.findByText('No prescriptions')).toBeInTheDocument();

    prescriptions.unmount();
    mocks.procedures.mockResolvedValue([]);
    renderAt('/patients/synthetic-patient/procedures');
    expect(await screen.findByText('No procedures')).toBeInTheDocument();
  });
});
