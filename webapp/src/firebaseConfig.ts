export type FirebaseWebConfig = {
  apiKey: string;
  authDomain: string;
  projectId: string;
  appId: string;
};

export type FirebaseConfigValidation =
  | { config: FirebaseWebConfig; missing: [] }
  | { config: null; missing: Array<keyof FirebaseWebConfig> };

export function validateFirebaseConfig(
  values: Partial<Record<keyof FirebaseWebConfig, string | undefined>>,
): FirebaseConfigValidation {
  const fields = ['apiKey', 'authDomain', 'projectId', 'appId'] as const;
  const missing: Array<keyof FirebaseWebConfig> = fields.filter((field) => !values[field]?.trim());
  if (missing.length) return { config: null, missing };

  return {
    config: {
      apiKey: values.apiKey!.trim(),
      authDomain: values.authDomain!.trim(),
      projectId: values.projectId!.trim(),
      appId: values.appId!.trim(),
    },
    missing: [],
  };
}
