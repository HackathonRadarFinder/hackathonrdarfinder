from fastapi import APIRouter, HTTPException

from app.schemas.prediction import PredictionRequest
from ai.prediction_model import predict_next_hackathon as baseline_predict
from ai.neural_prediction_model import predict_next_hackathon as neural_predict

router = APIRouter(
    prefix="/predictions",
    tags=["Predictions"]
)


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
