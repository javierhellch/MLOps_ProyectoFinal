# MLOps Proyecto Final — Real Estate Price Pipeline

Proyecto académico de MLOps para construir un pipeline end-to-end de ingesta incremental, procesamiento, feature engineering, entrenamiento, registro, despliegue e inferencia de un modelo de predicción de precios inmobiliarios.

El stack está desplegado completamente en **Kubernetes** (Docker Desktop), con imágenes publicadas en DockerHub, CI/CD mediante **GitHub Actions**, y GitOps mediante **Argo CD**. El sistema consume datos desde una API externa por lotes y selecciona automáticamente el mejor modelo usando MAE como métrica de promoción.

---

## 1. Arquitectura general

![alt text](/images/Architecture.png)

```text
Developer (push a main)
        ↓
GitHub Actions — build multi-plataforma + push DockerHub
        ↓
Argo CD — detecta cambios en k8s/ y sincroniza el clúster
        ↓
Kubernetes (Docker Desktop)
        ↓
Data API (grupo 8)
        ↓
Airflow DAG — fetch_and_store_batch
        ↓
raw.real_estate_raw  ←→  raw.batch_metadata
        ↓
validate_schema → validate_data_quality → detect_new_categories → detect_data_drift
        ↓
preprocess_data
        ↓
clean.real_estate_clean
        ↓
decide_training (@task.branch)
        ↓                    ↓
train_candidate_model     skip_training
        ↓
evaluate → register → compare_with_production
        ↓
decide_promotion (@task.branch)
        ↓                 ↓
promote_model        reject_model
        ↓
MLflow Model Registry (@champion)
        ↓
MinIO artifact storage
        ↓
FastAPI /predict
        ↓
Streamlit / Locust
        ↓
raw.inference_logs
        ↓
Prometheus → Grafana
```

---

## 2. Flujo funcional

1. El desarrollador hace `push` a `main` — **GitHub Actions** construye y publica automáticamente las imágenes Docker en DockerHub en multi-plataforma (`linux/amd64` + `linux/arm64`).
2. **Argo CD** detecta el cambio en el directorio `k8s/` del repositorio y sincroniza automáticamente el estado del clúster de Kubernetes.
3. Airflow consume la Data API del grupo 8 e ingesta un batch de datos por ejecución.
4. Los datos crudos se almacenan en `raw.real_estate_raw` junto con metadatos en `raw.batch_metadata`.
5. Se valida el esquema del batch — solo requiere columnas esenciales (`price`, `brokered_by`, `bed`, `bath`, `house_size`).
6. Se valida la calidad de los datos (nulos, duplicados).
7. Se detectan nuevas categorías en columnas one-hot versus el histórico en `clean`.
8. Se detecta data drift en variables numéricas clave comparando con el histórico.
9. Los datos se preprocesan y almacenan en `clean.real_estate_clean`.
10. El DAG decide si entrenar según criterios: primer batch, drift detectado, nuevas categorías, o aumento de volumen ≥ 5%.
11. Si se entrena: se usa `GradientBoostingRegressor` y se registra el experimento en MLflow.
12. El candidato se compara contra el modelo `champion` actual usando MAE.
13. Si el candidato mejora el MAE en al menos 3%, se promueve como `champion`.
14. FastAPI carga dinámicamente el modelo `champion` desde MLflow al iniciar.
15. Streamlit consume FastAPI para generar predicciones visuales.
16. Locust ejecuta pruebas de carga sobre la API.
17. Cada inferencia se registra en `raw.inference_logs`.
18. Prometheus recoge métricas de la API desde `/metrics`. Grafana las visualiza.

---

## 3. Componentes en Kubernetes

| Componente | Tipo | Descripción | Puerto local |
|---|---|---|---:|
| github-actions | CI/CD externo | Construye y publica imágenes en DockerHub al hacer push a `main` | — |
| argocd | Deployment | GitOps — sincroniza `k8s/` del repositorio con el clúster | 8080 |
| postgres | StatefulSet | Base de datos principal, backend MLflow, metadata Airflow | 5432 |
| minio | StatefulSet | Object storage S3-compatible para artefactos MLflow | 9000 / 9001 |
| minio-init | Job | Crea el bucket `mlflow-artifacts` en MinIO | — |
| mlflow | Deployment | Tracking server y model registry | 5050 |
| airflow-init | Job | Migra la DB y crea el usuario admin de Airflow | — |
| airflow-webserver | Deployment | UI de Airflow | 8081 |
| airflow-scheduler | Deployment | Scheduler + executor local de Airflow | — |
| data-api | Deployment | API externa de datos del grupo 8 | 80 (interno) |
| api | Deployment | API de inferencia FastAPI | 8000 |
| streamlit | Deployment | Interfaz visual de inferencia | 8501 |
| locust | Deployment | Pruebas de carga | 8089 |
| prometheus | Deployment | Recolección de métricas de la API | 9090 |
| grafana | Deployment | Visualización de métricas | 3000 |

---

## 4. URLs locales

```text
Argo CD:    http://localhost:8080
Airflow:    http://localhost:8081
MLflow:     http://localhost:5050
MinIO:      http://localhost:9001
FastAPI:    http://localhost:8000/docs
Streamlit:  http://localhost:8501
Locust:     http://localhost:8089
Prometheus: http://localhost:9090
Grafana:    http://localhost:3000
```

---

## 5. Credenciales

### GitHub Actions (secretos del repositorio)
```text
DOCKERHUB_USERNAME: jchapadockerhub
DOCKERHUB_TOKEN:    <token de DockerHub>
```

### Argo CD
```text
Usuario:  admin
Password: <generada al instalar — ver sección 10.2>
```

### Airflow
```text
Usuario:  airflow
Password: airflow
```

### MinIO
```text
Usuario:  minioadmin
Password: minioadmin
```

### Grafana
```text
Usuario:  admin
Password: admin
```

---

## 6. Estructura del proyecto

```text
.
├── .github/
│   └── workflows/
│       └── build-and-push.yml       # GitHub Actions CI/CD
├── airflow/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── dags/
│       └── real_estate_pipeline.py  # DAG principal
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       └── main.py
├── database/
│   └── init/
│       ├── 00_create_airflow_db.sql
│       └── 01_create_schemas.sql
├── locust/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── locustfile.py
├── mlflow/
│   └── Dockerfile
├── streamlit_app/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py
├── k8s/
│   ├── namespace.yaml
│   ├── secrets/
│   │   └── secrets.yaml
│   ├── configmaps/
│   │   └── configmap.yaml
│   ├── postgres/
│   ├── minio/
│   ├── mlflow/
│   ├── airflow/
│   │   ├── configmap-dags.yaml      # DAG embebido en ConfigMap
│   │   ├── deployment.yaml
│   │   ├── init-job.yaml
│   │   └── service.yaml
│   ├── data-api/
│   ├── api/
│   ├── streamlit/
│   ├── locust/
│   ├── prometheus/
│   ├── grafana/
│   └── argocd/
│       └── application.yaml         # App de Argo CD
└── README.md
```

---

## 7. Variables de entorno (Kubernetes Secrets y ConfigMaps)

Las variables sensibles se gestionan como Secrets de Kubernetes y las no sensibles como ConfigMaps. No se usa `.env` en el despliegue final.

### Secrets principales (`k8s/secrets/secrets.yaml`)

```text
postgres-secret:
  postgres-user:      mlops_user
  postgres-password:  mlops_password
  postgres-db:        mlops_real_estate

minio-secret:
  minio-root-user:       minioadmin
  minio-root-password:   minioadmin
  aws-access-key-id:     minioadmin
  aws-secret-access-key: minioadmin

airflow-secret:
  airflow-db-user:        airflow_user
  airflow-db-password:    airflow_password
  airflow-db:             airflow_db
  airflow-secret-key:     <clave-secreta>
  airflow-admin-user:     airflow
  airflow-admin-password: airflow
```

### ConfigMaps principales

```text
mlflow-config:
  MLFLOW_TRACKING_URI:    http://mlflow:5000
  MLFLOW_EXPERIMENT_NAME: real-estate-price-prediction
  MLFLOW_MODEL_NAME:      real-estate-price-model
  MLFLOW_MODEL_ALIAS:     champion
  MLFLOW_S3_ENDPOINT_URL: http://minio:9000

airflow-config:
  AIRFLOW__CORE__EXECUTOR:      LocalExecutor
  AIRFLOW__CORE__LOAD_EXAMPLES: "false"
  GROUP_NUMBER:                 "8"
  DATA_API_URL:                 http://data-api:80
```

---

## 8. Imágenes Docker publicadas en DockerHub

| Imagen | Tag |
|---|---|
| `jchapadockerhub/mlops-pf-airflow` | `latest` |
| `jchapadockerhub/mlops-pf-api` | `latest` |
| `jchapadockerhub/mlops-pf-streamlit` | `latest` |
| `jchapadockerhub/mlops-pf-locust` | `latest` |
| `jchapadockerhub/mlops-pf-mlflow` | `latest` |

Las imágenes se construyen automáticamente al hacer `push` a `main` mediante GitHub Actions. El workflow construye en multi-plataforma (`linux/amd64` + `linux/arm64`).

![alt text](/images/dockerhub.png)

---

## 9. Requisitos previos

- Docker Desktop con Kubernetes habilitado
- `kubectl` apuntando al contexto `docker-desktop`
- Argo CD instalado en el clúster (ver sección 10.2)
- Acceso a internet para descargar imágenes desde DockerHub

Verificar:

```bash
kubectl config current-context   # debe ser docker-desktop
kubectl get nodes                 # debe mostrar docker-desktop Ready
```

![alt text](/images/context.png)

---

## 10. Despliegue desde cero en Kubernetes

### 10.1. Clonar el repositorio

```bash
git clone https://github.com/javierhellch/MLOps_ProyectoFinal.git
cd MLOps_ProyectoFinal
```

### 10.2. Instalar Argo CD (primera vez)

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=available deployment/argocd-server -n argocd --timeout=180s
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

![alt text](/images/argo_pods.png)

Obtener la contraseña inicial:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

![alt text](/images/argo_pass.png)

Acceder en http://localhost:8080 con usuario `admin`.

![alt text](/images/argo1.png)

### 10.3. Aplicar manifiestos base

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets/
kubectl apply -f k8s/configmaps/
```

![alt text](/images/secrets_configmaps.png)

### 10.4. Levantar infraestructura base

```bash
kubectl apply -f k8s/postgres/
kubectl apply -f k8s/minio/
kubectl wait --for=condition=ready pod -l app=postgres -n mlops-pf --timeout=120s
kubectl wait --for=condition=complete job/minio-init -n mlops-pf --timeout=60s
kubectl apply -f k8s/mlflow/
kubectl wait --for=condition=ready pod -l app=mlflow -n mlops-pf --timeout=120s
```

![alt text](/images/base_services.png)

### 10.5. Inicializar y levantar Airflow

```bash
kubectl apply -f k8s/airflow/
kubectl wait --for=condition=complete job/airflow-init -n mlops-pf --timeout=180s
kubectl wait --for=condition=ready pod -l app=airflow-webserver -n mlops-pf --timeout=120s
kubectl wait --for=condition=ready pod -l app=airflow-scheduler -n mlops-pf --timeout=120s
```

![alt text](/images/airflow_service.png)

### 10.6. Levantar Data API

```bash
kubectl apply -f k8s/data-api/
kubectl wait --for=condition=ready pod -l app=data-api -n mlops-pf --timeout=120s
```

![alt text](/images/dataapi_service.png)

### 10.7. Configurar Argo CD

```bash
kubectl apply -f k8s/argocd/application.yaml
```
![alt text](/images/argo_config.png)

Desde la UI de Argo CD (http://localhost:8080), verificar que la app `mlops-pf` aparece como **Synced + Healthy**.

![alt text](/images/argo.png)

A partir de este punto, cualquier `push` a `main` que modifique el directorio `k8s/` será detectado por Argo CD y aplicado automáticamente al clúster.

### 10.8. Ejecutar el DAG de entrenamiento

1. Abrir Airflow en http://localhost:8081
2. Iniciar sesión con `airflow / airflow`
3. Buscar el DAG `real_estate_pipeline`
4. Activarlo si está pausado
5. Presionar **Trigger DAG**
6. Esperar que todas las tareas queden en verde

![alt text](/images/airflow_dag.png)

Primera ejecución

![alt text](/images/airflow_run1.png)

![alt text](/images/postgres_run1.png)

Segunda ejecución

![alt text](/images/airflow_run2.png)

Tercera ejecución

![alt text](/images/airflow_run3.png)

Verificar en PostgreSQL:

```bash
kubectl exec -n mlops-pf $(kubectl get pod -n mlops-pf -l app=postgres -o jsonpath="{.items[0].metadata.name}") -- \
  psql -U mlops_user -d mlops_real_estate -c \
  "SELECT batch_number, num_records, training_decision, training_reason, training_executed, model_promoted FROM raw.batch_metadata ORDER BY ingestion_timestamp DESC LIMIT 5;"
```

![alt text](/images/postgres_run1.png)

![alt text](/images/postgres_run2.png)

![alt text](/images/postgres_run3.png)

Ejecutar el DAG **al menos 2 veces** para tener datos históricos y evidenciar la lógica de promoción.

### 10.9. Reiniciar datos entre ejecuciones

Si la API retorna 400 (batches agotados), reiniciar desde dentro del clúster:

```bash
kubectl exec -n mlops-pf $(kubectl get pod -n mlops-pf -l app=airflow-scheduler -o jsonpath="{.items[0].metadata.name}") -- \
  python3 -c "import requests; r = requests.get('http://data-api:80/restart_data_generation?group_number=8'); print(r.status_code)"
```

Para limpiar datos y empezar desde cero:

```bash
kubectl exec -n mlops-pf $(kubectl get pod -n mlops-pf -l app=postgres -o jsonpath="{.items[0].metadata.name}") -- \
  psql -U mlops_user -d mlops_real_estate -c "
  DELETE FROM raw.real_estate_raw;
  DELETE FROM raw.batch_metadata;
  DELETE FROM clean.real_estate_clean;
  DELETE FROM monitoring.data_drift;
  DELETE FROM monitoring.model_training_runs;
  "
```

### 10.10. Levantar servicios de inferencia y observabilidad

Una vez exista un modelo `champion` en MLflow:

![alt text](/images/mlflow_champion.png)

```bash
kubectl apply -f k8s/api/
kubectl apply -f k8s/streamlit/
kubectl apply -f k8s/locust/
kubectl apply -f k8s/prometheus/
kubectl apply -f k8s/grafana/
```

![alt text](/images/inferenceapi_and_OServices.png)

Si la API arrancó antes de que existiera el modelo champion, reiniciarla:

```bash
kubectl rollout restart deployment/api -n mlops-pf
```

---

## 11. GitHub Actions — CI/CD

El workflow `.github/workflows/build-and-push.yml` se activa automáticamente en cada `push` a `main`.

El workflow tiene dos jobs:

**Job 1 — `build-app-images`**: construye y publica en DockerHub las imágenes de airflow, api, streamlit y locust en multi-plataforma (`linux/amd64,linux/arm64`).

**Job 2 — `build-mlflow-image`**: construye y publica la imagen de MLflow por separado para evitar timeouts en GitHub Actions.

Secretos requeridos en el repositorio:

```text
DOCKERHUB_USERNAME
DOCKERHUB_TOKEN
```

![alt text](/images/dockerhub_token.png)

Verificar el estado de los workflows en:

```text
https://github.com/javierhellch/MLOps_ProyectoFinal/actions
```

![alt text](/images/github_actions.png)

---

## 12. Argo CD — GitOps

Argo CD sincroniza el estado del clúster con el directorio `k8s/` del repositorio `main`.

Verificar el estado de sincronización:

```bash
kubectl get application -n argocd
```

![alt text](/images/argo_status.png)

Forzar sincronización manual (de ser necesario):

```bash
kubectl -n argocd patch application mlops-pf --type merge \
  -p '{"operation":{"initiatedBy":{"username":"admin"},"sync":{"revision":"HEAD"}}}'
```

Cualquier cambio en `k8s/` pusheado a `main` es detectado y aplicado automáticamente por Argo CD.

---

## 13. DAG `real_estate_pipeline` — Detalle de tareas

El DAG tiene 16 tareas organizadas en el siguiente flujo:

```text
start
  ↓
fetch_and_store_batch      — Consume API, inserta RAW en chunks de 500
  ↓
validate_schema            — Verifica columnas esenciales (price, bed, bath, house_size, brokered_by)
  ↓
validate_data_quality      — Verifica nulos y duplicados (umbral: 50%)
  ↓
detect_new_categories      — Detecta nuevas categorías en columnas one-hot vs histórico
  ↓
detect_data_drift          — Calcula drift en variables numéricas (umbral: 0.2)
  ↓
preprocess_data            — Limpieza, flags de anomalías, inserción en clean en chunks
  ↓
decide_training            — @task.branch — decide si entrenar o saltar
  ↓              ↓
train_candidate  skip_training
  ↓
evaluate_candidate_model
  ↓
register_candidate_in_mlflow
  ↓
compare_with_production
  ↓
decide_promotion           — @task.branch — compara MAE candidato vs champion
  ↓            ↓
promote_model  reject_model
  ↓
notify_from_promote / notify_from_reject / notify_from_skip
  ↓
end
```

### Criterios para entrenar

| Condición | Descripción |
|---|---|
| Primer batch | No hay datos históricos en `clean` |
| Drift detectado | Al menos una variable numérica supera el umbral de 0.2 |
| Nuevas categorías | Aparecen valores nuevos en columnas one-hot |
| Aumento de volumen | Los nuevos registros representan ≥ 5% del histórico |

### Criterio de promoción

El modelo candidato se promueve como `champion` si su MAE mejora **al menos 3%** respecto al champion actual. Si no hay champion previo, el primer modelo se promueve automáticamente.

---

![alt text](/images/airflow_dagmap.png)

## 14. Data API — Fuente de datos

La Data API (`cristiandiaz13/mlops-puj:data-api-pf-v1`) se despliega en el clúster como Deployment. Devuelve batches de datos inmobiliarios en formato variable.

Endpoints relevantes:

```text
GET /data?group_number=8                     — Obtiene el siguiente batch
GET /restart_data_generation?group_number=8  — Reinicia el contador (10 batches disponibles)
```

El DAG maneja automáticamente el código 400 (sin más batches) retornando un skip graceful.

Importante: el reinicio debe hacerse desde **dentro del clúster** (no desde localhost), ya que la API mantiene estado por instancia.

![alt text](/images/data_api.png)

---

## 15. Validación del sistema

### 15.1. Verificar pods

```bash
kubectl get pods -n mlops-pf
```

![alt text](/images/pods_ok1.png)

### 15.2. Verificar datos en PostgreSQL

Conteo por capa:

```bash
kubectl exec -n mlops-pf $(kubectl get pod -n mlops-pf -l app=postgres -o jsonpath="{.items[0].metadata.name}") -- \
  psql -U mlops_user -d mlops_real_estate -c "
  SELECT 'raw' AS capa, COUNT(*) FROM raw.real_estate_raw
  UNION ALL
  SELECT 'clean', COUNT(*) FROM clean.real_estate_clean
  UNION ALL
  SELECT 'inference_logs', COUNT(*) FROM raw.inference_logs;"
```

![alt text](/images/postgres_1.png)

Historial de batches:

```bash
kubectl exec -n mlops-pf $(kubectl get pod -n mlops-pf -l app=postgres -o jsonpath="{.items[0].metadata.name}") -- \
  psql -U mlops_user -d mlops_real_estate -c \
  "SELECT batch_number, num_records, training_decision, training_reason, training_executed, model_promoted FROM raw.batch_metadata ORDER BY ingestion_timestamp DESC LIMIT 10;"
```

![alt text](/images/postgres_historial.png)

### 15.3. Validar MLflow

Abrir http://localhost:5050 y verificar:

1. Existe el experimento `real-estate-price-prediction`
2. Hay al menos un run con métricas: `mae`, `rmse`, `r2`, `mape`
3. En **Models** existe `real-estate-price-model` con alias `@champion`

![alt text](/images/mlflow_metrics.png)

![alt text](/images/mlflow_champion2.png)

### 15.4. Validar MinIO

Abrir http://localhost:9001 con `minioadmin / minioadmin`.

Verificar que existe el bucket `mlflow-artifacts` con artefactos de MLflow (`MLmodel`, `model.pkl`, etc.).

![alt text](/images/minio_console.png)

### 15.5. Validar FastAPI

![alt text](/images/api_inference.png)

Health check:

```bash
curl http://localhost:8000/health
```

Ejemplo de respuesta esperada:

```json
{
  "status": "ok",
  "model_loaded": true,
  "model_uri": "models:/real-estate-price-model@champion",
  "model_version": "1"
}
```

![alt text](/images/api_healthcheck.png)

Predicción de prueba:

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "brokered_by": 50000,
    "bed": 3,
    "bath": 2,
    "acre_lot": 0.25,
    "house_size": 1500,
    "zip_code": 99206
  }'
```

![alt text](/images/api_inferencetest.png)

Verificar log de inferencia:

```bash
kubectl exec -n mlops-pf $(kubectl get pod -n mlops-pf -l app=postgres -o jsonpath="{.items[0].metadata.name}") -- \
  psql -U mlops_user -d mlops_real_estate -c \
  "SELECT request_id, prediction, model_version, response_time_ms, timestamp FROM raw.inference_logs ORDER BY timestamp DESC LIMIT 5;"
```

![alt text](/images/api_inferencelog.png)

### 15.6. Validar Streamlit

Abrir http://localhost:8501 y verificar:

1. En la barra lateral aparece `API conectada ✅`
2. El modelo mostrado es `models:/real-estate-price-model@champion`
3. Completar los campos y presionar **Predecir precio**
4. La pestaña **Historial de entrenamiento** muestra los batches procesados con su decisión

![alt text](/images/streamlit_home.png)

Prueba de inferencia

![alt text](/images/streamlit_inferencetest.png)

Historial de inferencia

![alt text](/images/streamlit_historial.png)

### 15.7. Validar Locust

Abrir http://localhost:8089.

Configuración recomendada:

```text
Number of users: 10
Ramp up:         2
Host:            http://api:8000
```

![alt text](/images/locust_test1.png)

Ejecutar durante 1-2 minutos y verificar:

- Requests totales > 0
- Fails: 0%
- RPS, latencia promedio, p95 y p99

```bash
kubectl exec -n mlops-pf $(kubectl get pod -n mlops-pf -l app=postgres -o jsonpath="{.items[0].metadata.name}") -- \
  psql -U mlops_user -d mlops_real_estate -c "SELECT COUNT(*) FROM raw.inference_logs;"
```

![alt text](/images/locust_inferencelogs.png)

Estadísticas

![alt text](/images/locust_statistics.png)

Gráficos

![alt text](/images/locust_charts.png)

### 15.8. Validar Prometheus

Abrir http://localhost:9090 → Status → Targets.

El target `api` debe aparecer como **UP**.

![alt text](/images/prometheus_targets.png)

### 15.9. Validar Grafana

Abrir http://localhost:3000 con `admin / admin`.

El dashboard incluye: total de solicitudes, RPS, latencia promedio, p95, p99, tasa de error.

Durante la prueba de Locust, los paneles deben mostrar el aumento en tráfico y latencia en tiempo real.

![alt text](/images/grafana_dashboard.png)

### 15.10. Validar GitHub Actions

```text
https://github.com/javierhellch/MLOps_ProyectoFinal/actions
```

Verificar que el último workflow completó con estado **passed ✅** y que las imágenes están publicadas en DockerHub.

![alt text](/images/github_action1.png)

### 15.11. Validar Argo CD

```bash
kubectl get application -n argocd
```

La aplicación `mlops-pf` debe mostrar:

```text
STATUS: Synced   HEALTH: Healthy
```

![alt text](/images/argo.png)

---

## 16. Selección de modelo champion por MAE

El sistema no promueve el último modelo entrenado automáticamente.

La tarea `compare_with_production` recupera las métricas del modelo `champion` actual desde MLflow y las compara con el candidato. La tarea `decide_promotion` promueve solo si:

```text
(mae_champion - mae_candidato) / mae_champion × 100 ≥ 3%
```

Consultar historial de entrenamientos:

```bash
kubectl exec -n mlops-pf $(kubectl get pod -n mlops-pf -l app=postgres -o jsonpath="{.items[0].metadata.name}") -- \
  psql -U mlops_user -d mlops_real_estate -c \
  "SELECT run_id, model_version, mae, rmse, r2, promoted_to_champion, promotion_reason, created_at FROM monitoring.model_training_runs ORDER BY created_at DESC LIMIT 10;"
```

FastAPI siempre consulta dinámicamente:

```text
models:/real-estate-price-model@champion
```

---

## 17. Comandos de operación

### 17.1. Ver estado general

```bash
kubectl get pods -n mlops-pf
```

### 17.2. Reiniciar un deployment

```bash
kubectl rollout restart deployment/<nombre> -n mlops-pf
```

### 17.3. Ver logs de un servicio

```bash
kubectl logs -n mlops-pf -l app=<nombre> --tail=100
```

### 17.4. Verificar uso de recursos

```bash
kubectl top pods -n mlops-pf
kubectl describe node docker-desktop | grep -A5 "Allocated resources"
```

### 17.5. Forzar sync de Argo CD

```bash
kubectl -n argocd patch application mlops-pf --type merge \
  -p '{"operation":{"initiatedBy":{"username":"admin"},"sync":{"revision":"HEAD"}}}'
```

### 17.6. Logs del DAG en tiempo real

```bash
kubectl exec -n mlops-pf $(kubectl get pod -n mlops-pf -l app=airflow-scheduler -o jsonpath="{.items[0].metadata.name}") -- \
  bash -c "find /opt/airflow/logs -name '*.log' | grep attempt | sort -r | head -1 | xargs tail -f"
```

### 17.7. Reiniciar API de datos desde el clúster

```bash
kubectl exec -n mlops-pf $(kubectl get pod -n mlops-pf -l app=airflow-scheduler -o jsonpath="{.items[0].metadata.name}") -- \
  python3 -c "import requests; r = requests.get('http://data-api:80/restart_data_generation?group_number=8'); print(r.status_code, r.text)"
```

---

## 18. Limitaciones conocidas

1. La Data API devuelve batches en formatos mixtos (arrays o diccionarios) — el DAG maneja ambos.
2. La API cambia de batch cada 5 minutos — ejecutar el DAG rápidamente para obtener el mismo batch.
3. Hay 10 batches disponibles por ciclo — retorna 400 al agotarse; reiniciar con el comando de la sección 17.7.
4. El scheduler de Airflow tiene límite de 2Gi de memoria — las queries tienen LIMIT 10.000 para evitar OOM.
5. La API de inferencia usa un solo proceso Uvicorn — bajo carga concurrente puede presentar latencias altas.
6. Cada inferencia escribe síncronamente en PostgreSQL — contribuye a la latencia bajo carga.
7. El modelo es un GradientBoostingRegressor baseline sin hyperparameter tuning.

---

## 19. Nota técnica — Pipeline del modelo

El pipeline de sklearn incluye preprocesamiento interno:

```text
SimpleImputer(strategy="median")
        ↓
GradientBoostingRegressor(n_estimators=50, max_depth=4, learning_rate=0.1)
```

El imputador maneja valores nulos automáticamente en inferencia, evitando que la API falle cuando los datos de entrada tengan campos opcionales omitidos.

Las features de entrada son las 54 columnas de `COLUMN_NAMES` sin `price` (target):

```text
brokered_by, bed, bath, acre_lot, house_size, zip_code, col_07 ... col_54
```

---

## 20. Troubleshooting

### El DAG no aparece en Airflow

Verificar que el initContainer copió el archivo:

```bash
kubectl exec -n mlops-pf $(kubectl get pod -n mlops-pf -l app=airflow-scheduler -o jsonpath="{.items[0].metadata.name}") -- \
  ls /opt/airflow/dags/
```

Si está vacío, reiniciar el scheduler:

```bash
kubectl rollout restart deployment/airflow-scheduler -n mlops-pf
```

### El scheduler se reinicia por OOM

Las queries del DAG tienen LIMIT 10.000. Si el problema persiste, verificar el límite de memoria en `k8s/airflow/deployment.yaml` (actualmente 2Gi).

### La API retorna `model_loaded: false`

El modelo champion no existía cuando arrancó la API. Reiniciar después del DAG:

```bash
kubectl rollout restart deployment/api -n mlops-pf
```

### La Data API retorna 400

Se agotaron los 10 batches del ciclo. Reiniciar desde dentro del clúster (sección 17.7).

### Logs del DAG no accesibles desde la UI de Airflow

El webserver no puede resolver el hostname del scheduler. Leer directamente:

```bash
kubectl exec -n mlops-pf $(kubectl get pod -n mlops-pf -l app=airflow-scheduler -o jsonpath="{.items[0].metadata.name}") -- \
  bash -c "find /opt/airflow/logs -name '*.log' | grep <task_id> | tail -1 | xargs tail -30"
```

### Error XCom con NaN

Los valores `NaN` de pandas no son válidos en JSON. El DAG usa `safe_float()` para convertirlos a `0.0` antes de retornarlos por XCom.

---

## 21. Mejoras futuras

### CI/CD — Builds selectivos por servicio

El workflow actual de GitHub Actions reconstruye todas las imágenes Docker en cada `push` a `main`, independientemente de qué archivos cambiaron. Esto genera builds innecesarios y aumenta el tiempo de entrega.

La mejora consiste en usar `dorny/paths-filter` para detectar qué directorios cambiaron y reconstruir solo las imágenes afectadas:

```yaml
jobs:
  changes:
    outputs:
      api: ${{ steps.filter.outputs.api }}
      airflow: ${{ steps.filter.outputs.airflow }}
    steps:
      - uses: dorny/paths-filter@v2
        with:
          filters: |
            api:
              - 'api/**'
            airflow:
              - 'airflow/**'

  build-api:
    needs: changes
    if: ${{ needs.changes.outputs.api == 'true' }}
    ...
```

### Logging asíncrono en la API

Cada inferencia escribe síncronamente en PostgreSQL, lo que aumenta la latencia bajo carga. La mejora sería usar una cola interna (por ejemplo `asyncio.Queue` o Celery) para desacoplar la escritura del log de la respuesta al cliente.

### Múltiples workers en la API

El servicio FastAPI usa un solo proceso Uvicorn. Para escenarios de carga real se recomienda configurar múltiples workers o usar Gunicorn como process manager frente a Uvicorn.

### Hyperparameter tuning automático

El modelo actual usa parámetros fijos (`n_estimators=50`, `max_depth=4`). Una mejora sería integrar Optuna o MLflow Hyperparameter Tuning dentro del DAG para optimizar automáticamente los hiperparámetros en cada ciclo de entrenamiento.

### Reentrenamiento automático por schedule

El DAG actualmente se ejecuta de forma manual. Una mejora sería configurar un `schedule` en Airflow (por ejemplo cada 6 horas) para que el pipeline se ejecute automáticamente y consuma nuevos batches sin intervención humana.

---

## 22. Checklist final

### Infraestructura

```bash
kubectl get pods -n mlops-pf
# Todos en Running o Completed
```

### URLs accesibles

```text
Argo CD:    http://localhost:8080   → App mlops-pf: Synced + Healthy
Airflow:    http://localhost:8081   → DAG real_estate_pipeline visible
MLflow:     http://localhost:5050   → Experimento y modelo champion registrado
MinIO:      http://localhost:9001   → Bucket mlflow-artifacts con artefactos
FastAPI:    http://localhost:8000/docs → Swagger accesible
Streamlit:  http://localhost:8501   → API conectada, predicción funcional
Locust:     http://localhost:8089   → Prueba de carga ejecutable
Prometheus: http://localhost:9090   → Target api en estado UP
Grafana:    http://localhost:3000   → Dashboard con métricas visibles
```

### Modelo champion

```bash
curl http://localhost:8000/health
# "model_loaded": true
```

### Pipeline ejecutado

```bash
kubectl exec -n mlops-pf $(kubectl get pod -n mlops-pf -l app=postgres -o jsonpath="{.items[0].metadata.name}") -- \
  psql -U mlops_user -d mlops_real_estate -c \
  "SELECT batch_number, training_decision, model_promoted FROM raw.batch_metadata ORDER BY ingestion_timestamp;"
# Al menos un batch con model_promoted = true
# Al menos un batch con model_promoted = false
```

### Inferencias registradas

```bash
kubectl exec -n mlops-pf $(kubectl get pod -n mlops-pf -l app=postgres -o jsonpath="{.items[0].metadata.name}") -- \
  psql -U mlops_user -d mlops_real_estate -c "SELECT COUNT(*) FROM raw.inference_logs;"
# COUNT > 0
```

### GitHub Actions

```text
https://github.com/javierhellch/MLOps_ProyectoFinal/actions
→ Último workflow: passed ✅
```

### Argo CD

```bash
kubectl get application -n argocd
# STATUS: Synced   HEALTH: Healthy
```