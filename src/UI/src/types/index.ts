import type { User } from 'firebase/auth';

export interface Job {
  id: string;
  params: {
    url: string;
    date_str: string;
    theatres: string[];
    language?: string;
    format?: string;
  };
  url: string;
  movie_name: string;
  language?: string;
  format?: string;
  date_str: string;
  theatres: string[];
  service_provider: string;
  notification_medium: string;
  notification_config: {
    recipient_email?: string;
    webhook_url?: string;
    phone_number?: string;
  };
  check_interval: number;
  created_at: string;
  status: string;
  last_checked_at: string | null;
  last_result: string;
  created_by?: string;
  user_name?: string;
  user_email?: string;
  // Multi-channel & Payment metadata
  phone_number?: string;
  sms_consent?: boolean;
  whatsapp_consent?: boolean;
  call_consent?: boolean;
  payment_method?: string; // 'wallet', 'cashfree', 'gateway', 'free'
  payment_id?: string;
  price_paise?: number;
  price_config_id?: string;
  notification_status?: string; // 'pending', 'sent', 'delivered', 'failed', 'policy_exempt'
  notification_retries?: number;
  notification_error?: string;
  refund_issued?: boolean;
  refund_reason?: string;
  policy_exempt_reason?: string;
}

export interface AppConfig {
  config_error: string | null;
  smtp_server: string | null;
  smtp_email: string | null;
  default_check_interval: number;
  recaptcha_site?: string;
  disable_security?: boolean;
  disable_approval?: boolean;
  disable_payments?: boolean;
  notification_provider?: string;
  payment_gateway?: string;
  current_terms_version?: string;
  environment?: string;
}

export interface UserClaims {
  authorized?: boolean;
  role?: string;
  blocked?: boolean;
  search_bookmyshow?: boolean;
  [key: string]: any;
}

export interface HeaderProps {
  user: User | null;
  claims: UserClaims | null;
  config?: AppConfig | null;
}

export interface WalletBalance {
  uid: string;
  balance_paise: number;
  balance_inr: number;
  version: number;
}

export interface WalletTransaction {
  id: string;
  uid: string;
  type: string; // 'WALLET_TOPUP', 'JOB_PAYMENT', 'JOB_CANCELLATION_REFUND', 'DELIVERY_FAILURE_REFUND', 'ADMIN_CREDIT', 'ADMIN_DEBIT'
  direction: 'CREDIT' | 'DEBIT';
  amount_paise: number;
  balance_before_paise: number;
  balance_after_paise: number;
  description: string;
  job_id?: string;
  payment_id?: string;
  refund_id?: string;
  idempotency_key: string;
  created_at: string;
  created_by?: string;
}

export interface PricingConfig {
  id: string;
  sms_paise: number;
  whatsapp_paise: number;
  phone_call_paise: number;
  email_paise: number;
  discord_paise: number;
  is_current?: boolean;
  effective_from?: string;
  superseded_at?: string | null;
  updated_by?: string;
  note?: string;
  created_at?: string;
}

export interface NotificationConsents {
  sms_consented: boolean;
  whatsapp_consented: boolean;
  call_consented: boolean;
  email_consented?: boolean;
  discord_consented?: boolean;
  sms_consented_at?: string | null;
  whatsapp_consented_at?: string | null;
  call_consented_at?: string | null;
  email_consented_at?: string | null;
  discord_consented_at?: string | null;
}

export interface NotificationMediumConfig {
  id: string; // 'email' | 'discord' | 'sms' | 'whatsapp' | 'phone_call'
  type: string;
  label: string;
  details: string;
  is_configured: boolean;
  consent_required: boolean;
  is_consented: boolean;
  price_paise?: number;
}

export interface UserProfileData {
  uid: string;
  email: string;
  phone_number?: string;
  discord_webhook_url?: string;
  email_medium_address?: string;
  preferences: {
    default_notification_medium?: string;
    [key: string]: any;
  };
  consents: NotificationConsents;
  terms_accepted: boolean;
  terms_version_accepted?: string;
  configured_mediums: NotificationMediumConfig[];
}

export interface AdminAuditLog {
  id: string;
  admin_uid: string;
  admin_email: string;
  action_type: string;
  target_uid?: string;
  amount_paise?: number;
  reason?: string;
  old_value?: any;
  new_value?: any;
  metadata?: any;
  created_at: string;
}
