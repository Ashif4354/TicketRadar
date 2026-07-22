import React from 'react';
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
              <CardTitle className="text-2xl sm:text-3xl font-extrabold tracking-tight">Terms & Conditions</CardTitle>
              <CardDescription className="text-xs text-muted-foreground mt-1">
                Last updated: July 2026 • General Terms of Service for TicketRadar
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
              By accessing, browsing, or using TicketRadar ("the Service"), you acknowledge that you have read, understood, and agree to be bound by these Terms and Conditions. If you do not agree to these terms, please do not use the platform.
            </p>
          </section>

          <section className="space-y-2">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-primary inline-block"></span>
              2. Description of Service
            </h3>
            <p className="text-muted-foreground">
              TicketRadar is an automated alert monitoring tool designed to track showtime releases and ticket availability on BookMyShow. TicketRadar sends real-time notifications via email, webhooks, or messaging integrations when showtimes match user criteria. TicketRadar is strictly a monitoring utility and does not directly sell, reserve, or issue tickets.
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
              4. Best-Effort Service & Availability
            </h3>
            <p className="text-muted-foreground">
              All alert checks and notifications are provided on a best-effort basis. While TicketRadar strives to maintain continuous uptime and timely delivery, we do not warrant or guarantee that notifications will be instantaneous, uninterrupted, or error-free. Ticket availability and seat inventory remain subject to public demand and third-party platform conditions.
            </p>
          </section>

          <section className="space-y-2">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-primary inline-block"></span>
              5. User Responsibilities & Acceptable Use
            </h3>
            <p className="text-muted-foreground">
              You agree to use TicketRadar solely for lawful, personal tracking purposes. You must not attempt to circumvent API security mechanisms, overload server infrastructure, reverse-engineer backend services, or use automated scripts to abuse the system.
            </p>
          </section>

          <section className="space-y-2">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-primary inline-block"></span>
              6. Limitation of Liability
            </h3>
            <p className="text-muted-foreground">
              To the fullest extent permitted by applicable law, TicketRadar and its maintainers shall not be liable for any direct, indirect, incidental, special, or consequential damages resulting from missed movie shows, sold-out tickets, notification delays, or third-party service outages.
            </p>
          </section>

          <section className="space-y-2">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-primary inline-block"></span>
              7. Updates to Terms
            </h3>
            <p className="text-muted-foreground">
              We reserve the right to revise or modify these Terms & Conditions at any time. Continued use of TicketRadar following any posted modifications constitutes your binding acceptance of the updated terms.
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
