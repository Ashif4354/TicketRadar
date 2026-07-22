import { getAuthToken, getAppCheckToken } from '../lib/firebase';

export const authenticatedFetch = async (url: string, options: RequestInit = {}): Promise<Response> => {
  const headers = { ...(options.headers || {}) } as Record<string, string>;
  
  const idToken = await getAuthToken();
  if (idToken) {
    headers['Authorization'] = `Bearer ${idToken}`;
  }
  
  const appCheckToken = await getAppCheckToken();
  if (appCheckToken) {
    headers['X-Firebase-AppCheck'] = appCheckToken;
  }
  
  let targetUrl = url;
  if (url.startsWith('/')) {
    const backendUrl = import.meta.env.VITE_BACKEND_URL || '';
    const cleanBackendUrl = backendUrl.endsWith('/') ? backendUrl.slice(0, -1) : backendUrl;
    targetUrl = `${cleanBackendUrl}${url}`;
  }
  
  return fetch(targetUrl, {
    ...options,
    headers
  });
};
