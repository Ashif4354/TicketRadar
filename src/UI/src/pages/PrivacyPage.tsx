import { Link } from 'react-router-dom';
import { ArrowLeft, ShieldCheck, User, Lock, CreditCard, Phone, Database, Trash2 } from 'lucide-react';
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
              <CardTitle className="text-2xl sm:text-3xl font-extrabold tracking-tight">Privacy Policy (v2.0)</CardTitle>
              <CardDescription className="text-xs text-muted-foreground mt-1">
                Last updated: September 2026 • Multi-Channel Telephony & Payment Data Protection Policy
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0 space-y-8 text-sm leading-relaxed text-foreground/90">
          {/* Section 1 */}
          <section className="space-y-3">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500 inline-block"></span>
              1. Overview & Commitment
            </h3>
            <p className="text-muted-foreground">
              TicketRadar respects your privacy and is strictly committed to data protection. This Privacy Policy details the specific data we collect, including user accounts, phone numbers, explicit consent audit records, and digital payment ledger transactions, how we utilize this information to deliver real-time ticket availability alerts, and your options to manage or delete your data.
            </p>
          </section>

          {/* Section 2 */}
          <section className="space-y-3">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <User className="h-4 w-4 text-emerald-400" />
              2. User Account Data Collected
            </h3>
            <p className="text-muted-foreground">
              When you authenticate with TicketRadar via Google OAuth, we collect limited profile data necessary to establish your account identity and personalize your experience:
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
              <div className="bg-muted/20 border border-border/50 rounded-xl p-3.5 space-y-1">
                <div className="font-semibold text-xs text-foreground flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                  User Name
                </div>
                <p className="text-xs text-muted-foreground">Your display name as provided by Google OAuth.</p>
              </div>
              <div className="bg-muted/20 border border-border/50 rounded-xl p-3.5 space-y-1">
                <div className="font-semibold text-xs text-foreground flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                  User Email Address
                </div>
                <p className="text-xs text-muted-foreground">Your primary Google account email used for authentication and alert delivery.</p>
              </div>
              <div className="bg-muted/20 border border-border/50 rounded-xl p-3.5 space-y-1">
                <div className="font-semibold text-xs text-foreground flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                  Profile Photo URL
                </div>
                <p className="text-xs text-muted-foreground">URL to your Google avatar picture used for UI avatar display.</p>
              </div>
            </div>
          </section>

          {/* Section 3 */}
          <section className="space-y-3">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <Phone className="h-4 w-4 text-emerald-400" />
              3. Telephony, Phone Numbers & Consent Records
            </h3>
            <div className="text-muted-foreground space-y-2">
              <p>
                When you configure SMS, WhatsApp, or Automated Phone Call alerts:
              </p>
              <ul className="list-disc pl-5 space-y-1 text-xs">
                <li><strong>Indian Phone Numbers:</strong> We collect and normalize your phone number under the E.164 standard (+91). Phone numbers are stored in encrypted format and redacted in administrative logs (e.g. `+91 98*** **210`).</li>
                <li><strong>Consent Logging:</strong> In compliance with TRAI and telecom guidelines, we record immutable consent timestamps and IP metadata for opt-in and opt-out actions in our `notification_consents` collection.</li>
                <li><strong>Delivery Telemetry:</strong> Transmission to carrier networks is brokered securely via Twilio Inc. Calls and messages contain strictly ticket availability information. We never record your personal voice or conversation.</li>
              </ul>
            </div>
          </section>

          {/* Section 4 */}
          <section className="space-y-3">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-emerald-400" />
              4. Payment & Financial Data Safeguards
            </h3>
            <div className="text-muted-foreground space-y-2">
              <p>
                TicketRadar does <strong>NOT collect, store, or process raw payment instrument details</strong> such as credit/debit card numbers, CVVs, or UPI PINs.
              </p>
              <ul className="list-disc pl-5 space-y-1 text-xs">
                <li>All payment checkouts and card transactions are handled directly by <strong>Cashfree Payments India Pvt. Ltd.</strong>, a PCI-DSS compliant, RBI-authorized payment aggregator.</li>
                <li>TicketRadar only stores payment references (gateway order ID, payment transaction ID, timestamp, and amount in paise) to credit your digital wallet or verify job payments.</li>
                <li>Internal wallet balances and transactions are tracked via an immutable append-only ledger in our database.</li>
              </ul>
            </div>
          </section>

          {/* Section 5 */}
          <section className="space-y-3">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <Lock className="h-4 w-4 text-emerald-400" />
              5. How We Use Your Information & Zero Advertising
            </h3>
            <div className="text-muted-foreground space-y-2">
              <p>Your data is used strictly for the following operational purposes:</p>
              <ul className="list-disc pl-5 space-y-1 text-xs">
                <li>To execute automated availability checks against public cinema listings according to your task parameters.</li>
                <li>To transmit notifications to your configured channels (Email, Discord, SMS, WhatsApp, Phone Call).</li>
                <li>To maintain your wallet transaction ledger and process automated refund rollbacks for cancelled tasks or delivery failures.</li>
              </ul>
              <p className="pt-2">
                <strong>We NEVER sell, rent, trade, or monetize your personal information or phone numbers.</strong> We do not serve third-party ads, nor do we share your data with marketing or analytics data brokers.
              </p>
            </div>
          </section>

          {/* Section 6 */}
          <section className="space-y-3">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <Database className="h-4 w-4 text-emerald-400" />
              6. Data Storage & Security Safeguards
            </h3>
            <p className="text-muted-foreground">
              All stored user profiles, wallet records, and task configurations are secured using Google Cloud Firestore infrastructure with robust security rules and role-based access control. All communication between your client and our API is encrypted via HTTPS/TLS 1.3.
            </p>
          </section>

          {/* Section 7 */}
          <section className="space-y-3">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <Trash2 className="h-4 w-4 text-emerald-400" />
              7. Your Rights & Data Deletion
            </h3>
            <p className="text-muted-foreground">
              You maintain full control over your personal data:
            </p>
            <ul className="list-disc pl-5 space-y-1 text-xs text-muted-foreground">
              <li><strong>Revoking Consents:</strong> You can opt-out of SMS, WhatsApp, or Phone Call notifications at any time directly in your Profile.</li>
              <li><strong>Task & Phone Deletion:</strong> You can remove or update your phone number, or delete monitoring jobs from your dashboard at any time.</li>
              <li><strong>Full Account Deletion:</strong> You can request complete account deletion and purge of all associated records by contacting project maintainers.</li>
            </ul>
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
