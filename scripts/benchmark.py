"""Isolated benchmark dataset lifecycle. Run inside the lab API container."""
import argparse, asyncio, csv, json, os, time, statistics
from pathlib import Path
from sqlalchemy import select, delete, func, text
from jose import jwt
import httpx
from src.backend.infrastructure.database.db_connection import AsyncSessionLocal, engine, create_tables
from src.backend.infrastructure.database.models import (
    StudentModel, CourseModel, SemesterModel, CourseSectionModel, RegistrationModel, OperationModel, BenchmarkRunModel)
from src.backend.infrastructure.bootstrap import build_service
from src.backend.infrastructure.webserver.config import config

RESULTS = Path(os.getenv("RESULT_DIR", "artifacts/benchmarks"))

def validate_counts(data, expected, mode):
    valid = data["confirmed"] == expected and data["enrolled"] == expected
    if mode == "redis_queue":
        valid = (valid and data["slots"] == 60-expected and data["owners"] == expected
                 and data["pending"] == 0 and data.get("queues_empty") is True
                 and data.get("credits_valid", True) and data.get("periods_valid", True))
    return valid

async def queues_empty():
    async with httpx.AsyncClient(timeout=10) as client:
        for name in ("registration_queue", "drop_queue"):
            base = os.getenv("RABBITMQ_MANAGEMENT_URL", "http://rabbitmq:15672")
            response = await client.get(f"{base}/api/queues/%2F/{name}", auth=("guest","guest"))
            if response.status_code == 404: continue
            response.raise_for_status()
            q = response.json()
            if q.get("messages_ready",0) or q.get("messages_unacknowledged",0):
                return False
    return True

async def prepare(mode):
    if not config.lab_mode:
        raise RuntimeError("LAB_MODE required")
    await create_tables()
    service, _ = build_service()
    r = service.store.redis
    async with engine.connect() as lock:
        if not await lock.scalar(text("SELECT pg_try_advisory_lock(71007001)")):
            raise RuntimeError("Another prepare is running")
        try:
            async with AsyncSessionLocal() as s, s.begin():
                run = await s.get(BenchmarkRunModel, "flash", with_for_update=True)
                if not run:
                    run = BenchmarkRunModel(id="flash",generation=0,accepting=False)
                    s.add(run)
                run.accepting = False
            await r.delete("lab:run:flash")
            # Closing admission precedes drain checks: late reservations are rejected by Lua.
            if await r.zcard("lab:pending") or not await queues_empty():
                raise RuntimeError("Pending/queued work: drain or recover before prepare")
            async with AsyncSessionLocal() as s, s.begin():
                run = await s.get(BenchmarkRunModel, "flash", with_for_update=True)
                run.generation += 1
                generation = run.generation
                await s.execute(delete(OperationModel).where(OperationModel.section_id == "bench-section"))
                await s.execute(delete(RegistrationModel).where(RegistrationModel.section_id == "bench-section"))
                if not await s.get(SemesterModel,"bench-sem"):
                    s.add(SemesterModel(id="bench-sem",semester_code="BENCH",name="Benchmark only",is_active=True))
                    s.add(CourseModel(id="bench-course",course_code="BENCH",course_name="Benchmark 60 seats",credits=3,department="LAB"))
                    await s.flush()
                section = await s.get(CourseSectionModel,"bench-section")
                if not section:
                    section = CourseSectionModel(id="bench-section",section_code="BENCH-60",course_id="bench-course",
                        semester_id="bench-sem",instructor="Lab",classroom="Virtual",schedule_day=2,
                        start_period=1,end_period=3,time_mask=7,max_capacity=60,current_enrolled=0)
                    s.add(section)
                section.current_enrolled = 0
                existing = set((await s.scalars(select(StudentModel.id).where(StudentModel.id.like("bench-%")))).all())
                for i in range(3000):
                    sid = f"bench-{i:04d}"
                    if sid not in existing:
                        s.add(StudentModel(id=sid,student_code=f"B{i:04d}",full_name=f"Benchmark {i}",email=f"b{i}@lab.invalid",
                            major="LAB",academic_year=2026,max_credits=24))
            # Only benchmark cache and its operation metadata are reset.
            keys = [k async for k in r.scan_iter("lab:student:bench-sem:*")]
            for key in [k async for k in r.scan_iter("lab:op:*")]:
                data = json.loads(await r.get(key))
                if data["operation"]["section_id"] == "bench-section":
                    keys.extend([key,"lab:idem:"+data["key"]])
            if keys: await r.delete(*keys)
            await r.delete("lab:section:bench-section:owners")
            await r.set("lab:section:bench-section:slots",60)
            await r.set("lab:run:flash",generation)
            async with AsyncSessionLocal() as s, s.begin():
                run = await s.get(BenchmarkRunModel,"flash",with_for_update=True)
                run.accepting = True
            from src.backend.infrastructure.database.repositories.catalog_repository import CatalogRepository
            from src.backend.infrastructure.cache.context_cache import warm_contexts
            await warm_contexts(AsyncSessionLocal,r)
            await r.set("lab:catalog",json.dumps(await CatalogRepository(AsyncSessionLocal).sections()))
            RESULTS.mkdir(parents=True,exist_ok=True)
            users = [{"id":f"bench-{i:04d}","token":jwt.encode({"sub":f"bench-{i:04d}","exp":time.time()+86400},config.jwt_secret,algorithm="HS256")} for i in range(3000)]
            (RESULTS/"fixture.json").write_text(json.dumps({"generation":generation,"mode":mode,"users":users}),encoding="utf-8")
            print(json.dumps({"prepared":True,"generation":generation,"users":3000,"capacity":60,"mode":mode}))
        finally:
            await lock.execute(text("SELECT pg_advisory_unlock(71007001)"))
            await service.queue.close()
            await r.aclose(close_connection_pool=True)

async def verify(mode, run_id, expected=60, timeout=60):
    service, _ = build_service()
    deadline = time.monotonic()+timeout
    try:
        while True:
            async with AsyncSessionLocal() as s:
                count = await s.scalar(select(func.count()).select_from(RegistrationModel).where(
                    RegistrationModel.section_id=="bench-section",RegistrationModel.status=="CONFIRMED"))
                sec = await s.get(CourseSectionModel,"bench-section")
            data = {"confirmed":count,"enrolled":sec.current_enrolled,"mode":mode,"run_id":run_id}
            if mode == "redis_queue":
                r = service.store.redis
                data.update(slots=int(await r.get("lab:section:bench-section:slots") or -1),
                    owners=await r.hlen("lab:section:bench-section:owners"),pending=await r.zcard("lab:pending"))
                data["queues_empty"] = await queues_empty()
                owner_ids = await r.hkeys("lab:section:bench-section:owners")
                credits = await r.mget([f"lab:student:bench-sem:{sid}:credits" for sid in owner_ids]) if owner_ids else []
                data["credits_valid"] = all(value == "3" for value in credits)
                data["periods_valid"] = all([await r.smembers(f"lab:student:bench-sem:{sid}:periods") == {"0","1","2"} for sid in owner_ids])
            if mode != "redis_queue" or (not data["pending"] and data["queues_empty"]) or time.monotonic()>=deadline:
                break
            await asyncio.sleep(1)
        data["valid"] = validate_counts(data,expected,mode)
        RESULTS.mkdir(parents=True,exist_ok=True)
        (RESULTS/f"{run_id}-verification.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
        print(json.dumps(data))
        if not data["valid"]: raise RuntimeError("Benchmark verification failed")
    finally:
        await service.queue.close()
        await service.store.redis.aclose(close_connection_pool=True)

def report():
    rows=[]
    for path in sorted(RESULTS.glob("*-summary.json")):
        summary=json.loads(path.read_text(encoding="utf-8-sig"))
        reg=summary["metrics"].get("http_req_duration{phase:register}",{}).get("values",{})
        verification=path.with_name(path.name.replace("-summary.json","-verification.json"))
        verify=json.loads(verification.read_text()) if verification.exists() else {}
        rows.append({"run":path.stem.removesuffix("-summary"),"avg_ms":reg.get("avg"),
            "p95_ms":reg.get("p(95)"),"confirmed":verify.get("confirmed"),"valid":verify.get("valid"),
            "completion_p95_ms":summary["metrics"].get("completion_duration",{}).get("values",{}).get("p(95)"),
            "unexpected":summary["metrics"].get("unexpected",{}).get("values",{}).get("count")})
    with (RESULTS/"comparison.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=["run","avg_ms","p95_ms","completion_p95_ms","confirmed","unexpected","valid"])
        writer.writeheader();writer.writerows(rows)
    lines=["| Run | avg ms | p95 ms | completion p95 ms | Confirmed | Unexpected | Verified |","|---|---:|---:|---:|---:|---:|---|"]
    lines += ["| "+" | ".join(str(row[k]) for k in ("run","avg_ms","p95_ms","completion_p95_ms","confirmed","unexpected","valid"))+" |" for row in rows]
    for mode in ("postgres","redis_queue"):
        group=[row for row in rows if row["run"] in [f"{mode}-{i}" for i in (1,2,3)] and row["valid"]]
        if len(group)==3 and all(row["p95_ms"] is not None for row in group):
            lines.append(f"\nMedian {mode}: avg {statistics.median(row['avg_ms'] for row in group):.3f} ms; p95 {statistics.median(row['p95_ms'] for row in group):.3f} ms.")
    (RESULTS/"comparison.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("action",choices=["prepare","verify","report"])
    p.add_argument("--mode",choices=["postgres","redis_queue"],default=config.registration_mode)
    p.add_argument("--run-id",default="flash")
    p.add_argument("--expected",type=int,default=60)
    args=p.parse_args()
    if not args.run_id.replace("-","").replace("_","").isalnum(): p.error("Invalid run id")
    if args.action=="report": report()
    else: asyncio.run(prepare(args.mode) if args.action=="prepare" else verify(args.mode,args.run_id,args.expected))
