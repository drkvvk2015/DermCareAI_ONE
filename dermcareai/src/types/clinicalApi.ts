/** Stable v1 API response types shared by the React Native client. */
export const CLINICAL_API_VERSION = "v1" as const;

export interface HealthResponse {
  status: string;
  version: typeof CLINICAL_API_VERSION;
}

export interface ErrorResponse {
  detail: string;
}

export interface ClinicalApiError extends Error {
  status: number;
  detail: string;
  requestId?: string;
}

export function isClinicalApiError(error: unknown): error is ClinicalApiError {
  return (
    error instanceof Error &&
    typeof (error as Partial<ClinicalApiError>).status === "number" &&
    typeof (error as Partial<ClinicalApiError>).detail === "string"
  );
}
