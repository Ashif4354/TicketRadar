import { Link } from 'react-router-dom';
import { ArrowLeft, ShieldCheck, User, ListCheck, Lock, Server, Database, Trash2 } from 'lucide-react';
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
                Last updated: July 2026 • Detailed breakdown of data collected, used, and stored by TicketRadar
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0 space-y-8 text-sm leading-relaxed text-foreground/90">
          {/* Section 1 */}
          <section className="space-y-3">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500 inline-block"></span>
              1. Overview
            </h3>
            <p className="text-muted-foreground">
              TicketRadar respects your privacy and is committed to transparency. This Privacy Policy details the specific data we collect, including your user profile details and full task monitoring configurations, how we utilize this information to deliver real-time ticket availability alerts, and your options to manage or delete your data.
            </p>
          </section>

          {/* Section 2 */}
          <section className="space-y-3">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <User className="h-4 w-4 text-emerald-400" />
              2. User Account Data Collected
            </h3>
            <p className="text-muted-foreground">
              When you authenticate with TicketRadar via Google OAuth, we collect limited profile data necessary to establish your account identity, authorize dashboard access, and personalize your experience:
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
                <p className="text-xs text-muted-foreground">Your primary Google account email used for login and alert delivery.</p>
              </div>
              <div className="bg-muted/20 border border-border/50 rounded-xl p-3.5 space-y-1">
                <div className="font-semibold text-xs text-foreground flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                  Profile Photo URL
                </div>
                <p className="text-xs text-muted-foreground">URL to your Google avatar picture used for UI avatar display.</p>
              </div>
            </div>
            <p className="text-xs text-muted-foreground pt-1">
              <em>Note: We also store a unique internal user identifier (Firebase Auth UID) and authorization claims (such as admin or user status) linked to your account.</em>
            </p>
          </section>

          {/* Section 3 */}
          <section className="space-y-3">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <ListCheck className="h-4 w-4 text-emerald-400" />
              3. Task & Monitoring Details Collected
            </h3>
            <p className="text-muted-foreground">
              When you set up or run ticket monitoring alerts on TicketRadar, we store and process comprehensive task configuration and status details:
            </p>
            <div className="bg-muted/20 border border-border/50 rounded-xl p-4 space-y-3">
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs text-muted-foreground">
                <li className="flex items-start gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 mt-1.5 shrink-0"></span>
                  <span><strong>Monitored URL:</strong> Target event or movie booking link (e.g., BookMyShow URL).</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 mt-1.5 shrink-0"></span>
                  <span><strong>Movie / Event Title:</strong> Name of the movie or show selected for monitoring.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 mt-1.5 shrink-0"></span>
                  <span><strong>Target Show Date(s):</strong> Selected dates (`date_str`) for ticket availability checks.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 mt-1.5 shrink-0"></span>
                  <span><strong>Selected Theatres:</strong> List of specific cinema locations or venues configured for alerts.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 mt-1.5 shrink-0"></span>
                  <span><strong>Service Provider:</strong> The ticketing provider platform monitored (e.g., BookMyShow).</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 mt-1.5 shrink-0"></span>
                  <span><strong>Notification Medium:</strong> Your chosen alert delivery method (Email or Discord Webhook).</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 mt-1.5 shrink-0"></span>
                  <span><strong>Notification Destination:</strong> Configured recipient email address or Discord webhook endpoint URL.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 mt-1.5 shrink-0"></span>
                  <span><strong>Polling Interval:</strong> Configured check frequency in seconds (minimum 1 minute).</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 mt-1.5 shrink-0"></span>
                  <span><strong>Task Status & Timestamps:</strong> Creation time, active/paused status, and last checked timestamp.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 mt-1.5 shrink-0"></span>
                  <span><strong>Execution & Audit Logs:</strong> Outcome of the latest check (e.g., "Available", "Not Found", or error diagnostic details).</span>
                </li>
              </ul>
            </div>
          </section>

          {/* Section 4 */}
          <section className="space-y-3">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <Server className="h-4 w-4 text-emerald-400" />
              4. System Security & Operational Data
            </h3>
            <p className="text-muted-foreground">
              To guarantee service stability and protect against unauthorized automated requests, we record essential diagnostic data:
            </p>
            <ul className="list-disc pl-5 space-y-1 text-muted-foreground text-xs">
              <li><strong>App Check & reCAPTCHA Enterprise Tokens:</strong> Verification tokens to validate request authenticity and prevent abuse.</li>
              <li><strong>Security & Network Headers:</strong> Technical logs including IP security headers and request origins during authentication or task dispatch.</li>
            </ul>
          </section>

          {/* Section 5 */}
          <section className="space-y-3">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <Lock className="h-4 w-4 text-emerald-400" />
              5. How We Use Your Information & Zero Third-Party Selling
            </h3>
            <div className="text-muted-foreground space-y-2">
              <p>Your data is used strictly for the following functional purposes:</p>
              <ul className="list-disc pl-5 space-y-1 text-xs">
                <li>To execute scheduled automated ticket availability checks on public cinema listings according to your task parameters.</li>
                <li>To send instant alerts to your designated email or Discord webhook when tickets become available.</li>
                <li>To display your task list, status metrics, and check logs on your personal dashboard.</li>
              </ul>
              <p className="pt-2">
                <strong>We NEVER sell, rent, trade, or monetize your personal information or task data.</strong> We do not use your data for advertising, marketing campaigns, tracking, or profiling across third-party websites.
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
              All stored user profiles and task configurations are secured using Google Firebase infrastructure with role-based access rules. Sensitive operational tokens and credentials are protected with industry-standard encryption standards. Public scraping routines inspect publicly accessible theatre web pages without exposing your identity.
            </p>
          </section>

          {/* Section 7 */}
          <section className="space-y-3">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <Trash2 className="h-4 w-4 text-emerald-400" />
              7. Your Control & Data Deletion
            </h3>
            <p className="text-muted-foreground">
              You maintain full ownership and control of your data on TicketRadar:
            </p>
            <ul className="list-disc pl-5 space-y-1 text-xs text-muted-foreground">
              <li><strong>Task Management:</strong> You can pause, edit, or permanently delete individual monitoring tasks directly from your dashboard at any time.</li>
              <li><strong>Account & Data Purge:</strong> Deleting a task immediately stops all background checks and removes the task configuration and execution history. You can request complete account data deletion by contacting project maintainers via our repository.</li>
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

