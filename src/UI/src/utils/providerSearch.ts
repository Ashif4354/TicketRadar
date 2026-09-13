// src/UI/src/utils/providerSearch.ts

import type { UserClaims } from '../types';

export const PROVIDER_SEARCH_CAPABLE: Record<string, boolean> = {
  bookmyshow: true,
};

/**
 * Determines whether a user can search through a provider.
 * Provider search is rolled out to all users for all search-capable providers.
 *
 * @param providerKey - The provider identifier.
 * @param _claims - The user's claims (optional, retained for backwards compatibility).
 * @returns `true` if the provider supports search, `false` otherwise.
 */
export function hasProviderSearch(providerKey: string, _claims?: UserClaims | null): boolean {
  const pKey = providerKey.toLowerCase();
  return Boolean(PROVIDER_SEARCH_CAPABLE[pKey]);
}

