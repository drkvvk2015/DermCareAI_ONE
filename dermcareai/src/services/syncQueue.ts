export type SyncOperation = {
  id: string;
  method: "POST" | "PUT" | "PATCH" | "DELETE";
  path: string;
  body?: unknown;
  createdAt: number;
  attempts: number;
};

export function enqueueSync(queue: SyncOperation[], operation: SyncOperation): SyncOperation[] {
  if (queue.some(item => item.id === operation.id)) return queue;
  return [...queue, operation];
}

export function nextSync(queue: SyncOperation[]): SyncOperation | undefined {
  return [...queue].sort((a, b) => a.createdAt - b.createdAt)[0];
}

export function markSyncRetry(queue: SyncOperation[], id: string): SyncOperation[] {
  return queue.map(item => item.id === id ? { ...item, attempts: item.attempts + 1 } : item);
}
