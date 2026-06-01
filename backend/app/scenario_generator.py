from __future__ import annotations

import itertools
import random
from typing import Any

SCENARIO_LIBRARY = {
    "intersection": {
        "traffic_density": ["low", "medium", "high"],
        "signal_state": ["green", "yellow", "red"],
        "weather": ["clear", "rain", "fog"],
    },
    "lane_merge": {
        "merge_side": ["left", "right"],
        "speed_delta_kph": [5, 15, 25],
        "gap_m": [8, 15, 30],
    },
    "pedestrian_crossing": {
        "pedestrian_count": [1, 2, 6],
        "occlusion": ["none", "parked_vehicle", "heavy_rain"],
        "crossing_style": ["zebra", "unmarked"],
    },
    "edge_case": {
        "sensor_dropout": ["none", "lidar_100ms", "camera_500ms"],
        "road_friction": [0.9, 0.6, 0.3],
        "unexpected_agent": ["none", "cyclist_wrong_way", "animal_crossing"],
    },
}


def generate_scenarios(
    scenario_type: str,
    count: int,
    seed: int | None = None,
    generated_from: str = "library",
) -> list[dict[str, Any]]:
    if scenario_type not in SCENARIO_LIBRARY:
        raise ValueError(f"Unknown scenario type: {scenario_type}")

    rng = random.Random(seed)
    options = SCENARIO_LIBRARY[scenario_type]
    keys = list(options.keys())

    cartesian = [dict(zip(keys, values)) for values in itertools.product(*options.values())]
    rng.shuffle(cartesian)

    selected = cartesian[:count]
    output: list[dict[str, Any]] = []
    for index, params in enumerate(selected, start=1):
        risk_score = _estimate_risk(scenario_type, params)
        output.append(
            {
                "name": f"{scenario_type.replace('_', '-')}-{index:03d}",
                "scenario_type": scenario_type,
                "risk_score": risk_score,
                "parameters": params,
                "generated_from": generated_from,
            }
        )
    return output


def _estimate_risk(scenario_type: str, params: dict[str, Any]) -> float:
    base_risk = {
        "intersection": 0.4,
        "lane_merge": 0.35,
        "pedestrian_crossing": 0.55,
        "edge_case": 0.65,
    }[scenario_type]

    variability = 0.0
    for value in params.values():
        if isinstance(value, (int, float)):
            variability += min(float(value) / 50.0, 0.25)
        elif isinstance(value, str) and value not in {"none", "clear", "low"}:
            variability += 0.08

    return round(min(base_risk + variability, 0.99), 2)
