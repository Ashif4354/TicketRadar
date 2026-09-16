import { Link } from 'react-router-dom';
import { ArrowLeft, FileText } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';

export function TermsPage() {
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
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary border border-primary/20">
              <FileText className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-2xl sm:text-3xl font-extrabold tracking-tight">Terms & Conditions (v2.0)</CardTitle>
              <CardDescription className="text-xs text-muted-foreground mt-1">
                Last updated: September 2026 • General Terms of Service for TicketRadar Multi-Channel & Payment System
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0 space-y-6 text-sm leading-relaxed text-foreground/90">
          <section className="space-y-2">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-primary inline-block"></span>
              1. Acceptance of Terms
            </h3>
            <p className="text-muted-foreground">
              By accessing, browsing, or using TicketRadar ("the Service"), you acknowledge that you have read, understood, and agree to be bound by these Terms and Conditions (v2.0). If you do not agree to these terms, do not use the platform.
            </p>
          </section>

          <section className="space-y-2">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-primary inline-block"></span>
              2. Description of Service
            </h3>
            <p className="text-muted-foreground">
              TicketRadar is an automated alert monitoring tool designed to track showtime releases and ticket availability on BookMyShow. TicketRadar sends real-time notifications via Email, Discord Webhook, SMS, WhatsApp, and Automated Phone Calls when showtimes match user criteria. TicketRadar is strictly a monitoring utility and does not directly sell, reserve, or issue tickets.
            </p>
          </section>

          <section className="space-y-2">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-primary inline-block"></span>
              3. Non-Affiliation Disclaimer
            </h3>
            <p className="text-muted-foreground">
              TicketRadar is an independent platform and is <strong>NOT affiliated, associated, authorized, endorsed by, or in any way officially connected with BookMyShow</strong> or Bigtree Entertainment Pvt. Ltd., or any of their subsidiaries or affiliates. All product names, logos, and brands are property of their respective owners.
            </p>
          </section>

          <section className="space-y-2">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-primary inline-block"></span>
              4. Multi-Channel Notifications
            </h3>
            <p className="text-muted-foreground">
              TicketRadar supports multiple delivery mediums: Email, Discord Webhooks, SMS, WhatsApp messages, and Automated Voice Calls. Automated voice calls and messaging alerts use Text-to-Speech (TTS) Indian English synthesis (Polly.Aditi) and authorized telecommunications carrier networks (including Twilio, as well as future telecommunication options like Plivo). Notifications are sent only to numbers validated under Indian numbering plans (+91 E.164).
            </p>
          </section>

          <section className="space-y-2">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-primary inline-block"></span>
              5. Explicit Consent & Opt-In/Opt-Out
            </h3>
            <p className="text-muted-foreground">
              In accordance with telecom regulations and consumer privacy standards, automated alerts via SMS, WhatsApp, and Phone Calls require explicit affirmative opt-in consent. You can view, grant, or revoke your consent anytime via your TicketRadar Profile. Revoking consent will block automated alerts from dispatching on that channel.
            </p>
          </section>

          <section className="space-y-2">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-primary inline-block"></span>
              6. Wallet & Pricing
            </h3>
            <p className="text-muted-foreground">
              Users may add funds denominated in Indian Rupees (₹) stored in their digital TicketRadar Wallet (100 paise = ₹1.00) via authorized third-party payment processors (Cashfree, as well as future integration options like Razorpay and Stripe). Free channels (Email, Discord) incur ₹0.00 charge. Paid channels (SMS, WhatsApp, Phone Calls) are priced according to the active pricing schedule at job creation.
            </p>
            <p className="text-muted-foreground font-semibold">
              WALLET BALANCES ARE STRICTLY NON-WITHDRAWABLE. Wallet balances cannot be redeemed for physical cash, bank transfers, or UPI payouts under any circumstances.
            </p>
          </section>

          <section className="space-y-2">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-primary inline-block"></span>
              7. Cancellation & Refund Policy
            </h3>
            <ul className="list-disc list-inside space-y-1 text-muted-foreground">
              <li><strong>Pre-Notification Cancellation (Wallet Only):</strong> If you cancel or delete a monitoring job before tickets open and notifications are dispatched, 100% of the price is refunded only to your TicketRadar Wallet.</li>
              <li><strong>Notification Delivery Failure (Original Method):</strong> Only if we fail to send you notification (you didn&apos;t cancel, and the tracker was running), we will give you a 100% refund to your original payment method, wallet included (refunded immediately to your wallet if paid with wallet balance; reversed directly to your original source payment method if paid via online gateway).</li>
              <li><strong>Unanswered/Busy Calls (Policy-Exempt):</strong> If an automated voice call is placed and goes unanswered, busy, or rejected across 3 immediate attempts, the system logs the alert as a policy-exempt completed delivery, sends an emergency fallback email notification, and NO refund is issued due to telecom termination charges incurred.</li>
              <li><strong>Gateway Refunds:</strong> In the event of duplicate billing or administrative review, refunds for online gateway payments can only be processed back to the original payment method via authorized third-party payment gateways (Cashfree, as well as future integration options like Razorpay and Stripe) by system administrators.</li>
            </ul>
            <p className="text-xs text-muted-foreground pt-1">
              For complete details, conditions, and gateway timelines, please consult our dedicated{' '}
              <Link to="/refund" className="text-primary font-semibold hover:underline">
                Cancellation & Refund Policy
              </Link>.
            </p>
          </section>

          <section className="space-y-2">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-primary inline-block"></span>
              8. Third-Party Infrastructure & Service Providers
            </h3>
            <p className="text-muted-foreground">
              TicketRadar utilizes trusted third-party infrastructure and service partners for message delivery, payment gateway processing, authentication, and cloud hosting:
            </p>
            <ul className="list-disc list-inside space-y-1 text-muted-foreground">
              <li><strong>Payment Processors:</strong> Cashfree, as well as future integration options like Razorpay and Stripe, for PCI-DSS compliant Indian and international payment processing (UPI, Netbanking, Cards).</li>
              <li><strong>Telecommunications / Notification Providers:</strong> Twilio, as well as future telecommunication options like Plivo, for SMS, WhatsApp business API, and Voice programmable telephony.</li>
              <li><strong>Authentication & Cloud Infrastructure:</strong> Google Firebase and Google Cloud Platform for secure user authentication, managed serverless compute, and distributed Firestore database storage.</li>
              <li><strong>Amazon Web Services (AWS Polly):</strong> For Indian English neural text-to-speech voice synthesis.</li>
              <li><strong>Webhook & Platform Integrations:</strong> Discord (Discord Inc.) for delivering real-time showtime alerts to Discord channels.</li>
              <li><strong>Email Delivery Providers:</strong> SMTP email services (including Google Gmail and standard SMTP relay infrastructure) for transactional notifications and account alerts.</li>
            </ul>
            <p className="text-muted-foreground mt-2">
              User payments, SMS, WhatsApp, and phone call alerts may be processed via these authorized third-party service partners in compliance with their respective service terms and privacy guidelines.
            </p>
          </section>

          <section className="space-y-2">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-primary inline-block"></span>
              9. Best-Effort Service & Availability
            </h3>
            <p className="text-muted-foreground">
              All alert checks and notifications are provided on a best-effort basis. While TicketRadar strives to maintain high uptime and prompt delivery, we do not warrant or guarantee that notifications will be instantaneous, uninterrupted, or error-free.
            </p>
          </section>

          <section className="space-y-2">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-primary inline-block"></span>
              10. Limitation of Liability
            </h3>
            <p className="text-muted-foreground">
              To the fullest extent permitted by applicable law, TicketRadar and its maintainers shall not be liable for any direct, indirect, incidental, special, or consequential damages resulting from missed movie shows, sold-out tickets, notification delays, telecom network outages, or third-party service downtime.
            </p>
          </section>
        </CardContent>
      </Card>
    </main>
  );
}
