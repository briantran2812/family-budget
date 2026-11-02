"""Build the iPhone Shortcut "Ghi chi tiêu" and sign it with macOS `shortcuts sign` so it can be AirDropped.

  python3 phone/make_shortcut.py          → phone/dist/Ghi chi tiêu.shortcut

The connection code is not in the file: Shortcuts asks for it when the shortcut is added (an import question).
"""
import plistlib
import subprocess
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "dist" / "Ghi chi tiêu.shortcut"
ACCOUNTS = ["Tiền mặt", "Thẻ Visa", "Chuyển khoản", "Ví MoMo"]  # editable on the phone; matched to card statements
OBJ = "￼"  # where a variable sits inside a text field


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


def build() -> dict:
    code = action("is.workflow.actions.gettext", "Text", WFTextActionText="")
    amount = action("is.workflow.actions.ask", "Provided Input", WFAskActionPrompt="Bao nhiêu? (45 = 45.000 ₫)",
                    WFInputType="Number", WFAskActionAllowsDecimalNumbers=False)
    desc = action("is.workflow.actions.ask", "Provided Input", WFAskActionPrompt="Chi cho gì?", WFInputType="Text")
    accounts = action("is.workflow.actions.list", "List", WFItems=ACCOUNTS)
    account = action("is.workflow.actions.choosefromlist", "Chosen Item", WFInput=attachment(accounts),
                     WFChooseFromListActionPrompt="Trả bằng?")
    device = action("is.workflow.actions.getdevicedetails", "Device Name", WFDeviceDetail="Device Name")
    # URL Encode takes a text field, so its input must be a WFTextTokenString; an attachment encodes to "" (seen on iOS).
    desc_q = action("is.workflow.actions.urlencode", "URL Encoded Text", WFEncodeMode="Encode", WFInput=tokens(desc))
    account_q = action("is.workflow.actions.urlencode", "URL Encoded Text", WFEncodeMode="Encode", WFInput=tokens(account))
    device_q = action("is.workflow.actions.urlencode", "URL Encoded Text", WFEncodeMode="Encode", WFInput=tokens(device))
    # GET, not POST: Apps Script answers with a 302 and a client that re-sends a POST as GET loses the body.
    send = action("is.workflow.actions.downloadurl", "Contents of URL", WFHTTPMethod="GET",
                  WFURL=tokens(code, "&a=add&so=", amount, "&d=", desc_q, "&t=", account_q, "&n=", device_q))
    notify = action("is.workflow.actions.notification", "Notification", WFNotificationActionTitle="Thu Chi Gia Đình",
                    WFNotificationActionBody=tokens(send))
    steps = [code, amount, desc, accounts, account, device, desc_q, account_q, device_q, send, notify]
    return {
        "WFWorkflowActions": [{"WFWorkflowActionIdentifier": a["id"], "WFWorkflowActionParameters": a["params"]}
                              for a in steps],
        "WFWorkflowClientVersion": "2607.0.2",
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowIcon": {"WFWorkflowIconStartColor": 4292093695, "WFWorkflowIconGlyphNumber": 59511},
        "WFWorkflowImportQuestions": [{
            "ActionIndex": 0, "Category": "Parameter", "ParameterKey": "WFTextActionText", "DefaultValue": "",
            "Text": "Dán mã kết nối (app trên Mac → Cài đặt → iPhone → Sao chép mã cho iPhone)"}],
        "WFWorkflowInputContentItemClasses": [],
        "WFWorkflowOutputContentItemClasses": [],
        "WFWorkflowTypes": [],
        "WFWorkflowHasShortcutInputVariables": False,
        "WFWorkflowHasOutputFallback": False,
        "WFQuickActionSurfaces": [],
    }


def main() -> None:
    OUT.parent.mkdir(exist_ok=True)
    unsigned = OUT.with_suffix(".unsigned.shortcut")
    unsigned.write_bytes(plistlib.dumps(build(), fmt=plistlib.FMT_BINARY))
    r = subprocess.run(["shortcuts", "sign", "--mode", "anyone", "--input", str(unsigned), "--output", str(OUT)],
                       capture_output=True, text=True)
    if r.returncode or not OUT.exists():
        sys.exit(f"shortcuts sign failed (needs macOS 12+, signed in to iCloud, online):\n{r.stderr or r.stdout}")
    unsigned.unlink()
    print(f"✓ {OUT.relative_to(HERE.parent)} ({OUT.stat().st_size // 1024} KB) — AirDrop it to the iPhone")


if __name__ == "__main__":
    main()
