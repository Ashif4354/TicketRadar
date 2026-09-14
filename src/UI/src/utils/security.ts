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

export const getEnvironment = (config?: AppConfig | null): string => {
  if (isSecurityDisabled(config)) {
    return 'development';
  }
  const effectiveConfig = config !== undefined ? config : globalConfig;
  if (effectiveConfig && effectiveConfig.environment) {
    return effectiveConfig.environment.toLowerCase();
  }
  const viteEnv = import.meta.env.VITE_ENVIRONMENT || import.meta.env.ENVIRONMENT;
  if (viteEnv) {
    return viteEnv.toLowerCase();
  }
  return import.meta.env.DEV ? 'development' : 'production';
};
