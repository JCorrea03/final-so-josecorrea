from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, conint, confloat
import boto3
import os
import csv
from typing import Optional
from botocore.exceptions import ClientError

# Config desde variables de entorno
S3_BUCKET = os.getenv("S3_BUCKET")  # nombre del bucket
S3_KEY = os.getenv("S3_KEY", "datos.csv")  # nombre del archivo en el bucket
AWS_REGION = os.getenv("AWS_REGION")  # opcional

if not S3_BUCKET:
    raise RuntimeError("La variable de entorno S3_BUCKET no está definida.")

# Inicializar cliente S3 (si la instancia tiene IAM role, no hace falta credenciales en env)
s3 = boto3.client("s3", region_name=AWS_REGION) if AWS_REGION else boto3.client("s3")

app = FastAPI(title="API de ejemplo - Guardar CSV en S3")

class Persona(BaseModel):
    nombre: str = Field(..., min_length=1)
    edad: conint(ge=0, le=150)
    altura: confloat(gt=0)  # altura en metros, por ejemplo

def create_csv_content(rows):
    """rows: lista de tuplas o listas. Devuelve bytes del CSV (utf-8)"""
    from io import StringIO
    sio = StringIO()
    writer = csv.writer(sio)
    # Escribir header
    writer.writerow(["nombre", "edad", "altura"])
    for r in rows:
        writer.writerow(r)
    return sio.getvalue().encode("utf-8")

@app.post("/personas", status_code=201)
def crear_persona(p: Persona):
    """
    1) Validación automática con Pydantic
    2) Se lee el CSV actual del bucket (si existe), se agrega la fila y se sobrescribe el mismo objeto S3.
    """
    # Leer CSV actual (si existe)
    try:
        resp = s3.get_object(Bucket=S3_BUCKET, Key=S3_KEY)
        body = resp["Body"].read().decode("utf-8")
        # parsear CSV existente (sin pandas)
        existing = []
        reader = csv.reader(body.splitlines())
        header = next(reader, None)
        for row in reader:
            if row:  # evitar líneas vacías
                existing.append(row)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        # si no existe el objeto, lo creamos nuevo
        if code in ("NoSuchKey", "404", "NoSuchBucket", "NoSuchKey"):
            existing = []
        else:
            # otros errores de S3
            raise HTTPException(status_code=500, detail=f"Error leyendo S3: {e}")

    # Agregar la nueva fila (mantener columnas nombre,edad,altura)
    existing.append([p.nombre, str(p.edad), str(p.altura)])

    # Generar contenido CSV y subir (sobrescribe el key)
    csv_bytes = create_csv_content(existing)
    try:
        s3.put_object(Bucket=S3_BUCKET, Key=S3_KEY, Body=csv_bytes, ContentType="text/csv")
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Error subiendo a S3: {e}")

    return {"message": "Persona guardada", "rows": len(existing)}

@app.get("/personas/count")
def contar_personas():
    """
    Retorna el número de filas (excluyendo la cabecera).
    """
    try:
        resp = s3.get_object(Bucket=S3_BUCKET, Key=S3_KEY)
        body = resp["Body"].read().decode("utf-8")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code in ("NoSuchKey", "404", "NoSuchBucket", "NoSuchKey"):
            return {"rows": 0}
        else:
            raise HTTPException(status_code=500, detail=f"Error leyendo S3: {e}")

    # contar filas válidas
    reader = csv.reader(body.splitlines())
    # saltar header
    _ = next(reader, None)
    count = 0
    for row in reader:
        if row:
            count += 1
    return {"rows": count}
