"""Build the iPhone Shortcut "Ghi chi tiêu" and sign it with macOS `shortcuts sign` so it can be AirDropped.

  python3 phone/make_shortcut.py              → phone/dist/Ghi chi tiêu.shortcut       (production, green)
  python3 phone/make_shortcut.py --env test   → phone/dist/Ghi chi tiêu TEST.shortcut  (TEST sheet, orange)

Both can sit side by side on one iPhone: each carries its own connection code (docs/DEPLOY.md).

The connection code is not in the file: Shortcuts asks for it when the shortcut is added (an import question).
"""
import argparse
import plistlib
import subprocess
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
# name on the iPhone, icon colour (Shortcuts palette: green / orange)
ENVS = {"production": ("Ghi chi tiêu", 4292093695), "test": ("Ghi chi tiêu TEST", 4271458815)}


def out_path(env: str = "production") -> Path:
    return HERE / "dist" / f"{ENVS[env][0]}.shortcut"  # iOS names the shortcut after the file
ACCOUNTS = ["Tiền mặt", "Thẻ Visa", "Chuyển khoản", "Ví MoMo"]  # editable on the phone; matched to card statements
AUTO = "✨ Tự động"  # as in the app's entry form; not a category name, so the Mac falls back to its keywords
OBJ = "\ufffc"  # where a variable sits inside a text field


def ref(action: dict) -> dict:
    return {"OutputName": action["name"], "OutputUUID": action["params"]["UUID"], "Type": "ActionOutput"}


def attachment(action: dict) -> dict:
    return {"Value": ref(action), "WFSerializationType": "WFTextTokenAttachment"}


def tokens(*parts) -> dict:
    """Text with variables: tokens("abc", action, "def") → WFTextTokenString."""
    text, ranges = "", {}
    for part in parts:
        if isinstance(part, str):
            text += part
        else:
            ranges[f"{{{len(text.encode('utf-16-le')) // 2}, 1}}"] = ref(part)
            text += OBJ
    return {"Value": {"string": text, "attachmentsByRange": ranges}, "WFSerializationType": "WFTextTokenString"}


def action(identifier: str, name: str, **params) -> dict:
    return {"id": identifier, "name": name, "params": {"UUID": str(uuid.uuid4()).upper(), **params}}


def categories() -> list[str]:
    """Same choices, same order as the app's entry form; income categories last, so picking one records money in."""
    sys.path.insert(0, str(HERE.parent))
    import db
    spend = [f"{icon} {name}" for name, kind, icon, _ in db.DEFAULT_CATEGORIES if kind == "expense"]
    earn = [f"{icon} {name}" for name, kind, icon, _ in db.DEFAULT_CATEGORIES if kind == "income"]
    return [AUTO, *spend, *earn]


def build(env: str = "production") -> dict:
    colour = ENVS[env][1]
    where = "" if env == "production" else " TEST"
    code = action("is.workflow.actions.gettext", "Text", WFTextActionText="")
    amount = action("is.workflow.actions.ask", "Provided Input", WFAskActionPrompt="Bao nhiêu tiền? (gõ đủ số, ví dụ 45000)",
                    WFInputType="Number", WFAskActionAllowsDecimalNumbers=False)
    # The number pad shows no thousands separators, so the next prompt repeats the amount formatted: a missing 0 shows.
    shown = action("is.workflow.actions.format.number", "Formatted Number", WFNumberFormatDecimalPlaces=0,
                   WFNumber=tokens(amount))
    desc = action("is.workflow.actions.ask", "Provided Input", WFAskActionPrompt=tokens(shown, " ₫ — chi cho gì?"),
                  WFInputType="Text")
    cats = action("is.workflow.actions.list", "List", WFItems=categories())
    cat = action("is.workflow.actions.choosefromlist", "Chosen Item", WFInput=attachment(cats),
                 WFChooseFromListActionPrompt="Hạng mục?")
    accounts = action("is.workflow.actions.list", "List", WFItems=ACCOUNTS)
    account = action("is.workflow.actions.choosefromlist", "Chosen Item", WFInput=attachment(accounts),
                     WFChooseFromListActionPrompt="Trả bằng?")
    device = action("is.workflow.actions.getdevicedetails", "Device Name", WFDeviceDetail="Device Name")
    cat_q = action("is.workflow.actions.urlencode", "URL Encoded Text", WFEncodeMode="Encode", WFInput=tokens(cat))
    # URL Encode takes a text field, so its input must be a WFTextTokenString; an attachment encodes to "" (seen on iOS).
    desc_q = action("is.workflow.actions.urlencode", "URL Encoded Text", WFEncodeMode="Encode", WFInput=tokens(desc))
    account_q = action("is.workflow.actions.urlencode", "URL Encoded Text", WFEncodeMode="Encode", WFInput=tokens(account))
    device_q = action("is.workflow.actions.urlencode", "URL Encoded Text", WFEncodeMode="Encode", WFInput=tokens(device))
    # GET, not POST: Apps Script answers with a 302 and a client that re-sends a POST as GET loses the body.
    send = action("is.workflow.actions.downloadurl", "Contents of URL", WFHTTPMethod="GET",
                  WFURL=tokens(code, "&a=add&so=", amount, "&d=", desc_q, "&t=", account_q, "&n=", device_q, "&c=", cat_q))
    notify = action("is.workflow.actions.notification", "Notification", WFNotificationActionTitle="Thu Chi Gia Đình" + where,
                    WFNotificationActionBody=tokens(send))
    steps = [code, amount, shown, desc, cats, cat, accounts, account, device, desc_q, account_q, device_q, cat_q, send, notify]
    return {
        "WFWorkflowActions": [{"WFWorkflowActionIdentifier": a["id"], "WFWorkflowActionParameters": a["params"]}
                              for a in steps],
        "WFWorkflowClientVersion": "2607.0.2",
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowIcon": {"WFWorkflowIconStartColor": colour, "WFWorkflowIconGlyphNumber": 59511},
        "WFWorkflowImportQuestions": [{
            "ActionIndex": 0, "Category": "Parameter", "ParameterKey": "WFTextActionText", "DefaultValue": "",
            "Text": f"Dán mã kết nối{where} (app trên Mac{where and ' của môi trường TEST'} → Cài đặt → iPhone → "
                    "Sao chép mã cho iPhone)"}],
        "WFWorkflowInputContentItemClasses": [],
        "WFWorkflowOutputContentItemClasses": [],
        "WFWorkflowTypes": [],
        "WFWorkflowHasShortcutInputVariables": False,
        "WFWorkflowHasOutputFallback": False,
        "WFQuickActionSurfaces": [],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--env", choices=ENVS, default="production")
    env = ap.parse_args().env
    out = out_path(env)
    out.parent.mkdir(exist_ok=True)
    out.unlink(missing_ok=True)  # a stale signed file must not pass for a fresh one
    unsigned = out.with_suffix(".unsigned.shortcut")
    unsigned.write_bytes(plistlib.dumps(build(env), fmt=plistlib.FMT_BINARY))
    r = subprocess.run(["shortcuts", "sign", "--mode", "anyone", "--input", str(unsigned), "--output", str(out)],
                       capture_output=True, text=True)
    if r.returncode or not out.exists():
        sys.exit(f"shortcuts sign failed (needs macOS 12+, signed in to iCloud, online):\n{r.stderr or r.stdout}")
    unsigned.unlink()
    print(f"✓ {out.relative_to(HERE.parent)} ({out.stat().st_size // 1024} KB) — AirDrop it to the iPhone")


if __name__ == "__main__":
    main()
