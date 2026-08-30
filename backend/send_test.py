#!/usr/bin/env python3
"""Send one real WhatsApp message, to a number we own, to prove the setup works.

    python backend/send_test.py check         config only, sends nothing, free
    python backend/send_test.py hello --yes   Meta's pre-approved hello_world  <- START HERE
    python backend/send_test.py recap --yes   our mid-call template (needs approval)
    python backend/send_test.py media --yes   follow-up template + architecture image
    python backend/send_test.py resume --yes  resume document template

Run `hello` first: it uses the sample template that ships approved with every
account, so it proves the credentials and the send path without depending on our
own templates clearing review.

Safety: only ever sends to ALLOWED_DESTINATION (which is your own TEST_NUMBER).
Reaching the evaluator additionally requires ALLOW_EVALUATOR=1, set deliberately.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from app.config import EVALUATOR_NUMBER, load_env, settings  # noqa: E402

ENV_FILE = load_env()

from app import whatsapp  # noqa: E402

OK, BAD, INFO = "  [ok]", "  [FAIL]", "  [..]"


def cmd_check():
    print(f"\nWHATSAPP CONFIG  (credentials from {ENV_FILE})\n" + "-" * 56)
    print(f"{INFO} provider      : {whatsapp.provider()}"
          f"   free-form={whatsapp.supports_freeform()}")

    if whatsapp.provider() == "ultramsg":
        fields = [
            ("ULTRAMSG_INSTANCE_ID", settings.um_instance, True),
            ("ULTRAMSG_TOKEN", settings.um_token, True),
            ("WHATSAPP_ARCHITECTURE_IMAGE_URL", settings.wa_architecture_url, False),
            ("WHATSAPP_RESUME_URL", settings.wa_resume_url, False),
            ("YOUR_NAME", settings.your_name, False),
            ("YOUR_MOBILE_NUMBER", settings.your_mobile, False),
        ]
    else:
        fields = [
            ("WHATSAPP_PHONE_NUMBER_ID", settings.wa_phone_number_id, True),
            ("WHATSAPP_ACCESS_TOKEN", settings.wa_access_token, True),
            ("WHATSAPP_BUSINESS_ACCOUNT_ID", settings.wa_business_account_id, False),
            ("WHATSAPP_SENDER_NUMBER", settings.wa_sender_number, False),
            ("WHATSAPP_ARCHITECTURE_IMAGE_URL", settings.wa_architecture_url, False),
            ("WHATSAPP_RESUME_URL", settings.wa_resume_url, False),
            ("YOUR_MOBILE_NUMBER", settings.your_mobile, False),
        ]
    missing_required = []
    for name, val, required in fields:
        if val:
            shown = val if name.endswith(("URL", "NUMBER")) and "TOKEN" not in name else \
                f"set ({len(val)} chars, not shown)"
            print(f"{OK} {name} = {shown}")
        else:
            print(f"{BAD if required else INFO} {name} is empty"
                  f"{'  <-- required' if required else '  (optional for now)'}")
            if required:
                missing_required.append(name)

    if whatsapp.provider() == "ultramsg":
        # The one thing worth checking before a live call: is the linked phone
        # actually connected? An unauthenticated instance queues messages
        # silently instead of failing, which on a timed row is the worst outcome.
        from app import ultramsg
        try:
            acct = ((ultramsg.status().get("status") or {}).get("accountStatus") or {})
            state = f"{acct.get('status')}/{acct.get('substatus')}"
            good = acct.get("status") == "authenticated"
            print(f"\n{OK if good else BAD} instance      : {state}")
            if not good:
                print("       Messages will QUEUE, not send. Re-link the phone in "
                      "the UltraMsg dashboard.")
        except Exception as exc:
            print(f"\n{BAD} instance      : cannot reach UltraMsg - {exc}")
        print(f"{INFO} templates     : none needed (free-form provider)")
    else:
        print(f"\n{INFO} api version   : {settings.wa_api_version}")
        print(f"{INFO} templates     : {settings.wa_tpl_midcall} | "
              f"{settings.wa_tpl_followup} | {settings.wa_tpl_resume}"
              f"  (lang={settings.wa_template_lang})")
    print(f"{INFO} will send to  : {settings.allowed_destination}")

    dest = whatsapp.normalize(settings.allowed_destination)
    ev = whatsapp.normalize(EVALUATOR_NUMBER)
    if dest and dest[-10:] == ev[-10:]:
        print(f"{BAD} destination is the EVALUATOR. Blocked unless ALLOW_EVALUATOR=1.")
    else:
        print(f"{OK} destination is not the evaluator")

    print("\n" + "-" * 56)
    if missing_required:
        print("NOT READY - fill in: " + ", ".join(missing_required))
        return 1
    print("READY.  next:  python backend/send_test.py hello --yes"
          "   (hello_world - proves credentials without waiting on approval)")
    return 0


def _guard():
    if "--yes" not in sys.argv:
        print(f"{BAD} refusing to send without --yes (this sends a real message)")
        return False
    if cmd_check() != 0:
        return False
    return True


def _run(label, fn):
    print(f"\n{INFO} sending: {label} -> {settings.allowed_destination}")
    try:
        res = fn()
        print(f"{OK} accepted by Meta. message id: {res['message_id']}")
        print("      Check the handset. If nothing arrives, the message was accepted")
        print("      but not delivered - usually the template is not approved yet,")
        print("      or the app is unpublished.")
        return 0
    except whatsapp.WhatsAppError as exc:
        print(f"{BAD} {exc}")
        print(_hint(exc))
        return 1


def _hint(exc):
    d = (exc.detail or "").lower()
    if "template" in d and ("not exist" in d or "not found" in d):
        return ("  HINT: Meta returns this for BOTH a wrong name/language AND a template\n"
                "        that is not approved yet - the error does not distinguish them.\n"
                "          - still Pending review?  expected. use `hello` meanwhile.\n"
                "          - already Approved?      check the exact name and language in\n"
                "            WhatsApp Manager. `en` vs `en_US` is the usual culprit; set\n"
                "            WHATSAPP_TEMPLATE_LANG in .env to match it exactly.\n")
    if exc.status in (401, 403) or "token" in d:
        return ("  HINT: token problem. The API Setup token expires in 24h - use a\n"
                "        System User token with expiration Never (setup guide Step 6).\n")
    if "recipient" in d or "not in allowed list" in d:
        return ("  HINT: you are still on the Meta TEST number, which only reaches\n"
                "        pre-verified recipients. Register your real sender number.\n")
    if "media" in d or "download" in d:
        return ("  HINT: Meta could not fetch the media URL. It must be a DIRECT file\n"
                "        link - Google Drive/Dropbox share pages do not work.\n")
    if "24" in d and "window" in d:
        return ("  HINT: free-form needs an open customer-service window. Expected\n"
                "        when the recipient has never messaged us - use a template.\n")
    return ""


def cmd_hello():
    """Meta's built-in sample template. The cleanest possible connectivity test.

    `hello_world` ships pre-approved with every WhatsApp Business Account and
    takes no parameters, so it isolates credentials and reachability from our
    own templates being stuck in review. If this works, the token, the phone
    number ID and the send path are all proven.

    It is registered as **en_US**, not `en` - sending `en` fails with a
    confusing "template does not exist" rather than a language error.
    """
    if not _guard():
        return 1
    if whatsapp.supports_freeform():
        # No template to fall back on, and none needed - plain text is the
        # provider's normal path, so this proves exactly what will be used.
        return _run("free-form text (no template needed)",
                    lambda: whatsapp.send_text(
                        settings.allowed_destination,
                        "Test from the ElevateBox voice agent. If you can read "
                        "this, the WhatsApp path works end to end."))
    name = os.environ.get("WHATSAPP_TEMPLATE_HELLO", "hello_world")
    lang = os.environ.get("WHATSAPP_TEMPLATE_HELLO_LANG", "en_US")
    print(f"{INFO} using the pre-approved sample template: {name} ({lang})")
    return _run(f"template {name} (no variables, no media)",
                lambda: whatsapp.send_template(settings.allowed_destination, name, lang=lang))


def cmd_recap():
    """Our own mid-call template. Needs it to be approved first."""
    if not _guard():
        return 1
    print(f"{INFO} using our template: {settings.wa_tpl_midcall} "
          f"({settings.wa_template_lang}) - must be APPROVED in WhatsApp Manager")
    return _run(f"template {settings.wa_tpl_midcall} (3 variables, no media)",
                lambda: whatsapp.send_template(
                    settings.allowed_destination, settings.wa_tpl_midcall,
                    body_params=["custom t-shirts, around 50 designs",
                                 "one lakh", "within a month"],
                    lang=settings.wa_template_lang))


def cmd_media():
    if not _guard():
        return 1
    if not settings.wa_architecture_url:
        print(f"{BAD} WHATSAPP_ARCHITECTURE_IMAGE_URL not set")
        return 1
    return _run(f"template {settings.wa_tpl_followup} + image header",
                lambda: whatsapp.send_template(
                    settings.allowed_destination, settings.wa_tpl_followup,
                    body_params=["the custom clothing business",
                                 "around 50 to 100 designs",
                                 "within a month",
                                 "payments, delivery tracking and WhatsApp orders",
                                 "around 1,000 to 2,000 US dollars"],
                    header={"type": "image", "link": settings.wa_architecture_url},
                    lang=settings.wa_template_lang))


def cmd_resume():
    if not _guard():
        return 1
    if not settings.wa_resume_url:
        print(f"{BAD} WHATSAPP_RESUME_URL not set")
        return 1
    return _run(f"template {settings.wa_tpl_resume} + document header",
                lambda: whatsapp.send_template(
                    settings.allowed_destination, settings.wa_tpl_resume,
                    body_params=["(demo url pending)", "(repo url pending)", "(note url pending)"],
                    header={"type": "document", "link": settings.wa_resume_url,
                            "filename": "resume.pdf"},
                    lang=settings.wa_template_lang))


COMMANDS = {"check": cmd_check, "hello": cmd_hello, "recap": cmd_recap,
            "media": cmd_media, "resume": cmd_resume}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    sys.exit(COMMANDS[cmd]())
