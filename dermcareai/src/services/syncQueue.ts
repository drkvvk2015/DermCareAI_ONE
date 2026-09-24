import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';
import CryptoJS from 'crypto-js';

export type SyncOperation = {
  id: string;
  method: "POST" | "PUT" | "PATCH" | "DELETE";
  path: string;
  body?: unknown;
  createdAt: number;
  attempts: number;
  idempotencyKey: string;
};

const MAX_RETRY_ATTEMPTS = 8;
const MAX_QUEUE_ITEMS = 100;
const QUEUE_TTL_MS = 7 * 24 * 60 * 60 * 1000;

function storageKey(scope: string): string {
  return '@dermcareai/clinical-sync-v2:' + scope;
}

async function encryptionKey(scope: string): Promise<string> {
  const keyName = 'dermcareai.sync.key.' + scope;
  const existing = await SecureStore.getItemAsync(keyName);
  if (existing) return existing;
  const generated = CryptoJS.lib.WordArray.random(32).toString(CryptoJS.enc.Base64);
  await SecureStore.setItemAsync(keyName, generated, {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
  return generated;
}

function encrypt(value: string, key: string): string {
  return CryptoJS.AES.encrypt(value, key).toString();
}

function decrypt(value: string, key: string): string {
  return CryptoJS.AES.decrypt(value, key).toString(CryptoJS.enc.Utf8);
}

export function enqueueSync(queue: SyncOperation[], operation: SyncOperation): SyncOperation[] {
  if (queue.some(item => item.id === operation.id)) return queue;
  return [...queue, operation].sort((a, b) => a.createdAt - b.createdAt).slice(-MAX_QUEUE_ITEMS);
}

export function nextSync(queue: SyncOperation[]): SyncOperation | undefined {
  return [...queue].sort((a, b) => a.createdAt - b.createdAt)[0];
}

export function markSyncRetry(queue: SyncOperation[], id: string): SyncOperation[] {
  return queue.map(item => item.id === id ? { ...item, attempts: item.attempts + 1 } : item);
}

function pruneExpired(queue: SyncOperation[]): SyncOperation[] {
  const cutoff = Date.now() - QUEUE_TTL_MS;
  return queue.filter(item => item.createdAt >= cutoff);
}

export async function loadSyncQueue(scope: string): Promise<SyncOperation[]> {
  const raw = await AsyncStorage.getItem(storageKey(scope));
  if (!raw) return [];
  try {
    const key = await encryptionKey(scope);
    const parsed = JSON.parse(decrypt(raw, key));
    return Array.isArray(parsed) ? pruneExpired(parsed) : [];
  } catch {
    return [];
  }
}

async function saveSyncQueue(scope: string, queue: SyncOperation[]): Promise<void> {
  const key = await encryptionKey(scope);
  const payload = JSON.stringify(pruneExpired(queue).slice(-MAX_QUEUE_ITEMS));
  await AsyncStorage.setItem(storageKey(scope), encrypt(payload, key));
}

export async function clearSyncQueue(scope: string): Promise<void> {
  await AsyncStorage.removeItem(storageKey(scope));
}

export async function enqueuePersistentSync(scope: string, operation: Omit<SyncOperation, 'attempts'>): Promise<SyncOperation[]> {
  const current = await loadSyncQueue(scope);
  const queued = enqueueSync(current, { ...operation, attempts: 0 });
  await saveSyncQueue(scope, queued);
  return queued;
}

export type SyncSendResult =
  | { status: 'sent' }
  | { status: 'conflict'; message: string }
  | { status: 'retry'; message: string };

export async function flushSyncQueue(scope: string, send: (operation: SyncOperation) => Promise<SyncSendResult>): Promise<{ sent: number; conflicts: number; remaining: number }> {
  let queue = await loadSyncQueue(scope);
  let sent = 0;
  let conflicts = 0;
  while (queue.length > 0) {
    const operation = nextSync(queue);
    if (!operation || operation.attempts >= MAX_RETRY_ATTEMPTS) break;
    const result = await send(operation);
    if (result.status === 'sent') {
      queue = queue.filter(item => item.id !== operation.id);
      await saveSyncQueue(scope, queue);
      sent += 1;
      continue;
    }
    if (result.status === 'conflict') {
      conflicts += 1;
      await saveSyncQueue(scope, queue);
      break;
    }
    queue = markSyncRetry(queue, operation.id);
    await saveSyncQueue(scope, queue);
    break;
  }
  return { sent, conflicts, remaining: queue.length };
}
