from contextlib import asynccontextmanager

import fastapi as fa


@asynccontextmanager
async def lifespan(application):
    yield


application = fa.FastAPI(lifespan=lifespan)


@application.get("/")
def read_root():
    return {"ok": True}
