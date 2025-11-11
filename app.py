from fastapi import FastAPI
from mangum import Mangum

fastapi = FastAPI(title="Ejemplo sencillo FastAPI + Mangum")

@fastapi.get("/")
def read_root():
    return {"mensaje": "Hola desde FastAPI en AWS Lambda"}

@fastapi.get("/saludo/{nombre}")
def saludar(nombre: str):
    return {"saludo": f"Hola, {nombre}. Bienvenido a la API!"}

mangum = Mangum(fastapi)
