# Challenge Resolver

When logging into an old account from a new IP, Instagram often presents a "Suspicious Login Attempt" challenge requiring 6-digit Email or SMS verification.

InstaHarvest v2 provides built-in tools to resolve these automatically (`resolve()`) and headless integrations with Gmail to completely bypass manual intervention.

## Standard Callback Approach

The simplest method is providing a callback function during setup:

```python
from instaharvest_v2 import Instagram
from instaharvest_v2.exceptions import ChallengeRequired

def prompt_for_code(ctx):
    print(f"Instagram sent a code to {ctx.contact_point} ({ctx.challenge_type})")
    return input("Enter the 6-digit code here: ")

ig = Instagram(challenge_callback=prompt_for_code)

try:
    ig.login("my_username", "my_password")
except ChallengeRequired as e:
    # Raised if challenge resolution cannot be completed automatically
    print(f"Challenge intervention needed: {e.challenge_url}")
```

## Headless Auto-Resolver (Gmail IMAP)

If the account uses Gmail, you can use `EmailVerifier` with a **Gmail App Password** over IMAP (`imap.gmail.com:993`) to read the verification code automatically without interactive prompts.

### 1. Create a Gmail App Password

1. Enable 2-Step Verification on your Google Account.
2. Open [Google App Passwords](https://myaccount.google.com/apppasswords) and generate a 16-character app password.

### 2. Configure the Auto-Resolver

```python
from instaharvest_v2 import Instagram
from instaharvest_v2.email_verifier import EmailVerifier

# 1. Init IMAP verifier
verifier = EmailVerifier("you@gmail.com", "your-16-char-app-password")

def auto_gmail_resolve(ctx):
    return verifier.get_instagram_code(max_wait=60, poll_interval=5)

# 2. Bind to Instagram object
ig = Instagram(challenge_callback=auto_gmail_resolve)

# 3. Login
ig.login("my_user", "my_pass")
# If a challenge triggers, it polls Gmail IMAP for up to 60s,
# extracts the 6-digit code, and submits it automatically.
```

## Supported Challenge Types

The internal `ChallengeHandler` module parses and supports:

* `email` (Standard 6-digit email)
* `sms` (Standard 6-digit text)
* `consent` (Terms of Service updates — auto-accepted!)
* `platform` (App-based approval loops)

If a Challenge type is completely unsupported (like a visual CAPTCHA or facial scan), the library will immediately raise a hard `ChallengeRequired` exception stating manual app intervention is needed.
