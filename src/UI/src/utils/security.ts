import type { AppConfig } from '../types';

export const isSecurityDisabled = (config?: AppConfig | null): boolean => {
  if (import.meta.env.VITE_DISABLE_SECURITY === 'true' || import.meta.env.DISABLE_SECURITY === 'true') {
    return true;
  }
  if (config && config.disable_security === true) {
    return true;
  }
  return false;
};
