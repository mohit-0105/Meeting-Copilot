from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import router as api_router
from app.api.websocket import handle_meeting_websocket

app = FastAPI(
    title="Meeting Copilot API",
    description="Real-time speech-to-text, live AI copilot, and meeting intelligence backend",
    version="0.1.0"
)

# CORS configuration to allow Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register REST API endpoints
app.include_router(api_router)

# Register WebSocket endpoint
@app.websocket("/ws/meetings/{meeting_id}")
async def websocket_meeting_endpoint(websocket: WebSocket, meeting_id: str):
    await handle_meeting_websocket(websocket, meeting_id)

@app.get("/")
async def root():
    return {
        "name": "Meeting Copilot Backend",
        "docs": "/docs",
        "health": "/api/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
