CREATE USER airflow_user WITH PASSWORD 'airflow_password';
CREATE DATABASE airflow_db OWNER airflow_user;
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow_user;