from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .engine import Engine
from .models import (
    AssignBody,
    ConnectBody,
    CustomMatrixBody,
    DelayBody,
    PresetBody,
    VolumeBody,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

STATIC = Path(__file__).parent.parent / "static"
engine = Engine()
app = FastAPI(title="btasio", version="0.1.0")


@app.get("/api/state")
def state():
    return engine.refresh()


@app.post("/api/refresh")
def refresh():
    return engine.refresh()


@app.post("/api/preset")
def preset(body: PresetBody):
    return engine.set_preset(body.preset)


@app.post("/api/assign")
def assign(body: AssignBody):
    return engine.assign(body)


@app.post("/api/delay")
def delay(body: DelayBody):
    return engine.set_delay(body)


@app.post("/api/volume")
def volume(body: VolumeBody):
    return engine.set_volume(body)


@app.post("/api/matrix")
def matrix(body: CustomMatrixBody):
    return engine.set_matrix(body)


@app.post("/api/connect")
def connect(body: ConnectBody):
    return engine.connect(body.mac, body.adapter)


@app.post("/api/disconnect")
def disconnect(body: ConnectBody):
    return engine.disconnect(body.mac)


@app.post("/api/scan")
def scan(seconds: int = 8):
    return engine.scan(seconds=min(max(seconds, 3), 20))


@app.post("/api/apply")
def apply():
    return engine.apply_graph()


@app.get("/")
def index():
    index = STATIC / "index.html"
    if not index.exists():
        raise HTTPException(404, "UI missing")
    return FileResponse(index)


if STATIC.exists():
    app.mount("/static", StaticFiles(directory=STATIC), name="static")


def run() -> None:
    import uvicorn

    uvicorn.run("btasio_hub.main:app", host="0.0.0.0", port=8745, reload=False)


if __name__ == "__main__":
    run()
