# src/Backend/lib/services/notification/templates/email.py

import html
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


class EmailTemplates:
    """
    Centralized email template catalog for TicketRadar.
    Provides get_template function returning subject, text_body, and html_body.
    Can be inherited by strategies or invoked directly as a factory.
    """

    @classmethod
    def get_template(cls, template_name: str, **context: Any) -> Dict[str, str]:
        """
        Retrieves and renders an email template by name with provided context parameters.

        Args:
            template_name: The identifier of the template.
            **context: Context variables required by the specific template.

        Returns:
            Dict with 'subject', 'text_body', and 'html_body' keys.
        """
        norm_name = template_name.strip().lower().replace("-", "_")

        renderers = {
            "booking_alert": cls._render_booking_alert,
            "signup": cls._render_signup,
            "welcome": cls._render_signup,
            "payment_success": cls._render_payment_success,
            "payment_failed": cls._render_payment_failed,
            "call_unanswered": cls._render_call_unanswered,
            "call_notified_unanswered": cls._render_call_unanswered,
            "call_3x_unanswered": cls._render_call_unanswered,
            "call_success": cls._render_call_success,
            "call_notified_success": cls._render_call_success,
            "wallet_topup_success": cls._render_wallet_topup_success,
            "wallet_topup_failed": cls._render_wallet_topup_failed,
            "wallet_transaction": cls._render_wallet_transaction,
            "wallet_debit": lambda **k: cls._render_wallet_transaction(direction="DEBIT", **k),
            "wallet_credit": lambda **k: cls._render_wallet_transaction(direction="CREDIT", **k),
            "refund": cls._render_refund,
            "admin_pricing_changed": cls._render_admin_pricing_changed,
            "job_created": cls._render_job_created,
            "job_cancelled": cls._render_job_cancelled,
            "notification_sent": cls._render_notification_sent,
            "notification_failed": cls._render_notification_failed,
            "access_granted": cls._render_access_granted,
        }

        renderer = renderers.get(norm_name)
        if not renderer:
            raise KeyError(f"Unknown email template '{template_name}'. Available: {list(renderers.keys())}")

        res = renderer(**context)
        # Aliases for convenience
        res["text"] = res["text_body"]
        res["html"] = res["html_body"]
        return res

    @staticmethod
    def _base_html(title: str, subtitle: str, body_html: str, header_gradient: str = "linear-gradient(135deg, #ec4899, #ef4444)") -> str:
        return f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
  </head>
  <body style="margin: 0; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0e1117; color: #f3f4f6;">
    <div style="max-width: 620px; margin: 0 auto; background-color: #1a1f2c; border: 1px solid #2d3748; border-radius: 14px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);">
      <div style="background: {header_gradient}; padding: 24px 20px; text-align: center;">
        <h1 style="margin: 0; color: #ffffff; font-size: 22px; font-weight: 800; letter-spacing: -0.02em;">{html.escape(title)}</h1>
        {f'<p style="margin: 6px 0 0 0; color: rgba(255, 255, 255, 0.9); font-size: 14px; font-weight: 500;">{html.escape(subtitle)}</p>' if subtitle else ''}
      </div>
      <div style="padding: 28px 24px; line-height: 1.6; font-size: 14px; color: #d1d5db;">
        {body_html}
      </div>
      <div style="background-color: #111520; padding: 16px; text-align: center; border-top: 1px solid #232a3b; font-size: 11px; color: #9ca3af;">
        <p style="margin: 0 0 4px 0; font-weight: 600; color: #d1d5db;">TicketRadar • Real-time Cinema Availability Alerts</p>
        <p style="margin: 0;">This is an automated system notification. Please do not reply directly to this message.</p>
      </div>
    </div>
  </body>
</html>"""

    @classmethod
    def _render_invoice_html(
        cls,
        doc_title: str,
        status_label: str,
        status_color: str,
        status_bg: str,
        status_border: str,
        accent_gradient: str,
        invoice_id: str,
        order_id: str,
        payment_id: str,
        payment_method: str,
        customer_name: str,
        customer_email: str,
        customer_phone: str,
        customer_id: str,
        issue_date: str,
        items: List[Dict[str, Any]],
        subtotal_str: str,
        tax_str: Optional[str],
        tax_label: str,
        total_label: str,
        grand_total_str: str,
        grand_total_color: str = "#0f172a",
        wallet_ledger: Optional[Dict[str, Any]] = None,
        terms_notes: Optional[List[str]] = None,
    ) -> str:
        # Build line items
        items_rows_html = ""
        for idx, itm in enumerate(items):
            bg = "#ffffff" if idx % 2 == 0 else "#f8fafc"
            desc = itm.get("desc", "")
            qty = html.escape(str(itm.get("qty", "1")))
            rate = html.escape(str(itm.get("rate", "")))
            amt = html.escape(str(itm.get("amount", "")))
            items_rows_html += f"""
            <tr style="background-color: {bg};">
              <td style="padding: 12px 14px; border-bottom: 1px solid #e2e8f0; color: #1e293b; line-height: 1.5;">{desc}</td>
              <td align="center" style="padding: 12px 14px; border-bottom: 1px solid #e2e8f0; color: #475569;">{qty}</td>
              <td align="right" style="padding: 12px 14px; border-bottom: 1px solid #e2e8f0; color: #475569;">{rate}</td>
              <td align="right" style="padding: 12px 14px; border-bottom: 1px solid #e2e8f0; font-weight: 700; color: #0f172a;">{amt}</td>
            </tr>"""

        # Build wallet ledger box if applicable
        wallet_ledger_html = ""
        if wallet_ledger:
            prev_b = html.escape(wallet_ledger.get("prev_bal", "₹0.00"))
            act_lbl = html.escape(wallet_ledger.get("action_label", "Credit Amount:"))
            imp_amt = html.escape(wallet_ledger.get("impact_amt", "+₹0.00"))
            imp_clr = wallet_ledger.get("impact_color", "#059669")
            new_b = html.escape(wallet_ledger.get("new_bal", "₹0.00"))
            wallet_ledger_html = f"""
            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px;">
              <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #64748b; margin-bottom: 8px;">
                💳 TicketRadar Wallet Impact
              </div>
              <table width="100%" cellpadding="0" cellspacing="0" border="0" style="font-size: 12px; line-height: 1.8;">
                <tr>
                  <td style="color: #64748b;">Previous Balance:</td>
                  <td align="right" style="color: #475569; font-weight: 500;">{prev_b}</td>
                </tr>
                <tr>
                  <td style="color: #64748b;">{act_lbl}</td>
                  <td align="right" style="color: {imp_clr}; font-weight: 700;">{imp_amt}</td>
                </tr>
                <tr style="border-top: 1px dashed #cbd5e1;">
                  <td style="color: #0f172a; font-weight: 700; padding-top: 4px;">Updated Balance:</td>
                  <td align="right" style="color: #059669; font-weight: 800; font-size: 13px; padding-top: 4px;">{new_b}</td>
                </tr>
              </table>
            </div>"""

        tax_row_html = ""
        if tax_str:
            tax_row_html = f"""
            <tr>
              <td style="color: #64748b;">{html.escape(tax_label)}:</td>
              <td align="right" style="color: #64748b;">{html.escape(tax_str)}</td>
            </tr>"""

        notes_list = terms_notes or [
            "This is an automated system tax invoice / receipt; no signature is required.",
            "Wallet credits are immediately available for automated ticket monitoring & alert services.",
            "Unspent wallet balances are subject to the TicketRadar Refund Policy."
        ]
        notes_html = "".join(f"• {html.escape(n)}<br>" for n in notes_list)

        phone_line = f'<div style="color: #64748b; margin-top: 2px; font-size: 12px;">{html.escape(customer_phone)}</div>' if customer_phone else ''
        email_line = f'<div style="color: #475569; margin-top: 2px;">{html.escape(customer_email)}</div>' if customer_email else ''
        uid_line = f'<div style="color: #94a3b8; margin-top: 4px; font-size: 11px;">Account ID: <span style="font-family: monospace; color: #64748b;">{html.escape(customer_id)}</span></div>' if customer_id else ''

        return f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(doc_title)} - TicketRadar</title>
    <style>
      @media print {{
        body {{ background-color: #ffffff !important; padding: 0 !important; margin: 0 !important; }}
        .no-print {{ display: none !important; }}
        .invoice-card {{ border: none !important; box-shadow: none !important; max-width: 100% !important; border-radius: 0 !important; }}
      }}
    </style>
  </head>
  <body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; color: #1e293b;">
    <div style="width: 100%; padding: 40px 15px; box-sizing: border-box; background-color: #f1f5f9;">
      <table align="center" cellpadding="0" cellspacing="0" border="0" style="max-width: 660px; width: 100%; margin: 0 auto;">
        <tr>
          <td>
            <div class="invoice-card" style="background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.08), 0 4px 6px -2px rgba(15, 23, 42, 0.04); overflow: hidden;">
              
              <!-- TOP ACCENT BAR -->
              <div style="height: 6px; background: {accent_gradient};"></div>

              <div style="padding: 36px 36px 28px 36px;">

                <!-- HEADER: BRAND & INVOICE META -->
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 28px;">
                  <tr>
                    <td valign="top" style="vertical-align: top;">
                      <div style="display: flex; align-items: center;">
                        <span style="font-size: 22px; font-weight: 800; letter-spacing: -0.03em; color: #0f172a;">Ticket<span style="color: #2563eb;">Radar</span></span>
                      </div>
                      <p style="margin: 4px 0 0 0; font-size: 12px; color: #64748b; line-height: 1.4;">
                        Automated Cinema Tracker & Alerts<br>
                        darkglance.developer@gmail.com • <a href="https://ticketradar.darkglance.in" target="_blank" style="color: #2563eb; text-decoration: none;">ticketradar.darkglance.in</a>
                      </p>
                    </td>
                    <td valign="top" align="right" style="vertical-align: top; text-align: right;">
                      <span style="display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; background-color: {status_bg}; color: {status_color}; border: 1px solid {status_border};">
                        {html.escape(status_label)}
                      </span>
                      <h2 style="margin: 8px 0 2px 0; font-size: 18px; font-weight: 800; color: #0f172a; letter-spacing: -0.02em;">{html.escape(doc_title)}</h2>
                      <p style="margin: 0; font-size: 12px; font-family: 'SFMono-Regular', Consolas, Menlo, monospace; color: #64748b; font-weight: 600;">
                        {html.escape(invoice_id)}
                      </p>
                    </td>
                  </tr>
                </table>

                <!-- DIVIDER -->
                <div style="height: 1px; background-color: #f1f5f9; margin-bottom: 24px;"></div>

                <!-- BILLED TO / DETAILS GRID -->
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 28px; font-size: 13px;">
                  <tr>
                    <td width="50%" valign="top" style="vertical-align: top; padding-right: 15px;">
                      <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #94a3b8; margin-bottom: 6px;">Customer Details</div>
                      <div style="font-weight: 700; color: #0f172a; font-size: 14px;">{html.escape(customer_name or "Valued Customer")}</div>
                      {email_line}
                      {phone_line}
                      {uid_line}
                    </td>
                    <td width="50%" valign="top" style="vertical-align: top; padding-left: 15px; border-left: 1px solid #f1f5f9;">
                      <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #94a3b8; margin-bottom: 6px;">Transaction Details</div>
                      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="font-size: 12px; line-height: 1.8;">
                        <tr>
                          <td style="color: #64748b;">Issue Date:</td>
                          <td align="right" style="color: #0f172a; font-weight: 600;">{html.escape(issue_date)}</td>
                        </tr>
                        <tr>
                          <td style="color: #64748b;">Order / Job ID:</td>
                          <td align="right" style="font-family: monospace; color: #0f172a; font-weight: 600;">{html.escape(order_id)}</td>
                        </tr>
                        <tr>
                          <td style="color: #64748b;">Payment Ref:</td>
                          <td align="right" style="font-family: monospace; color: #0f172a; font-weight: 600;">{html.escape(payment_id)}</td>
                        </tr>
                        <tr>
                          <td style="color: #64748b;">Payment Method:</td>
                          <td align="right" style="color: #0f172a; font-weight: 600;">{html.escape(payment_method)}</td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>

                <!-- LINE ITEMS TABLE -->
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: separate; border-spacing: 0; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; margin-bottom: 24px; font-size: 13px;">
                  <thead>
                    <tr style="background-color: #f8fafc; color: #475569; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;">
                      <th align="left" style="padding: 10px 14px; font-weight: 700; border-bottom: 1px solid #e2e8f0;">Description</th>
                      <th align="center" style="padding: 10px 14px; font-weight: 700; border-bottom: 1px solid #e2e8f0; width: 60px;">Qty</th>
                      <th align="right" style="padding: 10px 14px; font-weight: 700; border-bottom: 1px solid #e2e8f0; width: 90px;">Rate</th>
                      <th align="right" style="padding: 10px 14px; font-weight: 700; border-bottom: 1px solid #e2e8f0; width: 100px;">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items_rows_html}
                  </tbody>
                </table>

                <!-- SUMMARY & TOTALS -->
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 28px;">
                  <tr>
                    <td width="55%" valign="top" style="vertical-align: top; padding-right: 15px;">
                      {wallet_ledger_html}
                    </td>
                    <td width="45%" valign="top" style="vertical-align: top;">
                      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="font-size: 13px; line-height: 2;">
                        <tr>
                          <td style="color: #64748b;">Subtotal:</td>
                          <td align="right" style="color: #1e293b; font-weight: 600;">{html.escape(subtotal_str)}</td>
                        </tr>
                        {tax_row_html}
                        <tr>
                          <td colspan="2" style="padding-top: 6px; padding-bottom: 6px;">
                            <div style="height: 2px; background-color: #0f172a;"></div>
                          </td>
                        </tr>
                        <tr style="font-size: 15px;">
                          <td style="color: #0f172a; font-weight: 800;">{html.escape(total_label)}:</td>
                          <td align="right" style="color: {grand_total_color}; font-weight: 800; font-size: 18px;">{html.escape(grand_total_str)}</td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>

                <!-- ACTION BAR (Print Button) -->
                <div class="no-print" style="text-align: center; margin: 30px 0 10px 0;">
                  <table align="center" cellpadding="0" cellspacing="0" border="0">
                    <tr>
                      <td align="center" style="border-radius: 8px; background: #2563eb;">
                        <a href="#" onclick="window.print(); return false;" style="display: inline-block; padding: 12px 28px; font-size: 13px; font-weight: 700; color: #ffffff; text-decoration: none; border-radius: 8px;">
                          🖨️ Download / Print Receipt (PDF)
                        </a>
                      </td>
                    </tr>
                  </table>
                  <p style="margin: 10px 0 0 0; font-size: 11px; color: #94a3b8;">
                    Manage alerts & view transaction history on your <a href="https://ticketradar.darkglance.in/dashboard" target="_blank" style="color: #2563eb; text-decoration: underline;">TicketRadar Dashboard</a>.
                  </p>
                </div>

                <!-- DIVIDER -->
                <div style="height: 1px; background-color: #f1f5f9; margin: 24px 0;"></div>

                <!-- FOOTER -->
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="font-size: 11px; color: #94a3b8; line-height: 1.5;">
                  <tr>
                    <td>
                      <p style="margin: 0 0 4px 0; font-weight: 600; color: #64748b;">Terms & Information:</p>
                      <p style="margin: 0 0 4px 0;">
                        {notes_html}
                      </p>
                      <p style="margin: 8px 0 0 0; color: #64748b;">
                        TicketRadar • <a href="https://ticketradar.darkglance.in" target="_blank" style="color: #64748b; text-decoration: none;">ticketradar.darkglance.in</a>
                      </p>
                    </td>
                  </tr>
                </table>

              </div>

              <!-- BOTTOM BAR -->
              <div style="background-color: #0f172a; padding: 14px 36px; text-align: center; font-size: 11px; color: #94a3b8;">
                Questions regarding this transaction? Reach out to <a href="mailto:darkglance.developer@gmail.com" style="color: #38bdf8; text-decoration: none;">darkglance.developer@gmail.com</a>
              </div>

            </div>
          </td>
        </tr>
      </table>
    </div>
  </body>
</html>"""

    # 1. Booking Alert Template
    @classmethod
    def _render_booking_alert(
        cls,
        movie_name: str = "Movie",
        date_str: str = "",
        available_theatres: Optional[List[str]] = None,
        unavailable_theatres: Optional[List[str]] = None,
        url: str = "",
        language: str = "",
        format_name: str = "",
        subject: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, str]:
        available = available_theatres or []
        unavailable = unavailable_theatres or []

        fmt_details = " | ".join(filter(None, [language, format_name]))
        fmt_sub = f" ({fmt_details})" if fmt_details else ""

        escaped_movie = html.escape(movie_name)
        escaped_date = html.escape(date_str)
        escaped_lang = html.escape(language)
        escaped_fmt = html.escape(format_name)
        fmt_details_html = " | ".join(filter(None, [escaped_lang, escaped_fmt]))
        fmt_sub_html = f" ({fmt_details_html})" if fmt_details_html else ""

        rows_html = ""
        rows_text = ""
        for t in available:
            rows_html += f"""
            <tr style="background-color: rgba(16, 185, 129, 0.08);">
              <td style="padding: 10px 14px; border: 1px solid #374151; font-weight: 600; color: #f9fafb;">{html.escape(t)}</td>
              <td style="padding: 10px 14px; border: 1px solid #374151; text-align: center; color: #34d399; font-weight: 700;">🟢 Available</td>
            </tr>"""
            rows_text += f"{t: <40} | AVAILABLE\n"

        for t in unavailable:
            rows_html += f"""
            <tr style="background-color: rgba(239, 68, 68, 0.04);">
              <td style="padding: 10px 14px; border: 1px solid #374151; color: #9ca3af; text-decoration: line-through;">{html.escape(t)}</td>
              <td style="padding: 10px 14px; border: 1px solid #374151; text-align: center; color: #f87171;">🔴 Unavailable</td>
            </tr>"""
            rows_text += f"{t: <40} | UNAVAILABLE\n"

        format_badge_html = ""
        if language or format_name:
            parts = []
            if language:
                parts.append(f'<span style="background: rgba(244, 114, 182, 0.15); color: #f472b6; border: 1px solid rgba(244, 114, 182, 0.3); padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; margin-right: 6px;">🌐 {escaped_lang}</span>')
            if format_name:
                parts.append(f'<span style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700;">🎬 {escaped_fmt}</span>')
            format_badge_html = f'<div style="margin-top: 8px;">{"".join(parts)}</div>'

        resume_html = ""
        resume_text = ""
        if unavailable:
            resume_text = "\nNote: Monitoring has paused for this alert. If you still want to monitor for the remaining unavailable theatres, resume your tracker from the dashboard.\n"
            resume_html = """
            <div style="margin-top: 16px; padding: 12px 14px; background-color: rgba(245, 158, 11, 0.1); border-left: 4px solid #f59e0b; border-radius: 6px; font-size: 12px; color: #fbbf24;">
              ℹ️ <strong>Note:</strong> Monitoring has paused for this alert. Resume from dashboard to continue tracking unavailable theatres.
            </div>"""

        body_html = f"""
        <p style="margin-top: 0; font-size: 15px;">
          Booking is now open for <strong>{escaped_movie}</strong>{fmt_sub_html} on <strong>{escaped_date}</strong>!
        </p>
        <h3 style="color: #ffffff; margin-top: 20px; margin-bottom: 10px; font-size: 15px;">🏢 Theatre Availability</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 16px; font-size: 13px;">
          <thead>
            <tr style="background-color: #111827; color: #ffffff;">
              <th style="padding: 10px 14px; border: 1px solid #374151; text-align: left;">Theatre Name</th>
              <th style="padding: 10px 14px; border: 1px solid #374151; text-align: center; width: 130px;">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows_html}
          </tbody>
        </table>
        {resume_html}
        <div style="margin-top: 24px; text-align: center;">
          <a href="{url}" target="_blank" style="background: linear-gradient(135deg, #ec4899, #ef4444); color: white; padding: 12px 28px; text-decoration: none; border-radius: 8px; font-weight: 700; display: inline-block; box-shadow: 0 4px 14px rgba(236, 72, 153, 0.35);">Book Tickets Now 🍿</a>
        </div>
        """

        full_html = cls._base_html(
            title=f"🍿 Booking Open: {movie_name}",
            subtitle=f"{date_str}{fmt_sub}",
            body_html=body_html,
            header_gradient="linear-gradient(135deg, #ec4899, #ef4444)"
        )

        sub = subject or f"🍿 TicketRadar: Booking Open for {movie_name} ({date_str})!"
        text_body = (
            f"TicketRadar: Booking Open!\n\n"
            f"Movie: {movie_name}{fmt_sub}\n"
            f"Date: {date_str}\n"
            f"Link: {url}\n\n"
            f"Theatre Availability:\n"
            f"{'-'*55}\n"
            f"{'Theatre Name': <40} | {'Status': <12}\n"
            f"{'-'*55}\n"
            f"{rows_text}"
            f"{'-'*55}\n"
            f"{resume_text}\n"
            f"Book tickets immediately: {url}"
        )

        return {"subject": sub, "text_body": text_body, "html_body": full_html}

    # 2. Signup / Welcome Template
    @classmethod
    def _render_signup(
        cls,
        user_name: str = "",
        email: str = "",
        app_url: str = "https://ticketradar.local",
        **kwargs: Any
    ) -> Dict[str, str]:
        display_name = kwargs.get("name") or user_name or (email.split("@")[0] if email else "") or "Movie Fan"
        subject = "Welcome to TicketRadar! 🍿 Start Tracking Movie Tickets"

        body_html = f"""
        <p style="margin-top: 0; font-size: 15px;">Hi <strong>{html.escape(display_name)}</strong>,</p>
        <p>Welcome to <strong>TicketRadar</strong>! Your account has been registered successfully.</p>
        <div style="margin: 20px 0; padding: 16px; background-color: rgba(236, 72, 153, 0.08); border-left: 4px solid #ec4899; border-radius: 6px;">
          <h4 style="margin: 0 0 6px 0; color: #f472b6; font-size: 14px;">⚡ Real-time Availability Alerts</h4>
          <p style="margin: 0; font-size: 13px; color: #d1d5db;">Never miss first-day-first-show tickets again. Configure automated trackers and get notified within seconds via WhatsApp, SMS, Voice Call, Email, or Discord.</p>
        </div>
        <h4 style="color: #ffffff; margin-top: 20px; margin-bottom: 10px; font-size: 14px;">Next steps to get started:</h4>
        <ol style="padding-left: 20px; margin: 0 0 20px 0; color: #d1d5db; font-size: 13px; line-height: 1.8;">
          <li>Visit your <strong>Profile</strong> to link your phone number and configure notification channels.</li>
          <li>Top up your wallet balance in rupees for instant alerts.</li>
          <li>Paste any BookMyShow movie link on the dashboard to start tracking!</li>
        </ol>
        <div style="margin-top: 24px; text-align: center;">
          <a href="{app_url}/app" target="_blank" style="background: linear-gradient(135deg, #ec4899, #ef4444); color: white; padding: 12px 28px; text-decoration: none; border-radius: 8px; font-weight: 700; display: inline-block;">Go to TicketRadar Dashboard 🚀</a>
        </div>
        """

        full_html = cls._base_html(
            title="🍿 Welcome to TicketRadar",
            subtitle="Your ticket tracking account is ready",
            body_html=body_html,
            header_gradient="linear-gradient(135deg, #ec4899, #8b5cf6)"
        )

        text_body = (
            f"Hi {display_name},\n\n"
            f"Welcome to TicketRadar! Your account ({email}) is successfully created.\n\n"
            f"Start tracking BookMyShow movie showtimes and get instant alerts via WhatsApp, SMS, Phone Call, Email, or Discord.\n\n"
            f"Access your dashboard: {app_url}/app\n\n"
            f"Happy Watching,\nThe TicketRadar Team"
        )

        return {"subject": subject, "text_body": text_body, "html_body": full_html}

    # 3. Payment Success Template
    @classmethod
    def _render_payment_success(
        cls,
        user_name: str = "User",
        order_id: str = "",
        payment_id: str = "",
        amount_inr: Any = 0.0,
        payment_type: str = "Wallet Top-up",
        timestamp: str = "",
        **kwargs: Any
    ) -> Dict[str, str]:
        amt = _safe_float(amount_inr)
        now_str = timestamp or datetime.now(timezone.utc).strftime("%d %b %Y, %I:%M %p UTC")
        inv_id = kwargs.get("invoice_id") or f"REC-TR-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{abs(hash(order_id or payment_id or str(amt))) % 100000:05d}"
        cust_email = kwargs.get("recipient_email") or kwargs.get("user_email") or kwargs.get("email") or ""
        cust_phone = kwargs.get("phone_number") or kwargs.get("phone") or ""
        cust_uid = kwargs.get("user_id") or kwargs.get("uid") or ""
        method = kwargs.get("payment_method") or kwargs.get("payment_gateway") or "Online Payment"

        items = [
            {
                "desc": f"<strong>{html.escape(payment_type)}</strong><br><span style='color: #64748b; font-size: 11px;'>TicketRadar Service Credits / Transaction</span>",
                "qty": "1",
                "rate": f"₹{amt:.2f}",
                "amount": f"₹{amt:.2f}",
            }
        ]

        full_html = cls._render_invoice_html(
            doc_title="PAYMENT RECEIPT",
            status_label="● PAID",
            status_color="#059669",
            status_bg="#ecfdf5",
            status_border="#a7f3d0",
            accent_gradient="linear-gradient(90deg, #10b981, #06b6d4)",
            invoice_id=inv_id,
            order_id=order_id or "N/A",
            payment_id=payment_id or "N/A",
            payment_method=method,
            customer_name=user_name,
            customer_email=cust_email,
            customer_phone=cust_phone,
            customer_id=cust_uid,
            issue_date=now_str,
            items=items,
            subtotal_str=f"₹{amt:.2f}",
            tax_str=None,
            tax_label="",
            total_label="Total Paid",
            grand_total_str=f"₹{amt:.2f}",
            grand_total_color="#0f172a",
        )

        subject = f"Payment Successful: ₹{amt:.2f} received (Order #{order_id})"
        text_body = (
            f"Payment Successful!\n\n"
            f"Hi {user_name},\n"
            f"We received your payment of ₹{amt:.2f}.\n\n"
            f"Receipt ID: {inv_id}\n"
            f"Order ID: {order_id}\n"
            f"Payment ID: {payment_id or 'N/A'}\n"
            f"Purpose: {payment_type}\n\n"
            f"Thank you for using TicketRadar."
        )

        return {"subject": subject, "text_body": text_body, "html_body": full_html}

    # 4. Payment Failed Template
    @classmethod
    def _render_payment_failed(
        cls,
        user_name: str = "User",
        order_id: str = "",
        amount_inr: Any = 0.0,
        failure_reason: str = "Transaction declined or cancelled.",
        **kwargs: Any
    ) -> Dict[str, str]:
        amt = _safe_float(amount_inr)
        reason_text = kwargs.get("error_reason") or failure_reason
        subject = f"Payment Failed for Order #{order_id}"
        body_html = f"""
        <p style="margin-top: 0; font-size: 15px;">Hi <strong>{html.escape(user_name)}</strong>,</p>
        <p>Unfortunately, your payment attempt for <strong>₹{amt:.2f}</strong> was not successful.</p>
        <div style="margin: 20px 0; padding: 14px 16px; background-color: rgba(239, 68, 68, 0.1); border-left: 4px solid #ef4444; border-radius: 6px; font-size: 13px; color: #f87171;">
          <strong>Failure Reason:</strong> {html.escape(reason_text)}
        </div>
        <p style="font-size: 13px; color: #d1d5db;">No funds have been deducted from your bank account or payment method. You can retry the top-up or job creation from your dashboard at any time.</p>
        """

        full_html = cls._base_html(
            title="❌ Payment Failed",
            subtitle=f"Order #{order_id}",
            body_html=body_html,
            header_gradient="linear-gradient(135deg, #ef4444, #b91c1c)"
        )

        text_body = (
            f"Payment Failed!\n\n"
            f"Hi {user_name},\n"
            f"Your payment of ₹{amount_inr:.2f} (Order #{order_id}) could not be completed.\n"
            f"Reason: {failure_reason}\n\n"
            f"Please try again from your TicketRadar dashboard."
        )

        return {"subject": subject, "text_body": text_body, "html_body": full_html}

    # 5. Call Unanswered (3 Attempts) Template
    @classmethod
    def _render_call_unanswered(
        cls,
        user_name: str = "User",
        phone_number: str = "",
        movie_name: str = "",
        date_str: str = "",
        available_theatres: Optional[List[str]] = None,
        url: str = "",
        attempt_count: int = 3,
        **kwargs: Any
    ) -> Dict[str, str]:
        attempt_count = kwargs.get("attempts") or attempt_count
        cinema = kwargs.get("cinema_name")
        theatres_str = ", ".join(available_theatres or ([cinema] if cinema else ["Monitored Cinemas"]))
        booking_link = url or kwargs.get("booking_url", "")
        subject = f"⚠️ Alert: We called 3 times regarding {movie_name} tickets ({date_str})"

        body_html = f"""
        <p style="margin-top: 0; font-size: 15px;">Hi <strong>{html.escape(user_name)}</strong>,</p>
        <p>We detected that booking has opened for <strong>{html.escape(movie_name)}</strong> on <strong>{html.escape(date_str)}</strong>.</p>
        <div style="margin: 18px 0; padding: 14px 16px; background-color: rgba(245, 158, 11, 0.12); border-left: 4px solid #f59e0b; border-radius: 6px; font-size: 13px; color: #fbbf24; line-height: 1.6;">
          📞 <strong>Automated Call Notice:</strong><br>
          We attempted to call your registered phone number <strong>{html.escape(phone_number)}</strong> a total of <strong>{attempt_count} times</strong>, but the call was not answered or the line was busy.
        </div>
        <table style="width: 100%; border-collapse: collapse; margin: 18px 0; background-color: #111827; border-radius: 8px; font-size: 13px;">
          <tr>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; color: #9ca3af;">Target Number:</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; font-family: monospace; color: #f3f4f6; text-align: right;">{html.escape(phone_number)}</td>
          </tr>
          <tr>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; color: #9ca3af;">Call Attempts:</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; font-weight: 700; color: #fbbf24; text-align: right;">{attempt_count} of 3 (Final)</td>
          </tr>
          <tr>
            <td style="padding: 10px 14px; color: #9ca3af;">Cinemas Available:</td>
            <td style="padding: 10px 14px; color: #34d399; font-weight: 600; text-align: right;">{html.escape(theatres_str)}</td>
          </tr>
        </table>
        <p style="font-size: 13px; color: #d1d5db;">Per our delivery policy, after 3 unanswered attempts, voice calling concludes and this email is dispatched to ensure you don't miss out on tickets.</p>
        <div style="margin-top: 24px; text-align: center;">
          <a href="{booking_link}" target="_blank" style="background: linear-gradient(135deg, #ec4899, #ef4444); color: white; padding: 12px 28px; text-decoration: none; border-radius: 8px; font-weight: 700; display: inline-block;">Book Tickets Right Now 🍿</a>
        </div>
        """

        full_html = cls._base_html(
            title="📞 Call Unanswered — Tickets Open!",
            subtitle=f"Attempted 3 calls to {phone_number}",
            body_html=body_html,
            header_gradient="linear-gradient(135deg, #f59e0b, #ef4444)"
        )

        text_body = (
            f"TicketRadar Alert: We called 3 times but couldn't reach you!\n\n"
            f"Movie: {movie_name}\n"
            f"Date: {date_str}\n"
            f"Number Called: {phone_number}\n"
            f"Attempts: {attempt_count} of 3\n"
            f"Cinemas: {theatres_str}\n\n"
            f"Tickets are open now. Book immediately: {booking_link}"
        )

        return {"subject": subject, "text_body": text_body, "html_body": full_html}

    # 6. Successfully Notified via Call Template
    @classmethod
    def _render_call_success(
        cls,
        user_name: str = "User",
        phone_number: str = "",
        movie_name: str = "",
        date_str: str = "",
        call_duration_seconds: int = 0,
        url: str = "",
        timestamp: str = "",
        **kwargs: Any
    ) -> Dict[str, str]:
        duration_display = kwargs.get("duration") or f"{call_duration_seconds} seconds"
        cinema = kwargs.get("cinema_name")
        subject = f"✅ Voice Call Completed: {movie_name} Tickets Available ({date_str})"
        body_html = f"""
        <p style="margin-top: 0; font-size: 15px;">Hi <strong>{html.escape(user_name)}</strong>,</p>
        <p>Our automated voice call notification for <strong>{html.escape(movie_name)}</strong> was answered successfully.</p>
        <table style="width: 100%; border-collapse: collapse; margin: 18px 0; background-color: #111827; border-radius: 8px; font-size: 13px;">
          <tr>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; color: #9ca3af;">Phone Number Called:</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; font-family: monospace; color: #34d399; font-weight: 600; text-align: right;">{html.escape(phone_number)}</td>
          </tr>
          <tr>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; color: #9ca3af;">Call Status:</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; font-weight: 700; color: #34d399; text-align: right;">Answered ✅</td>
          </tr>
          <tr>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; color: #9ca3af;">Call Duration:</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; color: #d1d5db; text-align: right;">{html.escape(str(duration_display))}</td>
          </tr>
          {f'<tr><td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; color: #9ca3af;">Cinema:</td><td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; color: #f3f4f6; text-align: right;">{html.escape(cinema)}</td></tr>' if cinema else ''}
          <tr>
            <td style="padding: 10px 14px; color: #9ca3af;">Show Date:</td>
            <td style="padding: 10px 14px; color: #f3f4f6; font-weight: 600; text-align: right;">{html.escape(date_str)}</td>
          </tr>
        </table>
        <p style="font-size: 13px; color: #d1d5db;">Please proceed directly to BookMyShow to confirm your seat selection.</p>
        <div style="margin-top: 24px; text-align: center;">
          <a href="{url}" target="_blank" style="background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 12px 28px; text-decoration: none; border-radius: 8px; font-weight: 700; display: inline-block;">Open Booking Link 🎟️</a>
        </div>
        """

        full_html = cls._base_html(
            title="📞 Voice Alert Delivered",
            subtitle=f"{movie_name} • {phone_number}",
            body_html=body_html,
            header_gradient="linear-gradient(135deg, #10b981, #065f46)"
        )

        text_body = (
            f"Voice Alert Delivered!\n\n"
            f"Movie: {movie_name}\n"
            f"Show Date: {date_str}\n"
            f"Target Number: {phone_number}\n"
            f"Duration: {call_duration_seconds}s\n"
            f"Status: Answered\n\n"
            f"Book now: {url}"
        )

        return {"subject": subject, "text_body": text_body, "html_body": full_html}

    # 7. Wallet Topup Success Template
    @classmethod
    def _render_wallet_topup_success(
        cls,
        user_name: str = "User",
        amount_inr: Any = 0.0,
        new_balance_inr: Any = 0.0,
        order_id: str = "",
        **kwargs: Any
    ) -> Dict[str, str]:
        amt = _safe_float(amount_inr)
        bal = _safe_float(kwargs.get("balance_inr") if kwargs.get("balance_inr") is not None else new_balance_inr)
        prev_bal = max(0.0, bal - amt)
        now_str = kwargs.get("timestamp") or datetime.now(timezone.utc).strftime("%d %b %Y, %I:%M %p UTC")
        inv_id = kwargs.get("invoice_id") or f"REC-TR-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{abs(hash(order_id or str(amt))) % 100000:05d}"
        cust_email = kwargs.get("recipient_email") or kwargs.get("user_email") or kwargs.get("email") or ""
        cust_phone = kwargs.get("phone_number") or kwargs.get("phone") or ""
        cust_uid = kwargs.get("user_id") or kwargs.get("uid") or ""

        from lib.utils.config import settings
        gw_name = kwargs.get("gateway_name") or kwargs.get("payment_gateway") or (settings.payment_gateway if settings else None)
        method = f"{gw_name.capitalize()} PG" if gw_name else "Online Payment / UPI"

        items = [
            {
                "desc": "<strong>TicketRadar Wallet Recharge</strong><br><span style='color: #64748b; font-size: 11px;'>Instant wallet credits for real-time cinema ticket alerts & automated calls</span>",
                "qty": "1",
                "rate": f"₹{amt:.2f}",
                "amount": f"₹{amt:.2f}",
            }
        ]

        wallet_ledger = {
            "prev_bal": f"₹{prev_bal:.2f}",
            "action_label": "Amount Credited:",
            "impact_amt": f"+₹{amt:.2f}",
            "impact_color": "#059669",
            "new_bal": f"₹{bal:.2f}",
        }

        full_html = cls._render_invoice_html(
            doc_title="PAYMENT RECEIPT",
            status_label="● PAID & CREDITED",
            status_color="#059669",
            status_bg="#ecfdf5",
            status_border="#a7f3d0",
            accent_gradient="linear-gradient(90deg, #10b981, #06b6d4)",
            invoice_id=inv_id,
            order_id=order_id or "N/A",
            payment_id=kwargs.get("payment_id") or "N/A",
            payment_method=method,
            customer_name=user_name,
            customer_email=cust_email,
            customer_phone=cust_phone,
            customer_id=cust_uid,
            issue_date=now_str,
            items=items,
            subtotal_str=f"₹{amt:.2f}",
            tax_str=None,
            tax_label="",
            total_label="Total Paid",
            grand_total_str=f"₹{amt:.2f}",
            grand_total_color="#0f172a",
            wallet_ledger=wallet_ledger,
        )

        subject = f"Wallet Credited: ₹{amt:.2f} added to your account"
        text_body = (
            f"Wallet Top-up Successful!\n\n"
            f"Hi {user_name},\n"
            f"₹{amt:.2f} has been added to your wallet (Order #{order_id}).\n"
            f"New Wallet Balance: ₹{bal:.2f}\n\n"
            f"Thank you for choosing TicketRadar."
        )

        return {"subject": subject, "text_body": text_body, "html_body": full_html}

    # 8. Wallet Topup Failed Template
    @classmethod
    def _render_wallet_topup_failed(
        cls,
        user_name: str = "User",
        amount_inr: Any = 0.0,
        order_id: str = "",
        reason: str = "Payment gateway declined.",
        **kwargs: Any
    ) -> Dict[str, str]:
        amt = _safe_float(amount_inr)
        subject = f"Wallet Top-up Failed: ₹{amt:.2f} (Order #{order_id})"
        body_html = f"""
        <p style="margin-top: 0; font-size: 15px;">Hi <strong>{html.escape(user_name)}</strong>,</p>
        <p>Your attempt to top up <strong>₹{amt:.2f}</strong> into your TicketRadar wallet could not be completed.</p>
        <div style="margin: 18px 0; padding: 14px 16px; background-color: rgba(239, 68, 68, 0.1); border-left: 4px solid #ef4444; border-radius: 6px; font-size: 13px; color: #f87171;">
          <strong>Error Details:</strong> {html.escape(reason)}
        </div>
        <p style="font-size: 13px; color: #9ca3af;">Order ID: <code style="color: #f3f4f6;">{html.escape(order_id)}</code></p>
        """

        full_html = cls._base_html(
            title="❌ Wallet Top-up Failed",
            subtitle=f"Order #{order_id}",
            body_html=body_html,
            header_gradient="linear-gradient(135deg, #ef4444, #991b1b)"
        )

        text_body = (
            f"Wallet Top-up Failed!\n\n"
            f"Hi {user_name},\n"
            f"Top-up of ₹{amt:.2f} (Order #{order_id}) failed.\n"
            f"Reason: {reason}\n"
        )

        return {"subject": subject, "text_body": text_body, "html_body": full_html}

    # 9. Wallet Transaction (Debit / Credit) Template
    @classmethod
    def _render_wallet_transaction(
        cls,
        user_name: str = "User",
        txn_type: str = "DEBIT",
        direction: str = "DEBIT",
        amount_inr: Any = 0.0,
        new_balance_inr: Any = 0.0,
        description: str = "",
        **kwargs: Any
    ) -> Dict[str, str]:
        amt = _safe_float(amount_inr)
        bal = _safe_float(kwargs.get("balance_inr") if kwargs.get("balance_inr") is not None else new_balance_inr)
        desc = kwargs.get("reason") or description or txn_type
        is_credit = direction.upper() == "CREDIT"
        sign = "+" if is_credit else "-"
        color = "#34d399" if is_credit else "#f87171"
        subject = f"Wallet {direction.capitalize()}: {sign}₹{amt:.2f} ({desc})"

        body_html = f"""
        <p style="margin-top: 0; font-size: 15px;">Hi <strong>{html.escape(user_name)}</strong>,</p>
        <p>A new transaction occurred on your TicketRadar wallet:</p>
        <table style="width: 100%; border-collapse: collapse; margin: 18px 0; background-color: #111827; border-radius: 8px; font-size: 13px;">
          <tr>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; color: #9ca3af;">Transaction Type:</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; font-weight: 700; color: #f3f4f6; text-align: right;">{html.escape(txn_type)}</td>
          </tr>
          <tr>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; color: #9ca3af;">Amount:</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; font-weight: 800; color: {color}; text-align: right;">{sign}₹{amt:.2f}</td>
          </tr>
          <tr>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; color: #9ca3af;">Description:</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; color: #d1d5db; text-align: right;">{html.escape(desc)}</td>
          </tr>
          <tr>
            <td style="padding: 10px 14px; color: #9ca3af;">Updated Balance:</td>
            <td style="padding: 10px 14px; font-weight: 700; color: #f3f4f6; text-align: right;">₹{bal:.2f}</td>
          </tr>
        </table>
        """

        full_html = cls._base_html(
            title=f"💳 Wallet {direction.capitalize()}",
            subtitle=f"{sign}₹{amt:.2f} • {desc}",
            body_html=body_html,
            header_gradient="linear-gradient(135deg, #10b981, #059669)" if is_credit else "linear-gradient(135deg, #ef4444, #991b1b)"
        )

        text_body = (
            f"Wallet Transaction Alert\n\n"
            f"Hi {user_name},\n"
            f"Direction: {direction}\n"
            f"Amount: {sign}₹{amt:.2f}\n"
            f"Description: {desc}\n"
            f"Updated Balance: ₹{bal:.2f}\n"
        )

        return {"subject": subject, "text_body": text_body, "html_body": full_html}

    # 10. Refund Issued Template
    @classmethod
    def _render_refund(
        cls,
        user_name: str = "User",
        amount_inr: Any = 0.0,
        reason: str = "",
        job_id: str = "",
        new_balance_inr: Any = 0.0,
        **kwargs: Any
    ) -> Dict[str, str]:
        amt = _safe_float(amount_inr)
        bal = _safe_float(kwargs.get("balance_inr") if kwargs.get("balance_inr") is not None else new_balance_inr)
        prev_bal = max(0.0, bal - amt)
        refund_id = kwargs.get("refund_id") or ""
        now_str = kwargs.get("timestamp") or datetime.now(timezone.utc).strftime("%d %b %Y, %I:%M %p UTC")
        inv_id = refund_id or f"RFND-TR-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{abs(hash(job_id or str(amt))) % 100000:05d}"
        cust_email = kwargs.get("recipient_email") or kwargs.get("user_email") or kwargs.get("email") or ""
        cust_phone = kwargs.get("phone_number") or kwargs.get("phone") or ""
        cust_uid = kwargs.get("user_id") or kwargs.get("uid") or ""

        job_note = f" • Tracker #{html.escape(job_id)}" if job_id else ""
        items = [
            {
                "desc": f"<strong>Service Refund / Credit Note</strong><br><span style='color: #64748b; font-size: 11px;'>Reason: {html.escape(reason or 'Automated delivery or cancellation policy refund')}{job_note}</span>",
                "qty": "1",
                "rate": f"₹{amt:.2f}",
                "amount": f"₹{amt:.2f}",
            }
        ]

        wallet_ledger = {
            "prev_bal": f"₹{prev_bal:.2f}",
            "action_label": "Refund Credited:",
            "impact_amt": f"+₹{amt:.2f}",
            "impact_color": "#059669",
            "new_bal": f"₹{bal:.2f}",
        }

        full_html = cls._render_invoice_html(
            doc_title="REFUND RECEIPT",
            status_label="● REFUND PROCESSED",
            status_color="#d97706",
            status_bg="#fef3c7",
            status_border="#fde68a",
            accent_gradient="linear-gradient(90deg, #f59e0b, #ef4444)",
            invoice_id=inv_id,
            order_id=job_id or "N/A",
            payment_id=refund_id or "N/A",
            payment_method="Credited to Wallet Balance",
            customer_name=user_name,
            customer_email=cust_email,
            customer_phone=cust_phone,
            customer_id=cust_uid,
            issue_date=now_str,
            items=items,
            subtotal_str=f"₹{amt:.2f}",
            tax_str=None,
            tax_label="",
            total_label="Net Refunded",
            grand_total_str=f"₹{amt:.2f}",
            grand_total_color="#d97706",
            wallet_ledger=wallet_ledger,
            terms_notes=[
                "This receipt confirms refund crediting to your TicketRadar wallet.",
                f"Refund reason: {reason or 'Automated delivery or cancellation policy refund'}",
                f"Reference: {refund_id or job_id or 'Automated Policy'}"
            ]
        )

        subject = f"Refund Issued: ₹{amt:.2f} credited to your wallet"
        text_body = (
            f"Refund Issued!\n\n"
            f"Hi {user_name},\n"
            f"A refund of ₹{amt:.2f} was processed to your wallet.\n"
            f"Reason: {reason}\n"
            f"Refund ID: {refund_id or 'N/A'}\n"
            f"Job ID: #{job_id or 'N/A'}\n"
            f"New Balance: ₹{bal:.2f}\n"
        )

        return {"subject": subject, "text_body": text_body, "html_body": full_html}

    # 11. Admin Pricing Changed Template (sent to Admin)
    @classmethod
    def _render_admin_pricing_changed(
        cls,
        admin_name: str = "Admin",
        admin_email: str = "",
        old_prices: Optional[Dict[str, Any]] = None,
        new_prices: Optional[Dict[str, Any]] = None,
        note: str = "",
        **kwargs: Any
    ) -> Dict[str, str]:
        subject = "🛡️ TicketRadar Audit: Notification Pricing Schedule Updated"
        old = old_prices or {}
        new = dict(new_prices or {})

        if kwargs.get("sms_inr") is not None:
            new["sms_paise"] = int(_safe_float(kwargs["sms_inr"]) * 100)
        if kwargs.get("whatsapp_inr") is not None:
            new["whatsapp_paise"] = int(_safe_float(kwargs["whatsapp_inr"]) * 100)
        if kwargs.get("call_inr") is not None:
            new["phone_call_paise"] = int(_safe_float(kwargs["call_inr"]) * 100)
        if kwargs.get("email_inr") is not None:
            new["email_paise"] = int(_safe_float(kwargs["email_inr"]) * 100)
        if kwargs.get("discord_inr") is not None:
            new["discord_paise"] = int(_safe_float(kwargs["discord_inr"]) * 100)

        def _fmt(paise: Any) -> str:
            val = int(paise) if paise is not None else 0
            return f"₹{val/100:.2f} ({val}p)"

        rows = [
            ("SMS Alert", _fmt(old.get("sms_paise", 50)), _fmt(new.get("sms_paise", 50))),
            ("WhatsApp Alert", _fmt(old.get("whatsapp_paise", 100)), _fmt(new.get("whatsapp_paise", 100))),
            ("Phone Call (Polly)", _fmt(old.get("phone_call_paise", 150)), _fmt(new.get("phone_call_paise", 150))),
            ("Email Alert", _fmt(old.get("email_paise", 0)), _fmt(new.get("email_paise", 0))),
            ("Discord Webhook", _fmt(old.get("discord_paise", 0)), _fmt(new.get("discord_paise", 0))),
        ]

        table_rows_html = "".join([
            f"""<tr>
              <td style="padding: 10px 14px; border: 1px solid #374151; color: #f3f4f6; font-weight: 600;">{html.escape(m)}</td>
              <td style="padding: 10px 14px; border: 1px solid #374151; color: #9ca3af; text-align: center;">{html.escape(o)}</td>
              <td style="padding: 10px 14px; border: 1px solid #374151; color: #34d399; font-weight: 700; text-align: center;">{html.escape(n)}</td>
            </tr>"""
            for m, o, n in rows
        ])

        body_html = f"""
        <p style="margin-top: 0; font-size: 15px;">Notification pricing was successfully updated by <strong>{html.escape(admin_name)}</strong> ({html.escape(admin_email)}).</p>
        <div style="margin: 16px 0; padding: 12px 14px; background-color: rgba(99, 102, 241, 0.1); border-left: 4px solid #6366f1; border-radius: 6px; font-size: 13px; color: #a5b4fc;">
          <strong>Audit Explanation:</strong> {html.escape(note or 'No justification provided.')}
        </div>
        <h4 style="color: #ffffff; margin-top: 18px; margin-bottom: 8px; font-size: 14px;">Price Schedule Changes</h4>
        <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
          <thead>
            <tr style="background-color: #111827; color: #ffffff;">
              <th style="padding: 10px 14px; border: 1px solid #374151; text-align: left;">Medium</th>
              <th style="padding: 10px 14px; border: 1px solid #374151; text-align: center;">Previous</th>
              <th style="padding: 10px 14px; border: 1px solid #374151; text-align: center;">New Price</th>
            </tr>
          </thead>
          <tbody>
            {table_rows_html}
          </tbody>
        </table>
        """

        full_html = cls._base_html(
            title="🛡️ Pricing Schedule Updated",
            subtitle=f"Changed by {admin_name}",
            body_html=body_html,
            header_gradient="linear-gradient(135deg, #6366f1, #a855f7)"
        )

        text_body = (
            f"Audit Alert: Pricing Updated\n\n"
            f"Changed By: {admin_name} ({admin_email})\n"
            f"Audit Reason: {note}\n\n"
            f"New Pricing:\n"
            + "\n".join([f"- {m}: {o} -> {n}" for m, o, n in rows])
        )

        return {"subject": subject, "text_body": text_body, "html_body": full_html}

    # 12. Job Created Template
    @classmethod
    def _render_job_created(
        cls,
        user_name: str = "User",
        job_id: str = "",
        movie_name: str = "",
        date_str: str = "",
        theatres: Optional[List[str]] = None,
        notification_medium: str = "Email",
        check_interval: int = 60,
        **kwargs: Any
    ) -> Dict[str, str]:
        subject = f"🎯 Tracker Activated: {movie_name} (#{job_id})"
        theatres_list = theatres or ([kwargs["cinema_name"]] if "cinema_name" in kwargs else [])
        th_str = ", ".join(theatres_list[:4]) + (f" and {len(theatres_list)-4} more" if len(theatres_list) > 4 else "")

        body_html = f"""
        <p style="margin-top: 0; font-size: 15px;">Hi <strong>{html.escape(user_name)}</strong>,</p>
        <p>Your ticket monitor for <strong>{html.escape(movie_name)}</strong> on <strong>{html.escape(date_str)}</strong> is now active!</p>
        <table style="width: 100%; border-collapse: collapse; margin: 18px 0; background-color: #111827; border-radius: 8px; font-size: 13px;">
          <tr>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; color: #9ca3af;">Tracker ID:</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; font-family: monospace; color: #f3f4f6; text-align: right;">#{html.escape(job_id)}</td>
          </tr>
          <tr>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; color: #9ca3af;">Target Cinemas:</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; color: #d1d5db; text-align: right;">{html.escape(th_str or 'All Available')}</td>
          </tr>
          <tr>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; color: #9ca3af;">Notification Medium:</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #2d3748; font-weight: 700; color: #ec4899; text-align: right;">{html.escape(notification_medium)}</td>
          </tr>
          <tr>
            <td style="padding: 10px 14px; color: #9ca3af;">Check Interval:</td>
            <td style="padding: 10px 14px; color: #f3f4f6; text-align: right;">Every {check_interval // 60} min ({check_interval}s)</td>
          </tr>
        </table>
        <p style="font-size: 13px; color: #9ca3af;">We will instantly alert you the moment BookMyShow opens seats for your selection.</p>
        """

        full_html = cls._base_html(
            title="🎯 Tracker Activated",
            subtitle=f"{movie_name} • #{job_id}",
            body_html=body_html,
            header_gradient="linear-gradient(135deg, #ec4899, #8b5cf6)"
        )

        text_body = (
            f"Tracker Activated!\n\n"
            f"Movie: {movie_name}\n"
            f"Date: {date_str}\n"
            f"Tracker ID: #{job_id}\n"
            f"Cinemas: {th_str or 'All Available'}\n"
            f"Medium: {notification_medium}\n"
        )

        return {"subject": subject, "text_body": text_body, "html_body": full_html}

    # 13. Job Cancelled Template
    @classmethod
    def _render_job_cancelled(
        cls,
        user_name: str = "User",
        job_id: str = "",
        movie_name: str = "",
        refund_amount_inr: Any = 0.0,
        **kwargs: Any
    ) -> Dict[str, str]:
        ref_amt = _safe_float(refund_amount_inr)
        reason = kwargs.get("reason", "")
        subject = f"Tracker Cancelled: #{job_id} ({movie_name})"
        refund_msg = f"A full refund of ₹{ref_amt:.2f} has been returned to your wallet." if ref_amt > 0 else f"Monitoring was stopped.{f' Reason: {reason}' if reason else ''}"

        body_html = f"""
        <p style="margin-top: 0; font-size: 15px;">Hi <strong>{html.escape(user_name)}</strong>,</p>
        <p>Your ticket monitor <strong>#{html.escape(job_id)}</strong> for <strong>{html.escape(movie_name)}</strong> has been stopped and cancelled.</p>
        <div style="margin: 18px 0; padding: 14px 16px; background-color: rgba(99, 102, 241, 0.08); border-left: 4px solid #6366f1; border-radius: 6px; font-size: 13px; color: #a5b4fc;">
          ℹ️ {html.escape(refund_msg)}
        </div>
        """

        full_html = cls._base_html(
            title="⏸️ Tracker Cancelled",
            subtitle=f"Job #{job_id}",
            body_html=body_html,
            header_gradient="linear-gradient(135deg, #6b7280, #374151)"
        )

        text_body = (
            f"Tracker #{job_id} Cancelled\n\n"
            f"Movie: {movie_name}\n"
            f"{refund_msg}\n"
        )

        return {"subject": subject, "text_body": text_body, "html_body": full_html}

    # 14. Notification Sent Template
    @classmethod
    def _render_notification_sent(
        cls,
        user_name: str = "User",
        movie_name: str = "",
        notification_medium: str = "",
        available_theatres: Optional[List[str]] = None,
        **kwargs: Any
    ) -> Dict[str, str]:
        med = kwargs.get("medium") or notification_medium or "Alert Channel"
        subject = f"Alert Dispatched: {movie_name} Tickets Available via {med}"
        body_html = f"""
        <p style="margin-top: 0; font-size: 15px;">Hi <strong>{html.escape(user_name)}</strong>,</p>
        <p>An availability alert was just successfully sent to you via <strong>{html.escape(med)}</strong> for <strong>{html.escape(movie_name)}</strong>.</p>
        """

        full_html = cls._base_html(
            title="🔔 Alert Dispatched",
            subtitle=f"Sent via {med}",
            body_html=body_html
        )

        text_body = f"Alert Dispatched: {movie_name} tickets available via {med}."
        return {"subject": subject, "text_body": text_body, "html_body": full_html}

    # 15. Notification Failed Template
    @classmethod
    def _render_notification_failed(
        cls,
        user_name: str = "User",
        job_id: str = "",
        movie_name: str = "",
        notification_medium: str = "",
        error_message: str = "",
        refunded: bool = True,
        **kwargs: Any
    ) -> Dict[str, str]:
        med = kwargs.get("medium") or notification_medium or "Alert Channel"
        err = kwargs.get("error_details") or error_message or "Technical delivery failure"
        subject = f"⚠️ Alert Delivery Failed: {movie_name} (#{job_id or 'Alert'}) via {med}"
        ref_note = "Your job fee has been automatically refunded to your wallet." if refunded else ""

        body_html = f"""
        <p style="margin-top: 0; font-size: 15px;">Hi <strong>{html.escape(user_name)}</strong>,</p>
        <p>We attempted to deliver a ticket availability alert for <strong>{html.escape(movie_name)}</strong> via <strong>{html.escape(med)}</strong>, but encountered an error.</p>
        <div style="margin: 18px 0; padding: 14px 16px; background-color: rgba(239, 68, 68, 0.1); border-left: 4px solid #ef4444; border-radius: 6px; font-size: 13px; color: #f87171;">
          <strong>Error Message:</strong> {html.escape(err)}
        </div>
        {f'<p style="font-size: 13px; color: #34d399;">✅ {html.escape(ref_note)}</p>' if ref_note else ''}
        """

        full_html = cls._base_html(
            title="⚠️ Delivery Failure",
            subtitle=f"Job #{job_id}",
            body_html=body_html,
            header_gradient="linear-gradient(135deg, #ef4444, #b91c1c)"
        )

        text_body = (
            f"Alert Delivery Failed\n\n"
            f"Movie: {movie_name}\n"
            f"Job ID: #{job_id}\n"
            f"Medium: {notification_medium}\n"
            f"Error: {error_message}\n"
            f"{ref_note}\n"
        )

        return {"subject": subject, "text_body": text_body, "html_body": full_html}

    # 16. Access Granted Template
    @classmethod
    def _render_access_granted(
        cls,
        recipient_email: str = "",
        user_name: str = "",
        **kwargs: Any
    ) -> Dict[str, str]:
        display_name = kwargs.get("name") or user_name or (recipient_email.split("@")[0] if recipient_email else "") or "User"
        subject = "Welcome to TicketRadar — Access Granted! 🎉"

        body_html = f"""
        <p style="margin-top: 0;">Hi <strong>{html.escape(display_name)}</strong>,</p>
        <p>Great news! Your access request for <strong>TicketRadar</strong> has been approved by an administrator.</p>
        <div style="margin: 20px 0; padding: 16px; background-color: rgba(16, 185, 129, 0.1); border-left: 4px solid #10b981; border-radius: 6px; font-size: 14px; color: #34d399;">
          🎉 <strong>Status: Account Authorized</strong><br>
          You now have full access to create ticket availability trackers, receive instant alerts, and configure notifications.
        </div>
        <h4 style="color: #ffffff; margin-top: 20px; margin-bottom: 10px;">What you can do next:</h4>
        <ul style="padding-left: 20px; margin: 0 0 20px 0; color: #d1d5db; font-size: 14px;">
          <li style="margin-bottom: 8px;">🎬 Track movie showtimes on BookMyShow for target dates & theatres</li>
          <li style="margin-bottom: 8px;">🔔 Receive instant alerts via SMS, WhatsApp, Voice Calls, Email, or Discord</li>
          <li style="margin-bottom: 8px;">⚡ Monitor availability automatically in the background</li>
        </ul>
        """

        full_html = cls._base_html(
            title="🍿 Access Granted!",
            subtitle="Welcome to TicketRadar",
            body_html=body_html,
            header_gradient="linear-gradient(135deg, #10b981, #ec4899)"
        )

        text_body = (
            f"Hi {display_name},\n\n"
            f"Great news! Your access request for TicketRadar has been approved by an administrator.\n\n"
            f"Account Email: {recipient_email}\n"
            f"Status: Authorized ✅\n\n"
            f"Happy Tracking!\nThe TicketRadar Team"
        )

        return {"subject": subject, "text_body": text_body, "html_body": full_html}
