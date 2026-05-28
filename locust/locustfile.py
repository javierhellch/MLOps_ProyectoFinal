from __future__ import annotations
from locust import HttpUser, between, task


class RealEstatePredictionUser(HttpUser):
    wait_time = between(1, 3)

    @task(1)
    def health_check(self):
        self.client.get("/health", name="/health")

    @task(5)
    def predict_price(self):
        payload = {
            "brokered_by": 150,
            "bed": 3,
            "bath": 2,
            "acre_lot": 100,
            "house_size": 1500,
            "zip_code": 180,
            "col_07": 200,
            "col_08": 100,
            "col_09": 1000,
            "col_10": 0, "col_11": 0, "col_12": 1, "col_13": 0,
            "col_14": 0, "col_15": 0, "col_16": 0, "col_17": 0,
            "col_18": 0, "col_19": 0, "col_20": 0, "col_21": 0,
            "col_22": 0, "col_23": 0, "col_24": 0, "col_25": 0,
            "col_26": 0, "col_27": 0, "col_28": 0, "col_29": 0,
            "col_30": 0, "col_31": 0, "col_32": 0, "col_33": 0,
            "col_34": 0, "col_35": 0, "col_36": 0, "col_37": 0,
            "col_38": 0, "col_39": 0, "col_40": 0, "col_41": 0,
            "col_42": 0, "col_43": 0, "col_44": 0, "col_45": 0,
            "col_46": 0, "col_47": 0, "col_48": 0, "col_49": 0,
            "col_50": 0, "col_51": 1, "col_52": 0, "col_53": 0,
        }

        with self.client.post(
            "/predict",
            json=payload,
            name="/predict",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Status code inesperado: {response.status_code}")
                return
            try:
                data = response.json()
            except Exception:
                response.failure("La respuesta no es JSON válido")
                return
            if "prediction" not in data:
                response.failure("La respuesta no contiene prediction")
                return
            response.success()