from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.organization import Organization
from app.models.hackathon import Hackathon
from app.services.database import database_operation

from app.schemas.prediction import PredictionRequest
from ai.prediction_model import predict_next_hackathon as baseline_predict
from ai.neural_prediction_model import predict_next_hackathon as neural_predict

router = APIRouter(
    prefix="/predictions",
    tags=["Predictions"]
)


@router.get("/catalog")
def catalog_predictions(db: Session = Depends(get_db)):
    """Baseline recurrence forecasts from distinct past dates in the catalog."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with database_operation(db):
        rows = db.execute(select(Organization.id, Organization.name, Hackathon.start_date)
            .outerjoin(Hackathon, (Hackathon.organization_id == Organization.id)
                       & (Hackathon.start_date < now)).order_by(Organization.id, Hackathon.start_date)).all()
    groups = {}
    for org_id, name, started in rows:
        group = groups.setdefault(org_id, {"name": name, "dates": set()})
        if started is not None:
            group["dates"].add(started.date().isoformat())
    result = []
    for org_id, group in groups.items():
        dates = sorted(group["dates"])
        forecast = baseline_predict(group["name"], dates)
        # Repeat the model's measured interval to find the next future cycle.
        if forecast["predicted_date"]:
            predicted = datetime.strptime(forecast["predicted_date"], "%Y-%m-%d")
            latest = datetime.strptime(dates[-1], "%Y-%m-%d")
            interval = (predicted - latest).days
            if interval > 0 and predicted.date() <= now.date():
                try:
                    predicted += timedelta(days=((now.date() - predicted.date()).days // interval + 1) * interval)
                    forecast["predicted_date"] = predicted.date().isoformat()
                    forecast["reasoning"] += " Recurrence projected to the next future cycle."
                except OverflowError:
                    forecast["predicted_date"] = None
                    forecast["reasoning"] = "Estimated date exceeds the supported date range."
        result.append({**forecast, "organization_id": org_id, "historical_events": len(dates),
                       "model": "baseline", "confidence_kind": "heuristic"})
    return {"message": "Catalog predictions fetched", "data": result}


@router.get("/")
def prediction_status():
    return {
        "message": "Prediction API is ready",
        "models": ["baseline", "neural"]
    }


@router.post("/baseline")
def baseline_prediction(request: PredictionRequest):
    return baseline_predict(
        organization=request.organization,
        historical_dates=request.historical_dates
    )


@router.post("/neural")
def neural_prediction(request: PredictionRequest):
    try:
        return neural_predict(
            organization=request.organization,
            historical_dates=request.historical_dates
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Neural network model has not been trained yet."
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
