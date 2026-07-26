// src/UI/src/utils/providerSearch.ts

import type { UserClaims } from '../types';

export const PROVIDER_SEARCH_CAPABLE: Record<string, boolean> = {
  bookmyshow: true,
};

export function hasProviderSearch(providerKey: string, claims: UserClaims | null): boolean {
  const pKey = providerKey.toLowerCase();
  if (!PROVIDER_SEARCH_CAPABLE[pKey]) return false;
  if (claims?.role === 'admin') return true;
  return claims?.[`search_${pKey}`] === true;
}
