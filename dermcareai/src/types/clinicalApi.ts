/** Stable v1 API response types shared by the React Native client. */
export const CLINICAL_API_VERSION = "v1" as const;

export interface HealthResponse {
  status: string;
  version: typeof CLINICAL_API_VERSION;
}

export interface ErrorResponse {
  detail: string;
}

export class ClinicalApiError extends Error {
  constructor(
    message: string,
    public readonly status: number = 0,
    public readonly detail: string = message,
    public readonly requestId?: string,
  ) {
    super(message);
    this.name = "ClinicalApiError";
  }
}

export function isClinicalApiError(error: unknown): error is ClinicalApiError {
  return error instanceof ClinicalApiError;
}
