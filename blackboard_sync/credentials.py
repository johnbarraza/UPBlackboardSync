"""Optional saved login, kept in the OS credential store.

Windows Credential Manager / macOS Keychain / Linux Secret Service via
``keyring``. Nothing is written to the config file or the logs. Saving is
opt-in from Settings; unticking the option deletes the entry.
"""

import json
import logging

logger = logging.getLogger(__name__)

SERVICE = "BlackboardSync"
_KEY = "login"


def load() -> tuple[str, str] | None:
    """(username, password) if saved, else None. Never raises."""
    try:
        import keyring
        raw = keyring.get_password(SERVICE, _KEY)
        if raw:
            data = json.loads(raw)
            return data["u"], data["p"]
    except Exception:
        logger.warning("Saved login could not be read from the OS keyring")
    return None


def save(username: str, password: str) -> bool:
    try:
        import keyring
        keyring.set_password(SERVICE, _KEY,
                             json.dumps({"u": username, "p": password}))
        return True
    except Exception:
        logger.warning("Login could not be saved to the OS keyring")
        return False


def clear() -> None:
    try:
        import keyring
        keyring.delete_password(SERVICE, _KEY)
    except Exception:
        pass  # nothing saved / no backend


def autofill_js(username: str, password: str) -> str:
    """JS that fills the login form and submits it; returns true if filled.

    Values go through json.dumps so quotes in the password can't break out
    of the string literal.
    """
    return """(function (u, p) {
  var pw = document.querySelector('input[type=password]');
  if (!pw) return false;
  var form = pw.form || document;
  var us = document.getElementById('user_id') ||
           form.querySelector('input[type=email],input[type=text]');
  function set(el, v) {
    el.value = v;
    el.dispatchEvent(new Event('input', {bubbles: true}));
    el.dispatchEvent(new Event('change', {bubbles: true}));
  }
  if (us) set(us, u);
  set(pw, p);
  var btn = document.getElementById('entry-login') ||
            form.querySelector('[type=submit]');
  if (btn) btn.click(); else if (pw.form) pw.form.submit();
  return true;
})(%s, %s)""" % (json.dumps(username), json.dumps(password))
