import { auth } from '../config/firebase';
import { FIREBASE_CLINIC_ID, FIREBASE_ORGANIZATION_ID } from '@env';

export type ClinicScope = {
  organizationId: string;
  clinicId: string;
};

export async function getClinicScope(): Promise<ClinicScope> {
  const user = auth.currentUser;
  if (!user) throw new Error('User not authenticated');

  const token = await user.getIdTokenResult();
  const claims = token.claims as Record<string, unknown>;
  const organizationId = String(
    claims.organization_id ?? claims.organizationId ?? FIREBASE_ORGANIZATION_ID ?? '',
  ).trim();
  const clinicId = String(
    claims.clinic_id ?? claims.clinicId ?? FIREBASE_CLINIC_ID ?? '',
  ).trim();

  if (!organizationId || !clinicId) {
    throw new Error(
      'Clinic access is not configured for this account. Ask the administrator to assign organization and clinic access.',
    );
  }

  return { organizationId, clinicId };
}
