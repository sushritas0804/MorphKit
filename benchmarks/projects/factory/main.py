from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI()

    @app.get("/")
    def home():
        return {"ok": True}

    return app


app = create_app()
