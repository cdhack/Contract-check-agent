from app.depth import depth_guidance, depth_label, review_temperature, tool_rounds

def test_depth_policy_has_expected_rounds_and_temperature():
    assert depth_label("standard") == "标准审查"
    assert depth_label("deep") == "深度审查"
    assert tool_rounds("standard") == 2
    assert tool_rounds("deep") == 4
    assert review_temperature("standard", 0.1) == 0.1
    assert review_temperature("deep", 0.1) == 0.2
    assert review_temperature("deep", 0.8) == 0.3
    assert "逐项覆盖" in depth_guidance("deep")
