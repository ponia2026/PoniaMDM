from fastapi import FastAPI
from .converters import CONVERTERS

app = FastAPI(title="PoniaMDM")


@app.get("/api/sources")
def sources():
    return [{"key": k, "label": c.label} for k, c in CONVERTERS.items()]
