import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, ShieldCheck } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';

export function PrivacyPage() {
  return (
    <main className="flex-1 container mx-auto max-w-4xl px-4 py-10 sm:px-6">
      <div className="mb-6">
        <Link to="/" className="inline-flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors bg-muted/30 px-3 py-1.5 rounded-lg border border-border/50">
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Home
        </Link>
      </div>

      <Card className="border border-border/80 shadow-2xl glassmorphism glow-primary p-6 sm:p-10 rounded-2xl space-y-8">
        <CardHeader className="p-0 border-b border-border/60 pb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-2xl sm:text-3xl font-extrabold tracking-tight">Privacy Policy</CardTitle>
              <CardDescription className="text-xs text-muted-foreground mt-1">
                Last updated: July 2026 • How TicketRadar collects, protects, and uses your data
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0 space-y-6 text-sm leading-relaxed text-foreground/90">
          <section className="space-y-2">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500 inline-block"></span>
              1. Overview
            </h3>
            <p className="text-muted-foreground">
              TicketRadar respects your privacy. This Privacy Policy outlines what information we gather, how we utilize it to provide ticket monitoring services, and how we keep your personal details secure.
            </p>
          </section>

          <section className="space-y-2">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500 inline-block"></span>
              2. Information We Collect
            </h3>
            <div className="text-muted-foreground space-y-2">
              <p>When you use TicketRadar, we collect limited personal information necessary to deliver alerts:</p>
              <ul className="list-disc pl-5 space-y-1">
                <li><strong>Account Credentials:</strong> Google Name, Email Address, and Avatar URL obtained via Google OAuth login.</li>
                <li><strong>Monitoring Configurations:</strong> Monitored movie URLs, target show dates, selected theaters, polling frequency, and designated alert recipients (Email address or Webhook URL).</li>
                <li><strong>Security & Uptime Logs:</strong> Firebase App Check tokens and IP security headers required for bot prevention and system reliability.</li>
              </ul>
            </div>
          </section>

          <section className="space-y-2">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500 inline-block"></span>
              3. How We Use Your Data
            </h3>
            <p className="text-muted-foreground">
              We process your data strictly to execute ticket monitoring jobs created by you and dispatch alert notifications when tickets become available. We do not use your personal information for marketing campaigns, advertising, or profiling.
            </p>
          </section>

          <section className="space-y-2">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500 inline-block"></span>
              4. Data Protection & Zero Third-Party Selling
            </h3>
            <p className="text-muted-foreground">
              We maintain strict safeguards to protect your information. <strong>We do NOT sell, rent, trade, or share your personal data with third-party advertisers or data brokers.</strong> Authentication tokens and secrets are stored using secure encryption protocols.
            </p>
          </section>

          <section className="space-y-2">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500 inline-block"></span>
              5. Third-Party Integrations
            </h3>
            <p className="text-muted-foreground">
              TicketRadar utilizes Google Firebase for secure user authentication and reCAPTCHA Enterprise for App Check verification. When monitoring showtime listings, TicketRadar inspects publicly available event data; no user personal identifiers are sent to third-party cinema sites.
            </p>
          </section>

          <section className="space-y-2">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500 inline-block"></span>
              6. Your Control & Data Deletion
            </h3>
            <p className="text-muted-foreground">
              You retain full control over your data. You may pause or delete active alert tasks at any time directly from the TicketRadar dashboard. If you wish to delete your account or stored alert history entirely, you may do so by logging out and requesting task purge via our repository.
            </p>
          </section>

          <div className="pt-4 border-t border-border/60 flex items-center justify-between text-xs text-muted-foreground">
            <span>Repository: <a href="https://github.com/Ashif4354/TicketRadar" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline font-mono">Ashif4354/TicketRadar</a></span>
            <Link to="/" className="text-primary hover:underline font-medium">Return to App</Link>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
