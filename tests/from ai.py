from ai.followup_questions import build_followup_questions


def test_shipping_missing_order_number():
    followups = build_followup_questions(
        missing_information={
            "items": [{"key": "order_number", "severity": "blocking"}]
        },
        intent={"primary": "shipping", "confidence": 0.9},
        mode="assist",
        draft_text="",
    )

    assert len(followups) == 1
    assert followups[0]["key"] == "order_number"


def test_no_missing_info_produces_no_followups():
    followups = build_followup_questions(
        missing_information={"items": []},
        intent={"primary": "diagnostic", "confidence": 0.9},
        mode="assist",
        draft_text="",
    )

    assert followups == []
