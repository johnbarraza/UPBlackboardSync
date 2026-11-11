import json

from blackboard_sync import credentials


def test_autofill_js_escapes_values():
    js = credentials.autofill_js("ana", 'p"); alert(1); ("')
    # the password is embedded as a JSON string literal, not raw JS
    assert json.dumps('p"); alert(1); ("') in js
    assert js.rstrip().endswith('"ana", "p\\"); alert(1); (\\"")')


def test_save_load_clear_roundtrip(monkeypatch):
    import keyring
    store = {}
    monkeypatch.setattr(keyring, "set_password",
                        lambda s, k, v: store.__setitem__((s, k), v))
    monkeypatch.setattr(keyring, "get_password",
                        lambda s, k: store.get((s, k)))
    monkeypatch.setattr(keyring, "delete_password",
                        lambda s, k: store.pop((s, k)))

    assert credentials.load() is None
    assert credentials.save("ana", "secreto")
    assert credentials.load() == ("ana", "secreto")
    credentials.clear()
    assert credentials.load() is None
    credentials.clear()  # clearing twice is fine
