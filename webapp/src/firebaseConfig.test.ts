import { describe, expect, it } from 'vitest';
import { validateFirebaseConfig } from './firebaseConfig';

describe('Firebase web configuration validation', () => {
  it('rejects incomplete settings without including supplied values in the result', () => {
    const result = validateFirebaseConfig({
      apiKey: 'synthetic-public-key',
      authDomain: ' ',
      projectId: 'synthetic-project',
    });

    expect(result).toEqual({
      config: null,
      missing: ['authDomain', 'appId'],
    });
    expect(JSON.stringify(result)).not.toContain('synthetic-public-key');
  });

  it('returns trimmed settings when all required values are present', () => {
    expect(validateFirebaseConfig({
      apiKey: ' synthetic-key ',
      authDomain: ' synthetic.example.test ',
      projectId: ' synthetic-project ',
      appId: ' synthetic-app ',
    })).toEqual({
      config: {
        apiKey: 'synthetic-key',
        authDomain: 'synthetic.example.test',
        projectId: 'synthetic-project',
        appId: 'synthetic-app',
      },
      missing: [],
    });
  });
});
