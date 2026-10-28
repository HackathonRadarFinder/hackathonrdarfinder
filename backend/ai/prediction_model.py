from datetime import datetime, timedelta
from statistics import mean, pstdev
from typing import List, Dict, Any


def predict_next_hackathon(
    organization: str,
    historical_dates: List[str]
) -> Dict[str, Any]:

    if not historical_dates:
        return {
            "organization": organization,
            "predicted_date": None,
            "confidence": 0.0,
            "reasoning": "No historical hackathon data available."
        }

    if len(historical_dates) < 2:
        return {
            "organization": organization,
            "predicted_date": None,
            "confidence": 0.20,
            "reasoning": "At least two historical events are required for prediction."
        }

    try:
        parsed_dates = sorted(
            datetime.strptime(date, "%Y-%m-%d")
            for date in historical_dates
        )
    except ValueError:
        return {
            "organization": organization,
            "predicted_date": None,
            "confidence": 0.0,
            "reasoning": "Invalid date format. Expected YYYY-MM-DD."
        }

    gaps = [
        (parsed_dates[i] - parsed_dates[i - 1]).days
        for i in range(1, len(parsed_dates))
    ]

    average_gap = mean(gaps)

    predicted_date = (
        parsed_dates[-1] +
        timedelta(days=round(average_gap))
    )

    # Base confidence depends on amount of historical data.
    if len(historical_dates) == 2:
        base_confidence = 0.40
    elif len(historical_dates) == 3:
        base_confidence = 0.65
    elif len(historical_dates) == 4:
        base_confidence = 0.75
    else:
        base_confidence = 0.85

    # Reduce confidence when historical intervals vary significantly.
    if len(gaps) > 1:
        deviation = pstdev(gaps)

        if deviation <= 30:
            consistency_factor = 1.0
        elif deviation <= 90:
            consistency_factor = 0.85
        elif deviation <= 180:
            consistency_factor = 0.70
        else:
            consistency_factor = 0.50
    else:
        deviation = 0
        consistency_factor = 1.0

    confidence = base_confidence * consistency_factor

    confidence = round(
        max(0.0, min(confidence, 0.95)),
        2
    )

    return {
        "organization": organization,
        "predicted_date": predicted_date.strftime("%Y-%m-%d"),
        "confidence": confidence,
        "reasoning": (
            f"Prediction based on {len(historical_dates)} historical events "
            f"with an average interval of {round(average_gap)} days."
        )
    }


if __name__ == "__main__":

    sample_data = {
        "Google": [
            "2023-11-20",
            "2024-11-18",
            "2025-11-22"
        ],

        "Microsoft": [
            "2023-07-10",
            "2024-07-15",
            "2025-07-12"
        ],

        "Example Startup": [
            "2024-03-01",
            "2025-08-15"
        ]
    }

    for organization, dates in sample_data.items():
        result = predict_next_hackathon(
            organization,
            dates
        )

        print(result)
