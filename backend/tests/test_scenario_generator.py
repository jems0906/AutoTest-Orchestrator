from app.scenario_generator import generate_scenarios


def test_generate_scenarios_has_expected_shape():
    scenarios = generate_scenarios("intersection", count=3, seed=123)

    assert len(scenarios) == 3
    assert scenarios[0]["scenario_type"] == "intersection"
    assert "parameters" in scenarios[0]
    assert 0.0 <= scenarios[0]["risk_score"] <= 1.0
