import logging
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Category, Trace

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Seed data — 4 realistic conversations per category
# ---------------------------------------------------------------------------

_SEED_TRACES: list[dict] = [
    # ── Billing ──────────────────────────────────────────────────────────────
    {
        "category": Category.billing,
        "user_message": "Hi, I was charged $49 this month but my plan is $29. Can you explain the difference?",
        "bot_response": (
            "I'm sorry for the confusion! The $20 difference is due to a mid-cycle upgrade "
            "you made on the 12th. You were billed a prorated amount for the remaining days. "
            "I can send a detailed invoice breakdown to your email if that would help."
        ),
    },
    {
        "category": Category.billing,
        "user_message": "I never received an invoice for last month. Where can I find it?",
        "bot_response": (
            "All invoices are available in your account under Settings → Billing → Invoice History. "
            "If the invoice for last month is missing, it may still be generating. "
            "Please allow up to 24 hours, or contact us and we'll send it manually."
        ),
    },
    {
        "category": Category.billing,
        "user_message": "My credit card was declined when trying to update my payment method. What should I do?",
        "bot_response": (
            "This is usually caused by your bank blocking the transaction as a precaution. "
            "Please contact your bank to authorise charges from us, then retry the update. "
            "Alternatively, you can add a different card or use PayPal as a backup payment method."
        ),
    },
    {
        "category": Category.billing,
        "user_message": "Do you offer annual billing? Is there a discount compared to monthly?",
        "bot_response": (
            "Yes! Switching to annual billing saves you 20% compared to the monthly rate. "
            "You can switch at any time from Settings → Billing → Billing Cycle. "
            "The discount is applied immediately and a prorated credit is added to your account."
        ),
    },

    # ── Refund ───────────────────────────────────────────────────────────────
    {
        "category": Category.refund,
        "user_message": "I was accidentally charged twice this week. I'd like a refund for the duplicate charge.",
        "bot_response": (
            "I sincerely apologise for the duplicate charge — that should never happen. "
            "I've flagged your account and our billing team will issue a full refund within 3–5 business days. "
            "You'll receive a confirmation email once it's processed."
        ),
    },
    {
        "category": Category.refund,
        "user_message": "I cancelled my subscription 2 days ago but was still charged for the full month. Can I get a refund?",
        "bot_response": (
            "I completely understand your concern. Since you cancelled within the billing period, "
            "you're eligible for a partial refund for the unused days. "
            "I'll submit the refund request now and you should see it reflected within 5–7 business days."
        ),
    },
    {
        "category": Category.refund,
        "user_message": "The feature I paid for doesn't work at all. I want my money back.",
        "bot_response": (
            "I'm really sorry the feature isn't working as expected — that's absolutely frustrating. "
            "Our team is actively investigating the issue. "
            "In the meantime, I've submitted a refund request on your behalf. "
            "Could you also share the specific feature and any error messages so we can fix this faster?"
        ),
    },
    {
        "category": Category.refund,
        "user_message": "I signed up by mistake and haven't used the service at all. Is a refund possible?",
        "bot_response": (
            "No worries at all — mistakes happen! Since you haven't used the service, "
            "we're happy to process a full refund. "
            "Please note our refund policy covers requests made within 7 days of the charge. "
            "I've initiated the refund now, and it should appear on your statement within 5 business days."
        ),
    },

    # ── Account Access ────────────────────────────────────────────────────────
    {
        "category": Category.account_access,
        "user_message": "I can't log in to my account. I keep getting 'invalid credentials' even though I'm sure my password is correct.",
        "bot_response": (
            "Sorry for the trouble! First, try resetting your password using the 'Forgot Password' link on the login page. "
            "If you're still locked out after that, it's possible your account has been temporarily suspended for security reasons. "
            "Please reply with your registered email and we'll investigate right away."
        ),
    },
    {
        "category": Category.account_access,
        "user_message": "I lost access to my MFA authenticator app. How do I recover my account?",
        "bot_response": (
            "Account recovery without MFA requires identity verification for your security. "
            "Please email support@supportlens.io from your registered address with a photo ID. "
            "Our team will verify your identity and disable MFA so you can set it up fresh — "
            "this typically takes 1 business day."
        ),
    },
    {
        "category": Category.account_access,
        "user_message": "My team member says they weren't invited even though I sent an invite 3 days ago. What's wrong?",
        "bot_response": (
            "The invite email may have landed in their spam or junk folder — please ask them to check there first. "
            "If it's not there, you can resend the invite from Settings → Team → Pending Invites. "
            "Invites expire after 7 days, so resending will also refresh the expiry window."
        ),
    },
    {
        "category": Category.account_access,
        "user_message": "I changed my email address but now I can't receive the verification code. I'm locked out.",
        "bot_response": (
            "This can happen if the new email address was mistyped during the change. "
            "Please contact us with your old email address and we can manually verify and update it. "
            "For security, we'll send a one-time code to your old address to confirm the change."
        ),
    },

    # ── Cancellation ─────────────────────────────────────────────────────────
    {
        "category": Category.cancellation,
        "user_message": "I want to cancel my subscription. How do I do that?",
        "bot_response": (
            "We're sorry to see you go! You can cancel anytime from Settings → Billing → Cancel Subscription. "
            "Your access will remain active until the end of the current billing period. "
            "If you'd like, I can also connect you with our team to explore a pause or downgrade option instead."
        ),
    },
    {
        "category": Category.cancellation,
        "user_message": "I'm cancelling because the pricing is too expensive for my small team. Any options?",
        "bot_response": (
            "Thank you for being honest — we appreciate your feedback! "
            "We do have a Startup plan at 50% off for teams under 5 people that you might not be aware of. "
            "Would you like me to apply it to your account before you proceed with cancellation?"
        ),
    },
    {
        "category": Category.cancellation,
        "user_message": "Please cancel my account immediately and delete all my data.",
        "bot_response": (
            "I've submitted the cancellation request and your subscription has been stopped immediately. "
            "For a full data deletion request under GDPR/CCPA, please allow up to 30 days for complete removal. "
            "You'll receive a confirmation email once your data has been permanently deleted."
        ),
    },
    {
        "category": Category.cancellation,
        "user_message": "I cancelled last month but I was still charged. Can you cancel and refund me?",
        "bot_response": (
            "I'm very sorry about that — it looks like the cancellation did not process correctly on our end. "
            "I've cancelled your subscription now and raised an urgent refund request for the incorrect charge. "
            "You should see the refund within 3–5 business days along with a confirmation email."
        ),
    },

    # ── General Inquiry ───────────────────────────────────────────────────────
    {
        "category": Category.general_inquiry,
        "user_message": "What integrations do you support with third-party tools like Slack or Jira?",
        "bot_response": (
            "We currently support native integrations with Slack, Jira, GitHub, and Zapier. "
            "Slack and Jira integrations can be set up directly from Settings → Integrations. "
            "For Zapier, you can find us in their marketplace to connect with 5,000+ other apps."
        ),
    },
    {
        "category": Category.general_inquiry,
        "user_message": "How do I export my data from the platform?",
        "bot_response": (
            "You can export all your data in CSV or JSON format from Settings → Data → Export. "
            "Large exports may take a few minutes — you'll receive an email with a download link once ready. "
            "Exports include all traces, tickets, and account history."
        ),
    },
    {
        "category": Category.general_inquiry,
        "user_message": "Is there a free trial available before I commit to a paid plan?",
        "bot_response": (
            "Absolutely! We offer a 14-day free trial with full access to all features — no credit card required. "
            "At the end of the trial, you can choose any plan to continue, or your account will automatically "
            "switch to our free tier with limited usage."
        ),
    },
    {
        "category": Category.general_inquiry,
        "user_message": "What are your support hours and how can I reach a human agent?",
        "bot_response": (
            "Our human support team is available Monday–Friday, 9am–6pm EST via live chat and email. "
            "For urgent issues outside those hours, you can submit a priority ticket and we aim to respond "
            "within 4 hours. Enterprise plan customers also have access to 24/7 phone support."
        ),
    },
]


def _random_timestamp() -> datetime:
    """Return a UTC timestamp randomly spread across the last 30 days."""
    offset_seconds = random.randint(0, 30 * 24 * 3600)
    return datetime.now(timezone.utc) - timedelta(seconds=offset_seconds)


def seed_database() -> None:
    """Insert seed traces if the traces table is empty. Safe to call on every startup."""
    db: Session = SessionLocal()
    try:
        existing = db.query(Trace).count()
        if existing > 0:
            logger.info("seed_database: %d trace(s) already present — skipping seed.", existing)
            return

        logger.info("seed_database: table is empty — inserting %d seed traces.", len(_SEED_TRACES))

        for item in _SEED_TRACES:
            db.add(
                Trace(
                    id=str(uuid.uuid4()),
                    user_message=item["user_message"],
                    bot_response=item["bot_response"],
                    category=item["category"],
                    timestamp=_random_timestamp(),
                    response_time_ms=random.randint(400, 1800),
                )
            )

        db.commit()
        logger.info("seed_database: seed complete.")

    except Exception:
        db.rollback()
        logger.exception("seed_database: failed to seed — rolling back.")
    finally:
        db.close()
