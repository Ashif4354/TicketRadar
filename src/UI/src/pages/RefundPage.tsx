import { Link } from 'react-router-dom';
import {
  ArrowLeft,
  RotateCcw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  CreditCard,
  Wallet,
  PhoneCall,
  HelpCircle,
  ExternalLink,
  ShieldCheck,
  Zap
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';

export function RefundPage() {
  return (
    <main className="flex-1 container mx-auto max-w-4xl px-4 py-10 sm:px-6">
      <div className="mb-6">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors bg-muted/30 px-3 py-1.5 rounded-lg border border-border/50"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Home
        </Link>
      </div>

      <Card className="border border-border/80 shadow-2xl glassmorphism glow-primary p-6 sm:p-10 rounded-2xl space-y-8">
        <CardHeader className="p-0 border-b border-border/60 pb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
              <RotateCcw className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-2xl sm:text-3xl font-extrabold tracking-tight">
                Cancellation & Refund Policy (v2.0)
              </CardTitle>
              <CardDescription className="text-xs text-muted-foreground mt-1">
                Last updated: September 2026 • TicketRadar Multi-Channel Monitoring & Payment System
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0 space-y-8 text-sm leading-relaxed text-foreground/90">
          <section className="space-y-3">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-rose-500 inline-block"></span>
              1. Overview & Fair Billing Commitment
            </h3>
            <p className="text-muted-foreground">
              TicketRadar is built to provide reliable, automated movie showtime alerts across Email, Discord, SMS, WhatsApp, and Phone Calls. We adhere strictly to a fair, transparent billing philosophy: you are only charged when services are rendered, and automated safeguards protect your balance against delivery issues or pre-release cancellations.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
              <div className="bg-muted/20 border border-border/50 rounded-xl p-4 space-y-1.5">
                <div className="font-semibold text-xs text-foreground flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                  Your Cancellation (Wallet Only)
                </div>
                <p className="text-xs text-muted-foreground">
                  If you cancel, 100% of the price is refunded only to your wallet.
                </p>
              </div>

              <div className="bg-muted/20 border border-border/50 rounded-xl p-4 space-y-1.5">
                <div className="font-semibold text-xs text-foreground flex items-center gap-1.5">
                  <RotateCcw className="h-4 w-4 text-emerald-400 shrink-0" />
                  Failed Notification (Original Method)
                </div>
                <p className="text-xs text-muted-foreground">
                  Only if we fail to send you notification (you didn&apos;t cancel, and the tracker was running), refund is issued 100% to your original payment method, wallet included.
                </p>
              </div>

              <div className="bg-muted/20 border border-border/50 rounded-xl p-4 space-y-1.5">
                <div className="font-semibold text-xs text-foreground flex items-center gap-1.5">
                  <XCircle className="h-4 w-4 text-amber-400 shrink-0" />
                  Unanswered Voice Calls (Exempt)
                </div>
                <p className="text-xs text-muted-foreground">
                  Voice calls unanswered, busy, or rejected across 3 attempts incur telecom termination costs and are exempt from refunds. A free emergency email is sent.
                </p>
              </div>

              <div className="bg-muted/20 border border-border/50 rounded-xl p-4 space-y-1.5">
                <div className="font-semibold text-xs text-foreground flex items-center gap-1.5">
                  <CreditCard className="h-4 w-4 text-blue-400 shrink-0" />
                  Gateway Payment Reversals
                </div>
                <p className="text-xs text-muted-foreground">
                  Online top-up payments with duplicate billing or gateway errors are refunded directly to the original payment source within 5–7 business days.
                </p>
              </div>
            </div>
          </section>

          <section className="space-y-3">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <Zap className="h-4 w-4 text-rose-400" />
              2. Pre-Notification Job Cancellations (Wallet Only)
            </h3>
            <div className="text-muted-foreground space-y-2">
              <p>
                You can delete or cancel any active movie monitoring job directly from your TicketRadar Dashboard at any time prior to ticket availability.
              </p>
              <ul className="list-disc pl-5 space-y-1.5 text-xs">
                <li>
                  <strong>Refunded Strictly to Wallet Only:</strong> If you cancel a monitoring job, 100% of the price is refunded strictly to your TicketRadar Wallet only. Cancellations initiated by you are not eligible for payment gateway reversals to bank accounts, UPI, or cards.
                </li>
                <li>
                  <strong>Zero Penalties:</strong> There are no cancellation fees, convenience charges, or administrative deductions applied to pre-notification cancellations.
                </li>
                <li>
                  <strong>Instant Availability:</strong> Refunded wallet credits are available immediately to set up monitoring for another movie, theatre, or showtime.
                </li>
              </ul>
            </div>
          </section>

          <section className="space-y-3">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <RotateCcw className="h-4 w-4 text-rose-400" />
              3. Notification Delivery Failures (Original Method)
            </h3>
            <div className="text-muted-foreground space-y-2">
              <p>
                <strong>Our 100% Delivery Guarantee:</strong> If you cancel, then only refund to wallet. Only if we fail to send you notification (you didn&apos;t cancel, and the tracker was running), then we will give you a 100% refund to your original payment method, wallet included.
              </p>
              <ul className="list-disc pl-5 space-y-1.5 text-xs">
                <li>
                  <strong>Original Payment Method Reversal (Wallet Included):</strong>
                  <ul className="list-[circle] pl-4 pt-1 space-y-1">
                    <li><strong>Paid via TicketRadar Wallet:</strong> 100% of the deduction is immediately credited back to your wallet ledger.</li>
                    <li><strong>Paid via Payment Gateway (UPI / Card / Netbanking):</strong> 100% of the transaction amount is refunded directly back to your source payment method (bank account, debit/credit card, or UPI handle).</li>
                  </ul>
                </li>
                <li>
                  <strong>Automated Retry Cycle:</strong> If an alert dispatch fails due to an upstream gateway error, network timeout, or telecommunications route drop, our dispatcher automatically attempts up to 3 immediate retries before logging a delivery failure and triggering your 100% refund.
                </li>
                <li>
                  <strong>Free Emergency Fallback:</strong> In addition to your 100% refund, our system automatically dispatches an immediate backup email alert to your registered account email at no extra charge.
                </li>
              </ul>
            </div>
          </section>

          <section className="space-y-3">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <PhoneCall className="h-4 w-4 text-amber-400" />
              4. Automated Voice Calls: Policy-Exempt Deliveries
            </h3>
            <div className="text-muted-foreground space-y-2">
              <p>
                Automated phone calls require dedicated telecom circuit allocation and carrier termination infrastructure. Please review our specific policy for voice calls:
              </p>
              <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-200/90 text-xs space-y-1.5">
                <div className="font-semibold flex items-center gap-1.5 text-amber-300">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  Policy-Exempt Unanswered / Busy Calls
                </div>
                <p>
                  When an automated phone call is initiated by TicketRadar and your phone rings but is unanswered, returns a busy signal, or is manually rejected/declined across 3 retry attempts:
                </p>
                <ul className="list-disc pl-4 space-y-1 pt-1">
                  <li>
                    Carrier connection and circuit origination charges have already been incurred with the telecom operator.
                  </li>
                  <li>
                    The alert is officially logged as a <strong>policy-exempt completed delivery</strong>.
                  </li>
                  <li>
                    <strong>No wallet or monetary refund is issued</strong> for calls that went unanswered or were declined by you.
                  </li>
                  <li>
                    An emergency fallback email containing the showtime details and direct booking link is automatically dispatched to ensure you do not miss the booking window.
                  </li>
                </ul>
              </div>
            </div>
          </section>

          <section className="space-y-3">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <Wallet className="h-4 w-4 text-rose-400" />
              5. Digital Wallet Balances & Non-Withdrawable Rule
            </h3>
            <div className="text-muted-foreground space-y-2">
              <p>
                TicketRadar features an in-app digital wallet denominated in Indian Rupees (₹) (100 paise = ₹1.00) to streamline microtransactions for paid communication channels:
              </p>
              <ul className="list-disc pl-5 space-y-1.5 text-xs">
                <li>
                  <strong>Non-Withdrawable Balances:</strong> Wallet balances represent digital utility credits purchased exclusively for triggering TicketRadar notification jobs. Wallet balances cannot be withdrawn, redeemed for physical cash, transferred to personal bank accounts, or paid out via UPI.
                </li>
                <li>
                  <strong>Balance Preservation:</strong> Funds in your TicketRadar Wallet do not have an arbitrary expiry date and remain available in your account as long as your account is active.
                </li>
                <li>
                  <strong>Audit Trail:</strong> Every credit, debit, and automated refund is permanently logged with an immutable timestamp and cryptographic transaction identifier in your Wallet Transaction Ledger.
                </li>
              </ul>
            </div>
          </section>

          <section className="space-y-3">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-rose-400" />
              6. Payment Gateway Refunds (Source Payment Method)
            </h3>
            <div className="text-muted-foreground space-y-2">
              <p>
                Top-up payments made via authorized third-party payment gateways (Cashfree, as well as future integration options like Razorpay and Stripe) may be eligible for a direct refund back to the source payment instrument under specific circumstances:
              </p>
              <ul className="list-disc pl-5 space-y-1.5 text-xs">
                <li>
                  <strong>Eligible Circumstances:</strong>
                  <ul className="list-[circle] pl-4 pt-1 space-y-1">
                    <li>Accidental duplicate payment charges resulting in multiple debit transactions for a single top-up intent.</li>
                    <li>Technical payment gateway communication failures where funds were debited from the customer's account but the wallet balance was not credited.</li>
                    <li>Notification delivery failures where a direct payment transaction was charged for an alert that TicketRadar failed to send.</li>
                    <li>Fraudulent or unauthorized payment activity reported within 48 hours of occurrence.</li>
                  </ul>
                </li>
                <li>
                  <strong>Processing SLA & Timeline:</strong>
                  <ul className="list-[circle] pl-4 pt-1 space-y-1">
                    <li>Administrative review and initiation: <strong>24 to 48 business hours</strong> from ticket receipt.</li>
                    <li>Bank / Gateway credit settlement: Once initiated, refunds reflect back in the original payment method (Bank Account, Credit/Debit Card, or UPI handle) within <strong>5 to 7 business days</strong>, governed by your financial institution's settlement schedule.</li>
                  </ul>
                </li>
                <li>
                  <strong>Source-Account Reversal Only:</strong> In compliance with Reserve Bank of India (RBI) regulations and anti-money laundering (AML) directives, gateway refunds can only be processed back to the exact payment method and account from which the payment originated. We cannot remit gateway refunds to alternative bank accounts, different UPI IDs, or cash.
                </li>
              </ul>
            </div>
          </section>

          <section className="space-y-3">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-rose-400" />
              7. Cinema Availability & Best-Effort Disclaimer
            </h3>
            <p className="text-muted-foreground">
              TicketRadar is an independent showtime tracking utility and is not affiliated with BookMyShow, Bigtree Entertainment Pvt. Ltd., or cinema multiplex chains. All tracking operations are provided on a best-effort basis:
            </p>
            <ul className="list-disc pl-5 space-y-1.5 text-xs text-muted-foreground">
              <li>
                <strong>No Booking Guarantee:</strong> TicketRadar alerts users when tickets become available. We do not hold, reserve, or purchase tickets on your behalf. Rapid sell-outs on cinema platforms do not constitute a service defect.
              </li>
              <li>
                <strong>Delayed Cinema Openings:</strong> If cinema operators do not open ticket sales for your chosen movie or date, you are never charged for tracking. Only active alerts that execute upon tickets opening incur fees.
              </li>
            </ul>
          </section>

          <section className="space-y-3">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <HelpCircle className="h-4 w-4 text-rose-400" />
              8. Contact Us & Dispute Resolution
            </h3>
            <p className="text-muted-foreground">
              If you experience any billing discrepancies, duplicate payment debits, or unexpected charge issues, our development team is here to assist you promptly.
            </p>
            <div className="bg-muted/20 border border-border/50 rounded-xl p-4 space-y-3">
              <p className="text-xs text-muted-foreground">
                Please submit a refund dispute request or transaction inquiry via our official project repository:
              </p>
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
                <a
                  href="https://github.com/Ashif4354/TicketRadar/issues"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-semibold transition-colors"
                >
                  <span>Open a Dispute on GitHub Issues</span>
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                When raising a query, please include your <strong>Registered Email</strong>, the <strong>Payment Gateway Order ID</strong> (e.g. Cashfree Order ID), transaction date/time, and a brief description of the issue to expedite the resolution.
              </p>
            </div>
          </section>

          <div className="pt-4 border-t border-border/60 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-muted-foreground">
            <div className="flex items-center gap-3 flex-wrap justify-center sm:justify-start">
              <Link to="/tc" className="text-primary hover:underline font-medium">Terms & Conditions</Link>
              <span className="text-border">•</span>
              <Link to="/pp" className="text-primary hover:underline font-medium">Privacy Policy</Link>
              <span className="text-border">•</span>
              <Link to="/pricing" className="text-primary hover:underline font-medium">Pricing</Link>
            </div>
            <Link to="/" className="text-primary hover:underline font-medium">
              Return to App
            </Link>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
