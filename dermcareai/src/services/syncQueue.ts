import AsyncStorage from '@react-native-async-storage/async-storage';

export type SyncOperation = {
  id: string;
  method: "POST" | "PUT" | "PATCH" | "DELETE";
  path: string;
  body?: unknown;
  createdAt: number;
  attempts: number;
  idempotencyKey: string;
};

const STORAGE_KEY = '@dermcareai/clinical-sync-v1';
const MAX_RETRY_ATTEMPTS = 8;

export function enqueueSync(queue: SyncOperation[], operation: SyncOperation): SyncOperation[] {
  if (queue.some(item => item.id === operation.id)) return queue;
  return [...queue, operation].sort((a, b) => a.createdAt - b.createdAt);
}

export function nextSync(queue: SyncOperation[]): SyncOperation | undefined {
  return [...queue].sort((a, b) => a.createdAt - b.createdAt)[0];
}

export function markSyncRetry(queue: SyncOperation[], id: string): SyncOperation[] {
  return queue.map(item =>
    item.id === id ? { ...item, attempts: item.attempts + 1 } : item
  );
}

export async function loadSyncQueue(): Promise<SyncOperation[]> {
  const raw = await AsyncStorage.getItem(STORAGE_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

async function saveSyncQueue(queue: SyncOperation[]): Promise<void> {
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(queue));
}

export async function enqueuePersistentSync(operation: Omit<SyncOperation, "attempts">): Promise<SyncOperation[]> {
  const current = await loadSyncQueue();
  const queued = enqueueSync(current, { ...operation, attempts: 0 });
  await saveSyncQueue(queued);
  return queued;
}

export type SyncSendResult =
  | { status: "sent" }
  | { status: "conflict"; message: string }
  | { status: "retry"; message: string };

export async function flushSyncQueue(
  send: (operation: SyncOperation) => Promise<SyncSendResult>
): Promise<{ sent: number; conflicts: number; remaining: number }> {
  let queue = await loadSyncQueue();
  let sent = 0;
  let conflicts = 0;

  while (queue.length > 0) {
    const operation = nextSync(queue);
    if (!operation) break;

    if (operation.attempts >= MAX_RETRY_ATTEMPTS) {
      // Retain the operation for explicit clinician recovery rather than dropping data.
      break;
    }

    const result = await send(operation);
    if (result.status === "sent") {
      queue = queue.filter(item => item.id !== operation.id);
      await saveSyncQueue(queue);
      sent += 1;
      continue;
    }

    if (result.status === "conflict") {
      // A 409 is a real clinical concurrency conflict, not a transient network failure.
      // Keep it at the head of the queue so it remains visible/recoverable.
      conflicts += 1;
      break;
    }

    queue = markSyncRetry(queue, operation.id);
    await saveSyncQueue(queue);
    break;
  }

  return { sent, conflicts, remaining: queue.length };
}
