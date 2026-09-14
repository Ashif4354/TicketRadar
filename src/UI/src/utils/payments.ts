import type { AppConfig } from '../types';

/**
 * Determines whether payment and wallet features should be disabled.
 *
 * Payments are considered disabled if EITHER:
 * 1. The Vite environment variable `VITE_DISABLE_PAYMENTS === 'true'` (or fallback `DISABLE_PAYMENTS === 'true'`).
 * 2. The backend application configuration returns `disable_payments === true`.
 *
 * @param config Optional AppConfig object fetched from /api/config
 * @returns true if payments and wallet features should be disabled, false otherwise
 */
export const isPaymentsDisabled = (config?: AppConfig | null): boolean => {
  const envVal = String(
    import.meta.env.VITE_DISABLE_PAYMENTS ??
    import.meta.env.DISABLE_PAYMENTS ??
    ''
  ).trim().toLowerCase();

  if (envVal === 'true' || envVal === '1') {
    return true;
  }
  if (config && (config.disable_payments === true || String(config.disable_payments).toLowerCase() === 'true')) {
    return true;
  }
  return false;
};
