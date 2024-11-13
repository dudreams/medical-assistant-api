import nest_asyncio
nest_asyncio.apply()

from routers import assistant

from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse


app = FastAPI(
    title="Medical Assistant API",
    description="This is the API documentation for the Medical Assistant project.",
    version="1.0.0",
    contact={
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)


app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# 레이트 리미팅 설정
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# DB 연결
# Base.metadata.create_all(bind=engine)

app.include_router(assistant.router, prefix="/assistant", tags=["Assistant"])

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# if __name__ == "__main__":
#     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
# bash > uvicorn main:app --host [host] --port [port] --reload