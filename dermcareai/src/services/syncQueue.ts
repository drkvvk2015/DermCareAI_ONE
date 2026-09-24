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
  ownerUid: string;
};

const STORAGE_PREFIX = '@dermcareai/clinical-sync-v2:';
const KEY_PREFIX = 'dermcareai-sync-key-v2:';
const MAX_RETRY_ATTEMPTS = 8;
const MAX_QUEUE_ITEMS = 100;

async function getStorageKey(ownerUid: string): Promise<string> {
  const secureKey = `${KEY_PREFIX}${ownerUid}`;
  let key = await SecureStore.getItemAsync(secureKey);
  if (!key) {
    key = CryptoJS.lib.WordArray.random(32).toString();
    await SecureStore.setItemAsync(secureKey, key, {
      keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
    });
  }
  return key;
}

function storageId(ownerUid: string): string {
  return `${STORAGE_PREFIX}${ownerUid}`;
}

function encrypt(value: string, key: string): string {
  return CryptoJS.AES.encrypt(value, key).toString();
}

function decrypt(value: string, key: string): string {
  return CryptoJS.AES.decrypt(value, key).toString(CryptoJS.enc.Utf8);
}

export function enqueueSync(queue: SyncOperation[], operation: SyncOperation): SyncOperation[] {
  if (queue.some(item => item.id === operation.id)) return queue;
  return [...queue, operation].sort((a, b) => a.createdAt - b.createdAt).slice(0, MAX_QUEUE_ITEMS);
}

export function nextSync(queue: SyncOperation[]): SyncOperation | undefined {
  return [...queue].sort((a, b) => a.createdAt - b.createdAt)[0];
}

export function markSyncRetry(queue: SyncOperation[], id: string): SyncOperation[] {
  return queue.map(item => item.id === id ? { ...item, attempts: item.attempts + 1 } : item);
}

export async function loadSyncQueue(ownerUid: string): Promise<SyncOperation[]> {
  const raw = await AsyncStorage.getItem(storageId(ownerUid));
  if (!raw) return [];
  try {
    const key = await getStorageKey(ownerUid);
    const parsed = JSON.parse(decrypt(raw, key));
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(item => item?.ownerUid === ownerUid);
  } catch {
    return [];
  }
}

async function saveSyncQueue(ownerUid: string, queue: SyncOperation[]): Promise<void> {
  const key = await getStorageKey(ownerUid);
  await AsyncStorage.setItem(storageId(ownerUid), encrypt(JSON.stringify(queue), key));
}

export async function enqueuePersistentSync(
  ownerUid: string,
  operation: Omit<SyncOperation, 'attempts' | 'ownerUid'>
): Promise<SyncOperation[]> {
  const current = await loadSyncQueue(ownerUid);
  const queued = enqueueSync(current, { ...operation, attempts: 0, ownerUid });
  await saveSyncQueue(ownerUid, queued);
  return queued;
}

export async function clearSyncQueue(ownerUid: string): Promise<void> {
  await AsyncStorage.removeItem(storageId(ownerUid));
  await SecureStore.deleteItemAsync(`${KEY_PREFIX}${ownerUid}`);
}

export type SyncSendResult =
  | { status: 'sent' }
  | { status: 'conflict'; message: string }
  | { status: 'retry'; message: string };

export async function flushSyncQueue(
  ownerUid: string,
  send: (operation: SyncOperation) => Promise<SyncSendResult>
): Promise<{ sent: number; conflicts: number; remaining: number; exhausted: number }> {
  let queue = await loadSyncQueue(ownerUid);
  let sent = 0;
  let conflicts = 0;
  let exhausted = 0;

  while (queue.length > 0) {
    const operation = nextSync(queue);
    if (!operation) break;
    if (operation.attempts >= MAX_RETRY_ATTEMPTS) { exhausted += 1; break; }
    const result = await send(operation);
    if (result.status === 'sent') {
      queue = queue.filter(item => item.id !== operation.id);
      await saveSyncQueue(ownerUid, queue);
      sent += 1;
      continue;
    }
    if (result.status === 'conflict') { conflicts += 1; break; }
    queue = markSyncRetry(queue, operation.id);
    await saveSyncQueue(ownerUid, queue);
    break;
  }
  return { sent, conflicts, remaining: queue.length, exhausted };
}