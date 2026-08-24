from app.stance import stance_guidance, stance_label

def test_stance_guidance_is_role_specific():
    assert stance_label("buyer") == "买方"
    assert "买方" in stance_guidance("buyer")
    assert "卖方" in stance_guidance("seller")
    assert "不得假设" in stance_guidance("Auto")
