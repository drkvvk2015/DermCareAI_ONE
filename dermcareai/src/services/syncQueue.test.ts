import { enqueueSync, nextSync, markSyncRetry, SyncOperation } from "./syncQueue";

const op = (id: string, createdAt: number): SyncOperation => ({
  id, method: "POST", path: "/api/v1/clinical/media", createdAt, attempts: 0,
});

test("deduplicates operations and preserves FIFO ordering", () => {
  const queue = enqueueSync(enqueueSync([], op("b", 2)), op("a", 1));
  expect(enqueueSync(queue, op("a", 1))).toHaveLength(2);
  expect(nextSync(queue)?.id).toBe("a");
});

test("increments retry count without changing other operations", () => {
  const queue = [op("a", 1), op("b", 2)];
  const updated = markSyncRetry(queue, "a");
  expect(updated[0].attempts).toBe(1);
  expect(updated[1].attempts).toBe(0);
});
