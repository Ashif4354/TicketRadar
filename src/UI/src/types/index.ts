import type { User } from 'firebase/auth';

export interface Job {
  id: string;
  params: {
    url: string;
    date_str: string;
    theatres: string[];
  };
  url: string;
  movie_name: string;
  date_str: string;
  theatres: string[];
  service_provider: string;
  notification_medium: string;
  notification_config: {
    recipient_email?: string;
    webhook_url?: string;
  };
  check_interval: number;
  created_at: string;
  status: string;
  last_checked_at: string | null;
  last_result: string;
  created_by?: string;
}

export interface AppConfig {
  config_error: string | null;
  smtp_server: string | null;
  smtp_email: string | null;
  default_check_interval: number;
  recaptcha_site?: string;
}

export interface UserClaims {
  authorized?: boolean;
  role?: string;
  blocked?: boolean;
  [key: string]: any;
}

export interface HeaderProps {
  user: User | null;
  claims: UserClaims | null;
}
