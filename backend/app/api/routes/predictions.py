from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.organization import Organization
from app.models.hackathon import Hackathon
from app.services.database import database_operation
from app.api.deps import require_data_scientist
from app.services.prediction_policy import baseline_evaluation

from app.schemas.prediction import PredictionRequest
from ai.prediction_model import predict_next_hackathon as baseline_predict
from ai.neural_prediction_model import predict_next_hackathon as neural_predict
from ai.discovery_history import export_observations
from ai.temporal_prediction import evaluate, load_review, readiness

router = APIRouter(
    prefix="/predictions",
    tags=["Predictions"]
)


def _baseline_forecast(organization, dates):
    try:
        return baseline_predict(organization=organization, historical_dates=dates)
    except (ValueError, OverflowError):
        return {"organization": organization, "predicted_date": None, "confidence": 0.0,
                "reasoning": "History cannot support a date range within supported calendar bounds."}


def _catalog_evaluation(db):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with database_operation(db):
        rows = db.execute(select(Organization.id, Organization.name, Hackathon.start_date,
                                 Hackathon.title, Hackathon.url)
            .outerjoin(Hackathon, (Hackathon.organization_id == Organization.id)
                       & (Hackathon.start_date < now)).order_by(Organization.id, Hackathon.start_date)).all()
    groups = {}
    for org_id, name, started, title, url in rows:
        group = groups.setdefault(org_id, {"name": name, "dates": set(), "evidence": []})
        if started is not None:
            group["dates"].add(started.date().isoformat())
            group["evidence"].append({"date": started.date().isoformat(), "title": title, "url": url})
    result = []
    for org_id, group in groups.items():
        dates = sorted(group["dates"])
        forecast = _baseline_forecast(group["name"], dates)
        evaluated = baseline_evaluation(forecast, dates, now.replace(tzinfo=timezone.utc))
        result.append({**evaluated, "organization_id": org_id,
                       "model": "baseline", "confidence_kind": "heuristic", "confirmed": False,
                       "evidence": group["evidence"][-10:]})
    return result


@router.get("/catalog")
def catalog_predictions(db: Session = Depends(get_db)):
    rows = _catalog_evaluation(db)
    return {"message": "Only eligible, calibrated and promoted predictions are public",
            "data": [row for row in rows if row["public_eligible"]],
            "policy": {"public_threshold": 0.40,
                       "reason": "The baseline is not calibrated or promoted; forecasts remain internal."}}


@router.get("/evaluation", dependencies=[Depends(require_data_scientist)])
def evaluation_predictions(db: Session = Depends(get_db)):
    return {"message": "Internal baseline evaluation", "data": _catalog_evaluation(db)}


def _temporal_report(db):
    with database_operation(db):
        observations = export_observations(db)
        organizations = dict(db.execute(select(Organization.id, Organization.name)).all())
        observations = [{**row, 'snapshot': {**row['snapshot'],
            'organization': organizations.get(row['snapshot'].get('organization_id'))}} for row in observations]
    review, _ = load_review()
    return evaluate(observations, review, datetime.now(timezone.utc))


@router.get('/readiness')
def prediction_readiness(db: Session = Depends(get_db)):
    return {'data': readiness(_temporal_report(db))}


@router.get('/research', dependencies=[Depends(require_data_scientist)])
def temporal_research(db: Session = Depends(get_db)):
    return {'message': 'Observation-aware research; no publication approval', 'data': _temporal_report(db)}


@router.get("/")
def prediction_status():
    return {
        "message": "Prediction API is ready",
        "models": ["baseline", "neural"]
    }


@router.post("/baseline", dependencies=[Depends(require_data_scientist)])
def baseline_prediction(request: PredictionRequest):
    forecast = _baseline_forecast(request.organization, request.historical_dates)
    return baseline_evaluation(forecast, request.historical_dates)


@router.post("/neural", dependencies=[Depends(require_data_scientist)])
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
