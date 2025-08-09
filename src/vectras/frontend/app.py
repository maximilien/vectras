import os
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def create_app() -> FastAPI:
    app = FastAPI(title="Vectras UI", description="Static UI for Vectras", version="0.1.0")

    # Serve the frontend directory
    root_dir = Path(__file__).resolve().parents[3]
    frontend_dir = root_dir / "frontend"
    static_dir = frontend_dir / "static"
    static_dir.mkdir(parents=True, exist_ok=True)

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    index_path = frontend_dir / "index.html"

    @app.get("/")
    async def index() -> Response:
        if index_path.exists():
            # Read the HTML file and inject the application title
            with open(index_path, "r") as f:
                html_content = f.read()
            
            # Get application title from environment or use default
            app_title = os.getenv("APPLICATION_TITLE", "Vectras AI Assistant")
            
            # Inject the title as a global variable
            html_content = html_content.replace(
                '</head>',
                f'<script>window.APP_TITLE = "{app_title}";</script></head>'
            )
            
            return Response(html_content, media_type="text/html")
        return Response("<h1>Vectras UI</h1><p>index.html missing.</p>", media_type="text/html")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("VECTRAS_UI_HOST", "localhost")
    port = int(os.getenv("VECTRAS_UI_PORT", "8120"))
    uvicorn.run(app, host=host, port=port)


