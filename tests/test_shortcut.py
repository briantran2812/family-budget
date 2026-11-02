"""Structure of the generated iPhone Shortcut (signing and iOS import are checked by hand, phone/README.md D)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "phone"))
import make_shortcut  # noqa: E402


def test_variables_point_at_earlier_actions():
    actions = make_shortcut.build()["WFWorkflowActions"]
    seen = set()

    def refs(v):
        if isinstance(v, dict):
            if v.get("Type") == "ActionOutput":
                yield v["OutputUUID"]
            for x in v.values():
                yield from refs(x)
        elif isinstance(v, list):
            for x in v:
                yield from refs(x)
    for a in actions:
        params = a["WFWorkflowActionParameters"]
        for r in refs({k: v for k, v in params.items() if k != "UUID"}):
            assert r in seen, f"{a['WFWorkflowActionIdentifier']} uses a variable from a later or missing action"
        seen.add(params["UUID"])


def test_text_fields_use_token_strings():
    """Text parameters given a bare attachment arrive empty on iOS: description, account and device were blank."""
    for a in make_shortcut.build()["WFWorkflowActions"]:
        if a["WFWorkflowActionIdentifier"] == "is.workflow.actions.urlencode":
            assert a["WFWorkflowActionParameters"]["WFInput"]["WFSerializationType"] == "WFTextTokenString"


def test_url_carries_every_field():
    send = next(a for a in make_shortcut.build()["WFWorkflowActions"]
                if a["WFWorkflowActionIdentifier"] == "is.workflow.actions.downloadurl")
    url = send["WFWorkflowActionParameters"]["WFURL"]["Value"]
    assert url["string"].replace(make_shortcut.OBJ, "{}") == "{}&a=add&so={}&d={}&t={}&n={}"
    assert len(url["attachmentsByRange"]) == 5
