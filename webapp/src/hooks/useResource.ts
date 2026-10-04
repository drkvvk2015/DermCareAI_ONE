import { signOut } from 'firebase/auth';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '../api/client';
import { useSession } from '../auth/Session';
import { auth } from '../firebase';

export function useResource<T>(loader: (user: NonNullable<ReturnType<typeof useSession>['user']>) => Promise<T>, key: string) {
  const { user } = useSession();
  const [resource, setResource] = useState<{ userId: string; key: string; data: T } | null>(null);
  const [error, setError] = useState<unknown>();
  const [loading, setLoading] = useState(true);
  const loaderRef = useRef(loader);
  const requestIdRef = useRef(0);
  loaderRef.current = loader;

  const reload = useCallback(async () => {
    if (!user) return;
    const requestId = ++requestIdRef.current;
    setLoading(true);
    setError(undefined);
    try {
      const result = await loaderRef.current(user);
      if (requestId === requestIdRef.current) setResource({ userId: user.uid, key, data: result });
    } catch (reason) {
      if (requestId === requestIdRef.current) {
        setError(reason);
        if (reason instanceof ApiError && reason.status === 401 && auth) await signOut(auth);
      }
    } finally {
      if (requestId === requestIdRef.current) setLoading(false);
    }
  }, [user, key]);

  useEffect(() => {
    void reload();
    return () => { requestIdRef.current += 1; };
  }, [reload, key]);
  return {
    data: user && resource?.userId === user.uid && resource.key === key ? resource.data : null,
    error,
    loading,
    reload,
  };
}
