from __future__ import annotations

import os
import threading
import time
import uuid
from typing import Optional

import mlflow.pyfunc
import pandas as pd
from fastapi import FastAPI, BackgroundTasks, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MLFLOW_MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "real-estate-price-model")
MLFLOW_MODEL_ALIAS = os.getenv("MLFLOW_MODEL_ALIAS", "champion")

MLFLOW_S3_ENDPOINT_URL = os.getenv("MLFLOW_S3_ENDPOINT_URL", "http://minio:9000")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "mlops_real_estate")
POSTGRES_USER = os.getenv("POSTGRES_USER", "mlops_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "mlops_password")

DB_URI = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

os.environ["MLFLOW_S3_ENDPOINT_URL"] = MLFLOW_S3_ENDPOINT_URL
os.environ["AWS_ACCESS_KEY_ID"] = AWS_ACCESS_KEY_ID
os.environ["AWS_SECRET_ACCESS_KEY"] = AWS_SECRET_ACCESS_KEY

app = FastAPI(
    title="Real Estate Price Prediction API",
    description="API de inferencia para modelo de predicción de precios inmobiliarios usando MLflow.",
    version="1.0.0",
)

Instrumentator().instrument(app).expose(app)

# ─── Estado del modelo ────────────────────────────────────────────────────────

model = None
model_version = None
model_uri = f"models:/{MLFLOW_MODEL_NAME}@{MLFLOW_MODEL_ALIAS}"
model_lock = threading.Lock()


FEATURE_COLS = [
    "brokered_by", "bed", "bath", "acre_lot", "house_size",
    "zip_code", "col_07", "col_08", "col_09",
    "col_10", "col_11", "col_12", "col_13", "col_14",
    "col_15", "col_16", "col_17", "col_18", "col_19",
    "col_20", "col_21", "col_22", "col_23", "col_24",
    "col_25", "col_26", "col_27", "col_28", "col_29",
    "col_30", "col_31", "col_32", "col_33", "col_34",
    "col_35", "col_36", "col_37", "col_38", "col_39",
    "col_40", "col_41", "col_42", "col_43", "col_44",
    "col_45", "col_46", "col_47", "col_48", "col_49",
    "col_50", "col_51", "col_52", "col_53", "col_54",
]


# ─── Schemas ──────────────────────────────────────────────────────────────────

class PredictionRequest(BaseModel):
    brokered_by: int = Field(..., example=150)
    bed: int = Field(..., example=3)
    bath: int = Field(..., example=2)
    acre_lot: float = Field(..., example=100.0)
    house_size: float = Field(..., example=1500.0)
    zip_code: int = Field(..., example=180)
    col_07: int = Field(..., example=200)
    col_08: int = Field(..., example=100)
    col_09: float = Field(..., example=1000.0)
    col_10: int = Field(0, example=0)
    col_11: int = Field(0, example=0)
    col_12: int = Field(0, example=0)
    col_13: int = Field(0, example=0)
    col_14: int = Field(0, example=0)
    col_15: int = Field(0, example=0)
    col_16: int = Field(0, example=0)
    col_17: int = Field(0, example=0)
    col_18: int = Field(0, example=0)
    col_19: int = Field(0, example=0)
    col_20: int = Field(0, example=0)
    col_21: int = Field(0, example=0)
    col_22: int = Field(0, example=0)
    col_23: int = Field(0, example=0)
    col_24: int = Field(0, example=0)
    col_25: int = Field(0, example=0)
    col_26: int = Field(0, example=0)
    col_27: int = Field(0, example=0)
    col_28: int = Field(0, example=0)
    col_29: int = Field(0, example=0)
    col_30: int = Field(0, example=0)
    col_31: int = Field(0, example=0)
    col_32: int = Field(0, example=0)
    col_33: int = Field(0, example=0)
    col_34: int = Field(0, example=0)
    col_35: int = Field(0, example=0)
    col_36: int = Field(0, example=0)
    col_37: int = Field(0, example=0)
    col_38: int = Field(0, example=0)
    col_39: int = Field(0, example=0)
    col_40: int = Field(0, example=0)
    col_41: int = Field(0, example=0)
    col_42: int = Field(0, example=0)
    col_43: int = Field(0, example=0)
    col_44: int = Field(0, example=0)
    col_45: int = Field(0, example=0)
    col_46: int = Field(0, example=0)
    col_47: int = Field(0, example=0)
    col_48: int = Field(0, example=0)
    col_49: int = Field(0, example=0)
    col_50: int = Field(0, example=0)
    col_51: int = Field(0, example=0)
    col_52: int = Field(0, example=0)
    col_53: int = Field(0, example=0)
    col_54: int = Field(0, example=0)


class PredictionResponse(BaseModel):
    request_id: str
    prediction: float
    prediction_label: str
    model_name: str
    model_alias: str
    model_version: Optional[str]
    response_time_ms: float


class ModelReloadResponse(BaseModel):
    status: str
    model_version: Optional[str]
    message: str


# ─── Carga del modelo ─────────────────────────────────────────────────────────

def _load_model_from_mlflow() -> tuple:
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    from mlflow.tracking import MlflowClient
    client = MlflowClient()

    loaded_model = mlflow.pyfunc.load_model(model_uri)

    try:
        version_info = client.get_model_version_by_alias(MLFLOW_MODEL_NAME, MLFLOW_MODEL_ALIAS)
        version = version_info.version
    except Exception:
        version = None

    return loaded_model, version


@app.on_event("startup")
def load_model() -> None:
    global model, model_version
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    for attempt in range(5):
        try:
            with model_lock:
                model, model_version = _load_model_from_mlflow()
            print(f"Modelo cargado: {model_uri} versión {model_version}")
            return
        except Exception as e:
            print(f"Intento {attempt + 1}/5 fallido: {e}")
            time.sleep(10)

    print("No se pudo cargar el modelo al iniciar. La API arrancará sin modelo.")


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "model_uri": model_uri,
        "model_version": model_version,
    }


@app.get("/model/info")
def model_info() -> dict:
    return {
        "model_name": MLFLOW_MODEL_NAME,
        "model_alias": MLFLOW_MODEL_ALIAS,
        "model_uri": model_uri,
        "model_version": model_version,
    }


@app.post("/model/reload", response_model=ModelReloadResponse)
def reload_model() -> ModelReloadResponse:
    global model, model_version

    previous_version = model_version
    new_model = None
    new_version = None

    try:
        new_model, new_version = _load_model_from_mlflow()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo recargar el modelo desde MLflow: {e}"
        )

    with model_lock:
        model = new_model
        model_version = new_version

    message = (
        f"Modelo recargado exitosamente. "
        f"Versión anterior: {previous_version} → Nueva versión: {new_version}"
    )

    return ModelReloadResponse(
        status="reloaded",
        model_version=str(new_version),
        message=message,
    )


@app.post("/predict", response_model=PredictionResponse)
def predict(payload: PredictionRequest) -> PredictionResponse:
    if model is None:
        raise HTTPException(status_code=503, detail="El modelo no está cargado.")

    start_time = time.time()
    request_id = str(uuid.uuid4())

    input_data = payload.model_dump()
    input_df = pd.DataFrame([input_data])[FEATURE_COLS]

    with model_lock:
        prediction_raw = model.predict(input_df)

    predicted_price = float(prediction_raw[0])
    response_time_ms = round((time.time() - start_time) * 1000, 2)

    if predicted_price < 2500:
        label = "precio_bajo"
    elif predicted_price < 3000:
        label = "precio_medio"
    else:
        label = "precio_alto"

    log_inference(
        request_id=request_id,
        input_data=payload.model_dump_json(),
        prediction=predicted_price,
        response_time_ms=response_time_ms,
    )

    return PredictionResponse(
        request_id=request_id,
        prediction=predicted_price,
        prediction_label=label,
        model_name=MLFLOW_MODEL_NAME,
        model_alias=MLFLOW_MODEL_ALIAS,
        model_version=str(model_version) if model_version else None,
        response_time_ms=response_time_ms,
    )


def log_inference(
    request_id: str,
    input_data: str,
    prediction: float,
    response_time_ms: float,
) -> None:
    try:
        engine = create_engine(DB_URI)
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO raw.inference_logs (
                        request_id, input_data, prediction,
                        model_name, model_alias, model_version,
                        response_time_ms, status
                    )
                    VALUES (
                        :request_id,
                        CAST(:input_data AS JSONB),
                        :prediction,
                        :model_name,
                        :model_alias,
                        :model_version,
                        :response_time_ms,
                        'success'
                    )
                """),
                {
                    "request_id": request_id,
                    "input_data": input_data,
                    "prediction": prediction,
                    "model_name": MLFLOW_MODEL_NAME,
                    "model_alias": MLFLOW_MODEL_ALIAS,
                    "model_version": str(model_version) if model_version else None,
                    "response_time_ms": response_time_ms,
                },
            )
    except Exception as e:
        print(f"Error al registrar inferencia: {e}")