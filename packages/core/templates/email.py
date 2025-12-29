"""Email templates for Airport notifications.

This module provides both plain text and HTML email templates
for various notification types.
"""

from datetime import date
from typing import Any


class EmailTemplates:
    """
    Email template generator.

    Provides both plain text and HTML versions of all email templates.
    Templates are styled to match the Airport brand.
    """

    # Brand colors
    PRIMARY_COLOR = "#2563eb"  # Blue
    SECONDARY_COLOR = "#64748b"  # Gray
    SUCCESS_COLOR = "#22c55e"  # Green
    WARNING_COLOR = "#f59e0b"  # Amber
    DANGER_COLOR = "#ef4444"  # Red

    @classmethod
    def _base_html(cls, content: str, title: str = "Airport Notification") -> str:
        """Wrap content in base HTML template."""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #1f2937;
            margin: 0;
            padding: 0;
            background-color: #f3f4f6;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .card {{
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            padding: 24px;
            margin-bottom: 20px;
        }}
        .header {{
            text-align: center;
            padding-bottom: 20px;
            border-bottom: 1px solid #e5e7eb;
            margin-bottom: 20px;
        }}
        .logo {{
            font-size: 24px;
            font-weight: bold;
            color: {cls.PRIMARY_COLOR};
        }}
        .title {{
            font-size: 20px;
            font-weight: 600;
            color: #111827;
            margin: 0 0 16px 0;
        }}
        .subtitle {{
            font-size: 14px;
            color: {cls.SECONDARY_COLOR};
            margin: 0 0 16px 0;
        }}
        .content {{
            margin-bottom: 24px;
        }}
        .button {{
            display: inline-block;
            background-color: {cls.PRIMARY_COLOR};
            color: #ffffff !important;
            text-decoration: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-weight: 500;
        }}
        .button:hover {{
            background-color: #1d4ed8;
        }}
        .info-box {{
            background-color: #eff6ff;
            border-left: 4px solid {cls.PRIMARY_COLOR};
            padding: 16px;
            margin: 16px 0;
            border-radius: 0 4px 4px 0;
        }}
        .warning-box {{
            background-color: #fffbeb;
            border-left: 4px solid {cls.WARNING_COLOR};
            padding: 16px;
            margin: 16px 0;
            border-radius: 0 4px 4px 0;
        }}
        .danger-box {{
            background-color: #fef2f2;
            border-left: 4px solid {cls.DANGER_COLOR};
            padding: 16px;
            margin: 16px 0;
            border-radius: 0 4px 4px 0;
        }}
        .success-box {{
            background-color: #f0fdf4;
            border-left: 4px solid {cls.SUCCESS_COLOR};
            padding: 16px;
            margin: 16px 0;
            border-radius: 0 4px 4px 0;
        }}
        .footer {{
            text-align: center;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            margin-top: 20px;
            font-size: 12px;
            color: {cls.SECONDARY_COLOR};
        }}
        .deadline-item {{
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
        }}
        .deadline-item:last-child {{
            border-bottom: none;
        }}
        .deadline-name {{
            font-weight: 500;
            color: #111827;
        }}
        .deadline-date {{
            font-size: 14px;
            color: {cls.SECONDARY_COLOR};
        }}
        .deadline-urgent {{
            color: {cls.DANGER_COLOR};
            font-weight: 600;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }}
        th {{
            background-color: #f9fafb;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            color: {cls.SECONDARY_COLOR};
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="header">
                <div class="logo">Airport</div>
            </div>
            {content}
            <div class="footer">
                <p>This email was sent by Airport Transaction Coordination Platform</p>
                <p>Please do not reply to this email.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

    @classmethod
    def deadline_reminder(
        cls,
        user_name: str,
        deadline_name: str,
        due_date: str,
        days_remaining: int,
        property_address: str,
        transaction_url: str | None = None,
    ) -> tuple[str, str]:
        """
        Generate deadline reminder email.

        Returns:
            tuple: (plain_text, html)
        """
        urgency = "urgent" if days_remaining <= 1 else "upcoming"
        urgency_class = "danger-box" if days_remaining <= 1 else "warning-box"

        plain_text = f"""
Hi {user_name},

DEADLINE REMINDER: {deadline_name}

Property: {property_address}
Due Date: {due_date}
Days Remaining: {days_remaining} day(s)

Please take action on this deadline before it expires.

{"This deadline is due very soon. Please prioritize this item." if days_remaining <= 1 else ""}

Best regards,
Airport Transaction Coordination
"""

        html_content = f"""
<h1 class="title">Deadline Reminder</h1>
<p class="subtitle">A deadline requires your attention</p>

<div class="{urgency_class}">
    <strong>{deadline_name}</strong><br>
    Due: {due_date} ({days_remaining} day{"s" if days_remaining != 1 else ""} remaining)
</div>

<div class="content">
    <p><strong>Property:</strong> {property_address}</p>
    <p>{"This deadline is due very soon. Please prioritize this item." if days_remaining <= 1 else "Please review and take action before this deadline expires."}</p>
</div>

{"<p><a href='" + transaction_url + "' class='button'>View Transaction</a></p>" if transaction_url else ""}
"""

        return plain_text.strip(), cls._base_html(html_content, "Deadline Reminder")

    @classmethod
    def daily_digest(
        cls,
        user_name: str,
        upcoming_deadlines: list[dict[str, Any]],
        overdue_deadlines: list[dict[str, Any]],
        documents_pending_review: int,
        transactions_closing_soon: int,
        dashboard_url: str | None = None,
    ) -> tuple[str, str]:
        """
        Generate daily digest email.

        Returns:
            tuple: (plain_text, html)
        """
        today = date.today().strftime("%B %d, %Y")

        plain_text = f"""
Hi {user_name},

DAILY DIGEST - {today}

SUMMARY:
- Upcoming Deadlines: {len(upcoming_deadlines)}
- Overdue Deadlines: {len(overdue_deadlines)}
- Documents Pending Review: {documents_pending_review}
- Transactions Closing Soon: {transactions_closing_soon}

"""
        if overdue_deadlines:
            plain_text += "OVERDUE DEADLINES:\n"
            for d in overdue_deadlines:
                plain_text += f"  - {d['name']} (was due {d['due_date']})\n"
            plain_text += "\n"

        if upcoming_deadlines:
            plain_text += "UPCOMING DEADLINES:\n"
            for d in upcoming_deadlines[:5]:
                plain_text += f"  - {d['name']} - Due {d['due_date']}\n"
            plain_text += "\n"

        plain_text += """
Best regards,
Airport Transaction Coordination
"""

        # Build HTML deadline tables
        overdue_html = ""
        if overdue_deadlines:
            overdue_html = f"""
<div class="danger-box">
    <strong>{len(overdue_deadlines)} Overdue Deadline{"s" if len(overdue_deadlines) != 1 else ""}</strong>
</div>
<table>
    <thead>
        <tr>
            <th>Deadline</th>
            <th>Due Date</th>
            <th>Property</th>
        </tr>
    </thead>
    <tbody>
"""
            for d in overdue_deadlines:
                overdue_html += f"""
        <tr>
            <td class="deadline-urgent">{d['name']}</td>
            <td>{d['due_date']}</td>
            <td>{d.get('property', 'N/A')}</td>
        </tr>
"""
            overdue_html += """
    </tbody>
</table>
"""

        upcoming_html = ""
        if upcoming_deadlines:
            upcoming_html = """
<h3>Upcoming Deadlines</h3>
<table>
    <thead>
        <tr>
            <th>Deadline</th>
            <th>Due Date</th>
            <th>Days Left</th>
        </tr>
    </thead>
    <tbody>
"""
            for d in upcoming_deadlines[:10]:
                upcoming_html += f"""
        <tr>
            <td>{d['name']}</td>
            <td>{d['due_date']}</td>
            <td>{d.get('days_remaining', 'N/A')}</td>
        </tr>
"""
            upcoming_html += """
    </tbody>
</table>
"""

        html_content = f"""
<h1 class="title">Daily Digest</h1>
<p class="subtitle">{today}</p>

<div class="info-box">
    <table style="border: none;">
        <tr>
            <td style="border: none; padding: 8px;"><strong>{len(upcoming_deadlines)}</strong><br>Upcoming</td>
            <td style="border: none; padding: 8px;"><strong>{len(overdue_deadlines)}</strong><br>Overdue</td>
            <td style="border: none; padding: 8px;"><strong>{documents_pending_review}</strong><br>Pending Review</td>
            <td style="border: none; padding: 8px;"><strong>{transactions_closing_soon}</strong><br>Closing Soon</td>
        </tr>
    </table>
</div>

{overdue_html}
{upcoming_html}

{"<p style='text-align: center; margin-top: 24px;'><a href='" + dashboard_url + "' class='button'>Go to Dashboard</a></p>" if dashboard_url else ""}
"""

        return plain_text.strip(), cls._base_html(html_content, f"Daily Digest - {today}")

    @classmethod
    def document_needs_review(
        cls,
        user_name: str,
        document_type: str,
        filename: str,
        property_address: str,
        confidence: float,
        review_reasons: list[str],
        review_url: str | None = None,
    ) -> tuple[str, str]:
        """
        Generate document review notification email.

        Returns:
            tuple: (plain_text, html)
        """
        confidence_pct = int(confidence * 100)

        plain_text = f"""
Hi {user_name},

DOCUMENT REVIEW REQUIRED

A document has been uploaded and requires your review.

Document Type: {document_type}
Filename: {filename}
Property: {property_address}
Extraction Confidence: {confidence_pct}%

Review Reasons:
"""
        for reason in review_reasons:
            plain_text += f"  - {reason}\n"

        plain_text += """

Please review the extracted data and verify its accuracy.

Best regards,
Airport Transaction Coordination
"""

        reasons_html = "".join([f"<li>{r}</li>" for r in review_reasons])

        html_content = f"""
<h1 class="title">Document Review Required</h1>
<p class="subtitle">A document needs your attention</p>

<div class="warning-box">
    <strong>Extraction Confidence: {confidence_pct}%</strong><br>
    Manual review recommended
</div>

<div class="content">
    <p><strong>Document Type:</strong> {document_type}</p>
    <p><strong>Filename:</strong> {filename}</p>
    <p><strong>Property:</strong> {property_address}</p>

    <h3>Review Reasons:</h3>
    <ul>
        {reasons_html}
    </ul>
</div>

{"<p><a href='" + review_url + "' class='button'>Review Document</a></p>" if review_url else ""}
"""

        return plain_text.strip(), cls._base_html(html_content, "Document Review Required")

    @classmethod
    def transaction_status_change(
        cls,
        user_name: str,
        property_address: str,
        old_status: str,
        new_status: str,
        changed_by: str,
        transaction_url: str | None = None,
    ) -> tuple[str, str]:
        """
        Generate transaction status change notification.

        Returns:
            tuple: (plain_text, html)
        """
        plain_text = f"""
Hi {user_name},

TRANSACTION STATUS UPDATE

Property: {property_address}
Status Changed: {old_status} -> {new_status}
Changed By: {changed_by}

Best regards,
Airport Transaction Coordination
"""

        status_class = "success-box" if new_status.lower() == "closed" else "info-box"

        html_content = f"""
<h1 class="title">Transaction Status Update</h1>
<p class="subtitle">{property_address}</p>

<div class="{status_class}">
    <strong>Status Changed</strong><br>
    {old_status} → {new_status}
</div>

<div class="content">
    <p>Changed by: {changed_by}</p>
</div>

{"<p><a href='" + transaction_url + "' class='button'>View Transaction</a></p>" if transaction_url else ""}
"""

        return plain_text.strip(), cls._base_html(html_content, "Transaction Status Update")

    @classmethod
    def welcome_email(
        cls,
        user_name: str,
        organization_name: str,
        login_url: str,
        temp_password: str | None = None,
    ) -> tuple[str, str]:
        """
        Generate welcome email for new users.

        Returns:
            tuple: (plain_text, html)
        """
        plain_text = f"""
Hi {user_name},

Welcome to Airport!

You've been added to {organization_name} on Airport, the AI-powered transaction coordination platform.

{"Your temporary password is: " + temp_password + chr(10) + "Please change this after your first login." if temp_password else ""}

Getting Started:
1. Log in to your account
2. Review your upcoming deadlines
3. Upload and manage transaction documents
4. Track compliance status

If you have any questions, please contact your administrator.

Best regards,
The Airport Team
"""

        password_section = ""
        if temp_password:
            password_section = f"""
<div class="warning-box">
    <strong>Temporary Password:</strong> {temp_password}<br>
    Please change this after your first login.
</div>
"""

        html_content = f"""
<h1 class="title">Welcome to Airport!</h1>
<p class="subtitle">You've been added to {organization_name}</p>

{password_section}

<div class="content">
    <h3>Getting Started</h3>
    <ol>
        <li>Log in to your account</li>
        <li>Review your upcoming deadlines</li>
        <li>Upload and manage transaction documents</li>
        <li>Track compliance status</li>
    </ol>
</div>

<p style="text-align: center;"><a href="{login_url}" class="button">Log In Now</a></p>
"""

        return plain_text.strip(), cls._base_html(html_content, "Welcome to Airport")

    @classmethod
    def password_reset(
        cls,
        user_name: str,
        reset_url: str,
        expires_in_hours: int = 24,
    ) -> tuple[str, str]:
        """
        Generate password reset email.

        Returns:
            tuple: (plain_text, html)
        """
        plain_text = f"""
Hi {user_name},

PASSWORD RESET REQUEST

We received a request to reset your password.

Click the link below to reset your password:
{reset_url}

This link will expire in {expires_in_hours} hours.

If you didn't request this, please ignore this email.

Best regards,
Airport Transaction Coordination
"""

        html_content = f"""
<h1 class="title">Password Reset Request</h1>
<p class="subtitle">We received a request to reset your password</p>

<div class="content">
    <p>Click the button below to reset your password. This link will expire in {expires_in_hours} hours.</p>
</div>

<p style="text-align: center;"><a href="{reset_url}" class="button">Reset Password</a></p>

<div class="info-box">
    If you didn't request this password reset, please ignore this email. Your password will remain unchanged.
</div>
"""

        return plain_text.strip(), cls._base_html(html_content, "Password Reset Request")

    @classmethod
    def closing_reminder(
        cls,
        user_name: str,
        property_address: str,
        closing_date: str,
        days_until_closing: int,
        checklist_status: dict[str, int],
        transaction_url: str | None = None,
    ) -> tuple[str, str]:
        """
        Generate closing reminder email.

        Returns:
            tuple: (plain_text, html)
        """
        completed = checklist_status.get("completed", 0)
        total = checklist_status.get("total", 0)
        completion_pct = int((completed / total * 100) if total > 0 else 0)

        urgency_class = "danger-box" if days_until_closing <= 3 else "warning-box"

        plain_text = f"""
Hi {user_name},

CLOSING REMINDER

Property: {property_address}
Closing Date: {closing_date}
Days Until Closing: {days_until_closing}

Checklist Status: {completed}/{total} items complete ({completion_pct}%)

Please ensure all required documents and tasks are completed before closing.

Best regards,
Airport Transaction Coordination
"""

        html_content = f"""
<h1 class="title">Closing Reminder</h1>
<p class="subtitle">{property_address}</p>

<div class="{urgency_class}">
    <strong>Closing Date: {closing_date}</strong><br>
    {days_until_closing} day{"s" if days_until_closing != 1 else ""} until closing
</div>

<div class="content">
    <h3>Checklist Status</h3>
    <div class="info-box">
        <strong>{completed}/{total}</strong> items complete ({completion_pct}%)
    </div>
    <p>Please ensure all required documents and tasks are completed before closing.</p>
</div>

{"<p style='text-align: center;'><a href='" + transaction_url + "' class='button'>View Transaction</a></p>" if transaction_url else ""}
"""

        return plain_text.strip(), cls._base_html(html_content, "Closing Reminder")
