#!/usr/bin/env python3
"""
ResearchFinder - Daily Cosmetic Ingredients Research Digest

Searches for latest research, regulations, and safety data on cosmetic
ingredients using Claude or OpenAI with web search, then emails a compiled digest.

Supports two providers:
  PROVIDER=anthropic  →  Claude API with web_search tool
  PROVIDER=openai     →  OpenAI Responses API with web_search_preview tool
"""

import smtplib
import os
import sys
import markdown
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")

# Configuration
PROVIDER = os.getenv("PROVIDER", "anthropic").lower()
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM") or SMTP_USER
EMAIL_TO = os.getenv("EMAIL_TO", "miriam@miriamllantada.com,ricardo@miriamllantada.com")

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6-20250514")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")

REPORTS_DIR = Path(__file__).parent / "reports"
PROMPT_FILE = Path(__file__).parent / "prompt.md"


def load_prompt():
    """Load the research prompt and fill in today's date."""
    today = datetime.now()
    text = PROMPT_FILE.read_text(encoding="utf-8")
    text = text.replace("{{DATE}}", today.strftime("%B %d, %Y"))
    text = text.replace("{{YEAR}}", str(today.year))
    return text


# ---------------------------------------------------------------------------
# Provider: Anthropic (Claude)
# ---------------------------------------------------------------------------

def search_anthropic(prompt):
    """Use Claude API with built-in web search."""
    import anthropic

    client = anthropic.Anthropic()
    print(f"  Provider: Anthropic ({ANTHROPIC_MODEL})")

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=16000,
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 12,
        }],
        messages=[{"role": "user", "content": prompt}],
    )

    text_parts = []
    for block in response.content:
        if hasattr(block, "text"):
            text_parts.append(block.text)

    return "\n".join(text_parts)


# ---------------------------------------------------------------------------
# Provider: OpenAI (GPT)
# ---------------------------------------------------------------------------

def search_openai(prompt):
    """Use OpenAI Responses API with built-in web search."""
    from openai import OpenAI

    client = OpenAI()
    print(f"  Provider: OpenAI ({OPENAI_MODEL})")

    response = client.responses.create(
        model=OPENAI_MODEL,
        tools=[{"type": "web_search_preview"}],
        input=prompt,
    )

    # Extract text from the response output
    text_parts = []
    for item in response.output:
        if hasattr(item, "content"):
            for content_block in item.content:
                if hasattr(content_block, "text"):
                    text_parts.append(content_block.text)
        elif hasattr(item, "text"):
            text_parts.append(item.text)

    return "\n".join(text_parts)


# ---------------------------------------------------------------------------
# Shared logic
# ---------------------------------------------------------------------------

PROVIDERS = {
    "anthropic": search_anthropic,
    "openai": search_openai,
}


def search_and_compile():
    """Search using the configured provider and compile the digest."""
    if PROVIDER not in PROVIDERS:
        raise ValueError(f"Unknown PROVIDER '{PROVIDER}'. Use 'anthropic' or 'openai'.")

    prompt = load_prompt()
    print("  Searching and compiling research digest...")

    result = PROVIDERS[PROVIDER](prompt)

    if not result.strip():
        raise RuntimeError("No text content returned from API")

    print(f"  Digest compiled ({len(result)} characters)")
    return result


def to_html(md_text):
    """Convert markdown report to styled HTML for email."""
    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "toc"],
    )

    provider_label = f"Claude ({ANTHROPIC_MODEL})" if PROVIDER == "anthropic" else f"OpenAI ({OPENAI_MODEL})"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    max-width: 800px; margin: 0 auto; padding: 20px;
    color: #1a1a1a; line-height: 1.6;
  }}
  h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
  h2 {{ color: #2980b9; margin-top: 30px; }}
  h3 {{ color: #27ae60; }}
  table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
  th, td {{ border: 1px solid #ddd; padding: 10px 12px; text-align: left; }}
  th {{ background-color: #3498db; color: white; }}
  tr:nth-child(even) {{ background-color: #f8f9fa; }}
  a {{ color: #2980b9; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  blockquote {{
    border-left: 4px solid #3498db; margin: 15px 0;
    padding: 10px 20px; background: #f0f7ff;
  }}
  ul, ol {{ padding-left: 24px; }}
  li {{ margin-bottom: 6px; }}
  .footer {{
    margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd;
    color: #777; font-size: 0.85em;
  }}
</style>
</head>
<body>
{html_body}
<div class="footer">
  <p>Generated by ResearchFinder | Powered by {provider_label}</p>
  <p>Report date: {datetime.now().strftime("%B %d, %Y at %H:%M")}</p>
</div>
</body>
</html>"""


def send_email(subject, html_body):
    """Send the digest via SMTP."""
    recipients = [r.strip() for r in EMAIL_TO.split(",")]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(recipients)

    plain_text = "View this email in an HTML-capable client for the best experience."
    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    print(f"  Sending to: {', '.join(recipients)}")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, recipients, msg.as_string())

    print("  Email sent successfully.")


def save_report(md_text, html_text):
    """Save report locally as markdown and HTML."""
    REPORTS_DIR.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")

    md_path = REPORTS_DIR / f"{date_str}.md"
    html_path = REPORTS_DIR / f"{date_str}.html"

    md_path.write_text(md_text, encoding="utf-8")
    html_path.write_text(html_text, encoding="utf-8")

    print(f"  Saved: {md_path}")
    print(f"  Saved: {html_path}")


def main():
    today = datetime.now().strftime("%B %d, %Y")
    print(f"[ResearchFinder] {today}")
    print("=" * 50)

    # Validate config
    missing = []
    if PROVIDER == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY")
    if PROVIDER == "openai" and not os.getenv("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY")
    if not SMTP_USER:
        missing.append("SMTP_USER")
    if not SMTP_PASSWORD:
        missing.append("SMTP_PASSWORD")

    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}", file=sys.stderr)
        print("Copy .env.example to .env and fill in your credentials.", file=sys.stderr)
        sys.exit(1)

    try:
        report_md = search_and_compile()
        report_html = to_html(report_md)
        save_report(report_md, report_html)
        send_email(f"Cosmetic Ingredients Research Digest — {today}", report_html)
        print("\nDone.")
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
