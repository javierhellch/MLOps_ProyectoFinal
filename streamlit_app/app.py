from __future__ import annotations

import os

import pandas as pd
import psycopg2
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "mlops_real_estate")
POSTGRES_USER = os.getenv("POSTGRES_USER", "mlops_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "mlops_password")


def get_db_connection():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )


st.set_page_config(
    page_title="Real Estate Price Predictor",
    page_icon="🏠",
    layout="wide",
)

st.title("🏠 Real Estate Price Predictor")
st.write("Sistema MLOps para predicción de precios inmobiliarios.")

# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Estado del sistema")
    try:
        health_response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        health_data = health_response.json()

        if health_response.status_code == 200 and health_data.get("model_loaded"):
            st.success("API conectada ✅")
            st.write(f"Modelo: `{health_data.get('model_uri')}`")
            st.write(f"Versión: `{health_data.get('model_version')}`")
        else:
            st.warning("API disponible pero modelo no cargado ⚠️")
    except Exception as exc:
        st.error("No se pudo conectar con la API ❌")
        st.caption(str(exc))

    st.divider()

    if st.button("🔄 Recargar modelo desde MLflow"):
        try:
            reload_response = requests.post(f"{API_BASE_URL}/model/reload", timeout=30)
            if reload_response.status_code == 200:
                reload_data = reload_response.json()
                st.success(reload_data.get("message", "Modelo recargado."))
            else:
                st.error(f"Error al recargar: {reload_response.text}")
        except Exception as exc:
            st.error(f"Error: {exc}")

# ─── Tabs ─────────────────────────────────────────────────────────────────────

tab1, tab2 = st.tabs(["🔮 Inferencia", "📊 Historial de entrenamiento"])

# ─── Tab 1: Inferencia ────────────────────────────────────────────────────────

with tab1:
    st.header("Predicción de precio")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Características principales")
        brokered_by = st.number_input("Agencia (brokered_by)", min_value=0, max_value=360, value=150)
        bed = st.number_input("Habitaciones (bed)", min_value=0, max_value=42, value=3)
        bath = st.number_input("Baños (bath)", min_value=0, max_value=100, value=2)
        acre_lot = st.number_input("Terreno en acres (acre_lot)", min_value=0, max_value=1044, value=100)
        house_size = st.number_input("Tamaño de la casa (house_size)", min_value=0, max_value=5000, value=1500)

    with col2:
        st.subheader("Ubicación")
        zip_code = st.number_input("Código postal (zip_code)", min_value=92, max_value=254, value=180)
        col_07 = st.number_input("col_07", min_value=142, max_value=254, value=200)
        col_08 = st.number_input("col_08", min_value=0, max_value=243, value=100)
        col_09 = st.number_input("col_09", min_value=0, max_value=6000, value=1000)

    with col3:
        st.subheader("Categorías (one-hot)")
        st.caption("Selecciona una categoría activa")

        category_group1 = st.selectbox(
            "Grupo categoría 1 (col_10 a col_19)",
            options=["ninguna"] + [f"col_{i}" for i in range(10, 20)],
        )

        category_group2 = st.selectbox(
            "Grupo categoría 2 (col_20 a col_37)",
            options=["ninguna"] + [f"col_{i}" for i in range(20, 38)],
        )

        category_group3 = st.selectbox(
            "Grupo categoría 3 (col_42 a col_54)",
            options=["ninguna"] + [f"col_{i}" for i in range(42, 55)],
        )

    one_hot = {f"col_{i}": 0 for i in range(10, 55)}

    if category_group1 != "ninguna":
        one_hot[category_group1] = 1
    if category_group2 != "ninguna":
        one_hot[category_group2] = 1
    if category_group3 != "ninguna":
        one_hot[category_group3] = 1

    payload = {
        "brokered_by": brokered_by,
        "bed": bed,
        "bath": bath,
        "acre_lot": acre_lot,
        "house_size": house_size,
        "zip_code": zip_code,
        "col_07": col_07,
        "col_08": col_08,
        "col_09": col_09,
        **one_hot,
    }

    st.divider()

    if st.button("🏠 Generar predicción", type="primary"):
        try:
            response = requests.post(
                f"{API_BASE_URL}/predict",
                json=payload,
                timeout=20,
            )

            if response.status_code != 200:
                st.error(f"Error de la API: {response.text}")
            else:
                result = response.json()
                prediction = result["prediction"]
                label = result["prediction_label"]

                st.success("Predicción generada exitosamente")

                col_a, col_b, col_c = st.columns(3)

                with col_a:
                    st.metric("Precio estimado", f"{prediction:,.0f}")
                with col_b:
                    label_map = {
                        "precio_bajo": "🟢 Precio bajo (< 2500)",
                        "precio_medio": "🟡 Precio medio (2500-3000)",
                        "precio_alto": "🔴 Precio alto (> 3000)",
                    }
                    st.metric("Categoría", label_map.get(label, label))
                with col_c:
                    st.metric("Tiempo de respuesta", f"{result['response_time_ms']} ms")

                st.write(f"**Modelo:** `{result['model_name']}@{result['model_alias']}` versión `{result['model_version']}`")
                st.write(f"**Request ID:** `{result['request_id']}`")

        except Exception as exc:
            st.error(f"Error al conectar con la API: {exc}")

# ─── Tab 2: Historial ─────────────────────────────────────────────────────────

with tab2:
    st.header("Historial de entrenamiento y despliegue")
    st.caption("Resultado de cada batch procesado por el pipeline de Airflow.")

    try:
        conn = get_db_connection()
        query = """
            SELECT
                batch_number,
                batch_id,
                num_records,
                ingestion_timestamp,
                validation_status,
                training_decision,
                training_reason,
                training_executed,
                model_promoted,
                promotion_reason,
                run_id,
                model_version,
                mae_candidate,
                rmse_candidate,
                r2_candidate,
                mae_champion,
                rmse_champion,
                r2_champion
            FROM raw.batch_metadata
            ORDER BY ingestion_timestamp DESC
        """
        df = pd.read_sql(query, conn)
        conn.close()

        if df.empty:
            st.info("No hay batches procesados aún. Ejecuta el DAG de Airflow primero.")
        else:
            for _, row in df.iterrows():
                batch_num = row["batch_number"]
                trained = row["training_executed"]
                promoted = row["model_promoted"]

                if trained and promoted:
                    icon = "✅"
                    status_text = "Entrenado y promovido"
                elif trained and not promoted:
                    icon = "⚠️"
                    status_text = "Entrenado pero no promovido"
                else:
                    icon = "⏭️"
                    status_text = "No entrenado"

                with st.expander(f"{icon} Batch {batch_num} — {status_text} — {row['ingestion_timestamp']}"):
                    col_x, col_y = st.columns(2)

                    with col_x:
                        st.write("**Información del batch:**")
                        st.write(f"- Batch ID: `{row['batch_id']}`")
                        st.write(f"- Registros: {row['num_records']}")
                        st.write(f"- Estado validación: `{row['validation_status']}`")
                        st.write(f"- Decisión de entrenamiento: `{row['training_decision']}`")
                        st.write(f"- Razón: {row['training_reason']}")

                    with col_y:
                        if trained:
                            st.write("**Métricas del candidato:**")
                            st.write(f"- MAE: `{row['mae_candidate']:.4f}`" if row["mae_candidate"] else "- MAE: N/A")
                            st.write(f"- RMSE: `{row['rmse_candidate']:.4f}`" if row["rmse_candidate"] else "- RMSE: N/A")
                            st.write(f"- R²: `{row['r2_candidate']:.4f}`" if row["r2_candidate"] else "- R²: N/A")

                            if promoted:
                                st.success(f"**Promovido como champion** — versión `{row['model_version']}`")
                                st.write(f"- Run ID: `{row['run_id']}`")
                            else:
                                st.warning("**No promovido**")
                                st.write(f"- Razón: {row['promotion_reason']}")

                            if row["mae_champion"] and row["mae_candidate"]:
                                improvement = (row["mae_champion"] - row["mae_candidate"]) / row["mae_champion"] * 100
                                st.write(f"- Mejora MAE vs champion anterior: `{improvement:.1f}%`")
                        else:
                            st.info("No se ejecutó entrenamiento para este batch.")

    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")

    st.divider()

    st.subheader("Últimas inferencias")
    try:
        conn = get_db_connection()
        inference_query = """
            SELECT
                request_id,
                timestamp,
                prediction,
                model_name,
                model_alias,
                model_version,
                response_time_ms,
                status
            FROM raw.inference_logs
            ORDER BY timestamp DESC
            LIMIT 20
        """
        df_inferences = pd.read_sql(inference_query, conn)
        conn.close()

        if df_inferences.empty:
            st.info("No hay inferencias registradas aún.")
        else:
            st.dataframe(df_inferences, use_container_width=True)

    except Exception as e:
        st.error(f"Error al cargar inferencias: {e}")