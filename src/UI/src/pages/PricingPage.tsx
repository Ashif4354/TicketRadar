import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Mail, MessageSquare, Phone, PhoneCall,
  Check, ArrowRight, ShieldCheck, RefreshCw, Zap
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { authenticatedFetch } from '../utils/api';
import { isPaymentsDisabled } from '../utils/payments';
import type { AppConfig } from '../types';

interface PricingPageProps {
  config?: AppConfig | null;
}

interface PriceData {
  sms_paise: number;
  whatsapp_paise: number;
  phone_call_paise: number;
  email_paise: number;
  discord_paise: number;
  sms_inr: number;
  whatsapp_inr: number;
  phone_call_inr: number;
  email_inr: number;
  discord_inr: number;
}

export function PricingPage({ config }: PricingPageProps = {}) {
  const [prices, setPrices] = useState<PriceData>({
    sms_paise: 50,
    whatsapp_paise: 100,
    phone_call_paise: 150,
    email_paise: 0,
    discord_paise: 0,
    sms_inr: 0.50,
    whatsapp_inr: 1.00,
    phone_call_inr: 1.50,
    email_inr: 0.0,
    discord_inr: 0.0,
  });

  const paymentsDisabled = isPaymentsDisabled(config);

  useEffect(() => {
    authenticatedFetch('/api/payments/prices')
      .then((res) => res.json())
      .then((data) => {
        if (data && !data.detail) {
          setPrices({
            sms_paise: data.sms_paise ?? 50,
            whatsapp_paise: data.whatsapp_paise ?? 100,
            phone_call_paise: data.phone_call_paise ?? 150,
            email_paise: data.email_paise ?? 0,
            discord_paise: data.discord_paise ?? 0,
            sms_inr: (data.sms_paise ?? 50) / 100,
            whatsapp_inr: (data.whatsapp_paise ?? 100) / 100,
            phone_call_inr: (data.phone_call_paise ?? 150) / 100,
            email_inr: (data.email_paise ?? 0) / 100,
            discord_inr: (data.discord_paise ?? 0) / 100,
          });
        }
      })
      .catch((err) => console.error('Failed to fetch pricing:', err));
  }, []);

  const formatPrice = (paise: number, inr: number) => {
    if (paymentsDisabled || paise === 0) {
      return { tag: 'Free', isFree: true, sub: '₹0.00 / alert' };
    }
    return {
      tag: `₹${inr.toFixed(2)}`,
      isFree: false,
      sub: `${paise} paise / alert`,
    };
  };

  const mediums = [
    {
      name: 'Email Alert',
      icon: Mail,
      accent: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
      description: 'HTML & plain-text breakdown of available & unavailable theatres sent to your inbox.',
      pricing: formatPrice(prices.email_paise, prices.email_inr),
      features: [
        'Formatted theatre availability tables',
        'Direct 1-click BookMyShow booking link',
        'Unlimited free monitoring alerts',
        'Primary & custom email addresses supported',
      ],
      popular: false,
    },
    {
      name: 'Discord Webhook',
      icon: MessageSquare,
      accent: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/30',
      description: 'Rich embedded notification posted directly to your personal or group Discord server.',
      pricing: formatPrice(prices.discord_paise, prices.discord_inr),
      features: [
        'Clean ASCII table of open cinemas',
        'Real-time webhook trigger (sub-second)',
        'Share with cinema groups and friends',
        'Custom channel webhook configuration',
      ],
      popular: false,
    },
    {
      name: 'SMS Notification',
      icon: Phone,
      accent: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
      description: 'Direct SMS message delivered straight to your Indian mobile (+91) carrier.',
      pricing: formatPrice(prices.sms_paise, prices.sms_inr),
      features: [
        'Instant telecom delivery to Indian carriers',
        'Top 3 available cinemas summarized',
        'Works offline without internet connection',
        '100% refund to original method (wallet included) if we fail to send notification',
      ],
      popular: false,
    },
    {
      name: 'WhatsApp Alert',
      icon: MessageSquare,
      accent: 'text-green-400 bg-green-500/10 border-green-500/30',
      description: 'Pre-approved WhatsApp business template sent directly to your chat.',
      pricing: formatPrice(prices.whatsapp_paise, prices.whatsapp_inr),
      features: [
        'Official WhatsApp Business template',
        'Direct clickable BookMyShow URL button',
        'Highest open-rate notification channel',
        '100% refund to original method (wallet included) if we fail to send notification',
      ],
      popular: true,
    },
    {
      name: 'Automated Voice Call',
      icon: PhoneCall,
      accent: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
      description: 'High-priority voice phone call using Amazon Polly Indian-English (Aditi) TTS.',
      pricing: formatPrice(prices.phone_call_paise, prices.phone_call_inr),
      features: [
        'Amazon Polly (en-IN) crystal-clear TTS',
        'Up to 3 automatic call retry attempts',
        'Bypasses silent mode & notification fatigue',
        'Fallback email sent if unanswered 3 times',
      ],
      popular: false,
    },
  ];

  return (
    <div className="container mx-auto px-4 py-12 max-w-6xl space-y-12 animate-in fade-in duration-300">
      {/* Header Section */}
      <div className="text-center space-y-4 max-w-2xl mx-auto">
        <Badge className="bg-rose-500/10 text-rose-400 border-rose-500/20 text-xs px-3 py-1 font-semibold tracking-wide uppercase">
          Dynamic Pricing Schedule
        </Badge>
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
          Transparent, Pay-per-Alert Pricing
        </h1>
        <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
          Monitor BookMyShow showtimes 24/7. Never overpay — all prices are set dynamically by the administrator, and you only pay when tickets actually open.
        </p>
      </div>

      {/* Pricing Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {mediums.map((m) => {
          const Icon = m.icon;
          return (
            <Card
              key={m.name}
              className={`relative border glassmorphism rounded-2xl flex flex-col justify-between transition-all hover:border-rose-500/40 hover:shadow-lg ${
                m.popular ? 'border-rose-500/50 shadow-rose-500/10' : 'border-border/80'
              }`}
            >
              {m.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <Badge className="bg-rose-500 text-white text-[10px] font-bold px-3 py-0.5 shadow-md">
                    Most Popular
                  </Badge>
                </div>
              )}

              <CardHeader className="space-y-3 pb-4">
                <div className="flex items-center justify-between">
                  <div className={`h-10 w-10 rounded-xl flex items-center justify-center border ${m.accent}`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <Badge
                    className={`text-xs font-bold px-2.5 py-1 ${
                      m.pricing.isFree
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                        : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                    }`}
                  >
                    {m.pricing.tag}
                  </Badge>
                </div>
                <div>
                  <CardTitle className="text-base font-bold text-foreground">{m.name}</CardTitle>
                  <CardDescription className="text-xs text-muted-foreground mt-1 line-clamp-2">
                    {m.description}
                  </CardDescription>
                </div>
                <div className="pt-2">
                  <div className="text-2xl font-extrabold text-foreground">
                    {m.pricing.isFree ? 'Free' : m.pricing.tag}
                    {!m.pricing.isFree && (
                      <span className="text-xs font-normal text-muted-foreground ml-1">/ alert</span>
                    )}
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-0.5">{m.pricing.sub}</p>
                </div>
              </CardHeader>

              <CardContent className="space-y-4 pt-0">
                <div className="border-t border-border/40 pt-4 space-y-2.5">
                  <p className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">Features</p>
                  <ul className="space-y-2 text-xs text-muted-foreground">
                    {m.features.map((f, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <Check className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="pt-2">
                  <Link
                    to="/app"
                    className="flex items-center justify-center gap-1.5 w-full h-9 rounded-lg text-xs font-bold bg-muted/30 hover:bg-rose-500 hover:text-white border border-border/60 transition-all cursor-pointer"
                  >
                    Configure in Dashboard <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Trust & Refund Policy Section */}
      <div className="rounded-2xl border border-border/70 bg-[#12141c] p-8 space-y-6">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center border border-emerald-500/20">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-foreground">Fair & Transparent Billing Guarantee</h3>
            <p className="text-xs text-muted-foreground">Everything you need to know about your wallet balance and charges.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-xs text-muted-foreground">
          <div className="space-y-2">
            <h4 className="font-bold text-foreground text-sm flex items-center gap-1.5">
              <Zap className="h-4 w-4 text-amber-400" />
              Pay Only Upon Success
            </h4>
            <p className="leading-relaxed">
              Tracking a movie showtime does not lock up your money. If tickets never open for your target date, you are never charged for tracking.
            </p>
          </div>

          <div className="space-y-2">
            <h4 className="font-bold text-foreground text-sm flex items-center gap-1.5">
              <RefreshCw className="h-4 w-4 text-emerald-400" />
              Instant Automated Refunds
            </h4>
            <p className="leading-relaxed">
              If you cancel, 100% is refunded only to your wallet. Only if we fail to send you notification (you didn&apos;t cancel, and the tracker was running), 100% of your fee is refunded to your original payment method, wallet included.{' '}
              <Link to="/refund" className="text-primary hover:underline font-semibold inline-flex items-center gap-0.5">
                View Policy &rarr;
              </Link>
            </p>
          </div>

          <div className="space-y-2">
            <h4 className="font-bold text-foreground text-sm flex items-center gap-1.5">
              <ShieldCheck className="h-4 w-4 text-blue-400" />
              Easy Top-ups
            </h4>
            <p className="leading-relaxed">
              Top up your digital wallet via UPI, Debit/Credit Cards, or Netbanking. Quick select presets of ₹5, ₹10, ₹25, and ₹50 make it simple to keep just what you need.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
