from fastapi import APIRouter

from app.api.v1.routes import answer, answers, audit, auth, evaluate, health, reviews

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(answer.router, tags=["answer"])
api_router.include_router(evaluate.router, tags=["evaluate"])
api_router.include_router(answers.router, tags=["answers"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
