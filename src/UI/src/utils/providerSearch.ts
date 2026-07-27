// src/UI/src/utils/providerSearch.ts

import type { UserClaims } from '../types';

export const PROVIDER_SEARCH_CAPABLE: Record<string, boolean> = {
  bookmyshow: true,
};

/**
 * Determines whether a user can search through a provider.
 *
 * @param providerKey - The provider identifier.
 * @param claims - The user's claims, or `null` when unavailable.
 * @returns `true` if the provider supports search and the user is an administrator or has the provider-specific search claim, `false` otherwise.
 */
export function hasProviderSearch(providerKey: string, claims: UserClaims | null): boolean {
  const pKey = providerKey.toLowerCase();
  if (!PROVIDER_SEARCH_CAPABLE[pKey]) return false;
  if (claims?.role === 'admin') return true;
  return claims?.[`search_${pKey}`] === true;
}
