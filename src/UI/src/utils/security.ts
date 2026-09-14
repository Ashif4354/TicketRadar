import type { AppConfig } from '../types';

let globalConfig: AppConfig | null = null;

export const setSecurityConfig = (config: AppConfig | null): void => {
  globalConfig = config;
};

export const isSecurityDisabled = (config?: AppConfig | null): boolean => {
  if (import.meta.env.VITE_DISABLE_SECURITY === 'true' || import.meta.env.DISABLE_SECURITY === 'true') {
    return true;
  }
  const effectiveConfig = config !== undefined ? config : globalConfig;
  if (effectiveConfig && effectiveConfig.disable_security === true) {
    return true;
  }
  return false;
};

export const isApprovalDisabled = (config?: AppConfig | null): boolean => {
  if (isSecurityDisabled(config)) {
    return true;
  }
  if (import.meta.env.VITE_DISABLE_APPROVAL === 'true' || import.meta.env.DISABLE_APPROVAL === 'true') {
    return true;
  }
  const effectiveConfig = config !== undefined ? config : globalConfig;
  if (effectiveConfig && effectiveConfig.disable_approval === true) {
    return true;
  }
  return false;
};
