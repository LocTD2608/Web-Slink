import os, time, json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, Header, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from jose import jwt, JWTError
from sqlalchemy import select, text
from src.backend.core.domain.entities.operation import RegistrationError
from src.backend.infrastructure.observability.metrics import Metrics, generate_latest, CONTENT_TYPE_LATEST

class RegisterBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section_id: str = Field(min_length=1, max_length=36)

class LabTokenBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_id: str

def create_app(lab_mode=None, secret=None):
    from src.backend.infrastructure.webserver.config import config
    lab = config.lab_mode if lab_mode is None else lab_mode
    signing_key = secret or config.jwt_secret
    metrics = Metrics()

    @asynccontextmanager
    async def lifespan(app):
        from src.backend.infrastructure.bootstrap import build_service
        from src.backend.infrastructure.database.db_connection import engine, create_tables
        if not lab and signing_key == "super-secret-course-reg-key-2026":
            raise RuntimeError("Set JWT_SECRET outside LAB_MODE")
        await create_tables()
        app.state.service, app.state.catalog = build_service()
        yield
        await app.state.service.queue.close()
        await app.state.service.store.redis.aclose(close_connection_pool=True)
        await engine.dispose()

    app = FastAPI(title="Course Registration Lab", version="3.0.0", lifespan=lifespan)

    @app.middleware("http")
    async def observe(request, call_next):
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            route = request.scope.get("route")
            path = getattr(route, "path", "unmatched")
            if path != "/metrics":
                metrics.requests.labels(path, request.method, str(status)).inc()
                metrics.duration.labels(path, request.method).observe(time.perf_counter()-started)

    async def identity(request: Request):
        auth = request.headers.get("Authorization", "")
        try:
            if not auth.startswith("Bearer "):
                raise ValueError()
            claims = jwt.decode(auth[7:], signing_key, algorithms=["HS256"], options={"require_exp":True, "require_sub":True})
            return claims["sub"]
        except (JWTError, ValueError, KeyError):
            raise HTTPException(401, "Authentication required")

    @app.exception_handler(RegistrationError)
    async def business_error(request, exc):
        return JSONResponse(status_code=exc.status_code, content={"error_code":exc.code, "detail":exc.code})

    @app.exception_handler(Exception)
    async def unavailable(request, exc):
        import logging
        logging.getLogger(__name__).exception("Request failed")
        return JSONResponse(status_code=503, content={"error_code":"SERVICE_UNAVAILABLE",
            "detail":"Dịch vụ tạm thời chưa sẵn sàng", "ticket_id":getattr(exc, "ticket_id", None)})

    @app.get("/health")
    async def health():
        return {"status":"healthy", "mode":config.registration_mode, "lab_mode":lab}

    @app.get("/ready")
    async def ready(request: Request):
        from src.backend.infrastructure.database.db_connection import AsyncSessionLocal
        async with AsyncSessionLocal() as s: await s.execute(text("SELECT 1"))
        if request.app.state.service.mode == "redis_queue":
            await request.app.state.service.store.redis.ping()
            await request.app.state.service.queue.get_channel()
        return {"status":"ready"}

    @app.get("/metrics")
    async def exposition():
        return Response(generate_latest(metrics.registry), media_type=CONTENT_TYPE_LATEST)

    @app.get("/api/v1/sections")
    async def sections(request: Request):
        service = request.app.state.service
        if service.mode == "redis_queue":
            raw = await service.store.redis.get("lab:catalog")
            if raw:
                catalog = json.loads(raw)
                slots = await service.store.redis.mget([f"lab:section:{s['id']}:slots" for s in catalog])
                for sec, available in zip(catalog, slots):
                    if available is not None:
                        sec["available_slots"] = int(available)
                        sec["current_enrolled"] = sec["max_capacity"]-int(available)
                return catalog
        return await request.app.state.catalog.sections()

    @app.post("/api/v1/registrations")
    async def register(body: RegisterBody, request: Request, student=Depends(identity), x_idempotency_key: str = Header(...)):
        op = await request.app.state.service.register(student, body.section_id, x_idempotency_key)
        return JSONResponse(op.to_dict(), status_code=202 if op.status == "PENDING" else 200)

    @app.delete("/api/v1/registrations/{registration_id}")
    async def drop(registration_id: str, request: Request, student=Depends(identity), x_idempotency_key: str = Header(...)):
        op = await request.app.state.service.drop(registration_id, student, x_idempotency_key)
        return JSONResponse(op.to_dict(), status_code=202 if op.status == "CANCEL_PENDING" else 200)

    @app.get("/api/v1/registrations/status/{ticket_id}")
    async def status(ticket_id: str, request: Request, student=Depends(identity)):
        return (await request.app.state.service.status(ticket_id, student)).to_dict()

    @app.get("/api/v1/registrations/student/{student_id}")
    async def enrolled(student_id: str, request: Request, student=Depends(identity)):
        if student_id != student: raise RegistrationError("FORBIDDEN", 403)
        return await request.app.state.catalog.sections(student)

    @app.post("/api/v1/lab/token")
    async def lab_token(body: LabTokenBody):
        if not lab: raise HTTPException(404)
        from src.backend.infrastructure.database.db_connection import AsyncSessionLocal
        from src.backend.infrastructure.database.models import StudentModel
        async with AsyncSessionLocal() as s:
            student = await s.get(StudentModel, body.student_id)
            if not student: raise RegistrationError("NOT_FOUND", 404)
            profile = {"id":student.id, "student_code":student.student_code, "full_name":student.full_name,
                "major":student.major, "max_credits":student.max_credits, "current_credits":0}
        return {"token":jwt.encode({"sub":body.student_id, "exp":time.time()+86400}, signing_key, algorithm="HS256"), "student":profile}
    return app
