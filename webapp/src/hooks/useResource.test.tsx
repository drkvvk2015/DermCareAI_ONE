import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { useResource } from './useResource';

const mocks = vi.hoisted(() => ({
  user: { uid: 'user-A', email: 'staff@example.test', getIdToken: async () => 'synthetic-token' },
  signedOut: false,
}));

vi.mock('../auth/Session', () => ({
  useSession: () => ({ user: mocks.signedOut ? null : mocks.user }),
}));

type RecordData = { label: string };
type Loader = Parameters<typeof useResource<RecordData>>[0];

function ResourceView({ resourceKey, loader }: { resourceKey: string; loader: Loader }) {
  const { data } = useResource(loader, resourceKey);
  return <output>{data?.label ?? 'no resource data'}</output>;
}

describe('useResource', () => {
  it('does not expose data from the previous resource key', async () => {
    const patientALoader = vi.fn().mockResolvedValue({ label: 'synthetic-patient-A' }) as Loader;
    const patientBLoader = vi.fn(() => new Promise<RecordData>(() => undefined)) as Loader;
    const view = render(<ResourceView resourceKey="patient-A" loader={patientALoader} />);

    expect(await screen.findByText('synthetic-patient-A')).toBeInTheDocument();

    view.rerender(<ResourceView resourceKey="patient-B" loader={patientBLoader} />);

    expect(screen.getByText('no resource data')).toBeInTheDocument();
    expect(screen.queryByText('synthetic-patient-A')).not.toBeInTheDocument();
  });

  it('does not expose data from the previous user for the same resource key', async () => {
    mocks.signedOut = false;
    const userALoader = vi.fn().mockResolvedValue({ label: 'synthetic-user-A-data' }) as Loader;
    const userBLoader = vi.fn(() => new Promise<RecordData>(() => undefined)) as Loader;
    const view = render(<ResourceView resourceKey="patient-A" loader={userALoader} />);

    expect(await screen.findByText('synthetic-user-A-data')).toBeInTheDocument();

    mocks.user = { ...mocks.user, uid: 'user-B' };
    view.rerender(<ResourceView resourceKey="patient-A" loader={userBLoader} />);

    expect(screen.getByText('no resource data')).toBeInTheDocument();
    expect(screen.queryByText('synthetic-user-A-data')).not.toBeInTheDocument();

    mocks.signedOut = true;
    view.rerender(<ResourceView resourceKey="patient-A" loader={userBLoader} />);

    expect(screen.getByText('no resource data')).toBeInTheDocument();
  });
});
