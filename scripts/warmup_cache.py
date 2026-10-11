import os
import sys
import json
import asyncio
import redis.asyncio as aioredis

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.backend.infrastructure.webserver.config import config
from scripts.init_db import COURSES_SPEC, INSTRUCTORS, ROOMS, PERIOD_RANGES
from src.backend.core.domain.entities.time_slot import TimeSlot

async def warmup_cache():
    print(f"Connecting to Redis at {config.redis_url}...")
    r = aioredis.from_url(config.redis_url, decode_responses=True)

    print("Generating and pre-warming catalog:active_sections...")
    sections = []
    pipe = r.pipeline()

    section_idx = 1
    course_section_counter = {}
    while section_idx <= 200:
        for code, name, credits, prereq, dept in COURSES_SPEC:
            if section_idx > 200:
                break
            
            course_section_counter[code] = course_section_counter.get(code, 0) + 1
            sec_num = course_section_counter[code]

            day = (section_idx % 6) + 2 # 2 to 7
            start_p, end_p = PERIOD_RANGES[(section_idx % len(PERIOD_RANGES))]
            mask = TimeSlot(schedule_day=day, start_period=start_p, end_period=end_p).compute_mask()
            capacity = 30 if section_idx == 1 else 40
            
            sec_dict = {
                "id": f"sec-{section_idx:03d}",
                "section_code": f"{code}-{sec_num:02d}",
                "course_code": code,
                "course_name": name,
                "credits": credits,
                "prerequisite_course_code": prereq or "NONE",
                "instructor": INSTRUCTORS[section_idx % len(INSTRUCTORS)],
                "classroom": ROOMS[section_idx % len(ROOMS)],
                "schedule_day": day,
                "start_period": start_p,
                "end_period": end_p,
                "time_mask": mask,
                "max_capacity": capacity,
                "current_enrolled": 0,
                "available_slots": capacity,
                "department": dept
            }
            sections.append(sec_dict)

            # Warm-up từng section slot & mask
            sec_id = sec_dict["id"]
            pipe.set(f"section:{sec_id}:slots", capacity)
            pipe.set(f"section:{sec_id}:time_mask", mask)
            pipe.delete(f"section:{sec_id}:enrolled")

            section_idx += 1

    # Lưu toàn bộ 200 lớp vào khóa JSON duy nhất cho Client-side search (12h TTL)
    pipe.set("catalog:active_sections", json.dumps(sections), ex=43200)

    print("Pre-warming 3.000 Students data into Redis...")
    for i in range(1, 3001):
        std_id = f"std-{i:04d}"
        # Credits hash
        pipe.hset(f"student:{std_id}:credits", mapping={"current": 0, "max": 24})
        # Schedule mask
        pipe.set(f"student:{std_id}:registered_mask", 0)
        # Pre-requisite completed courses (set CS101, MATH101, ENG101 as completed)
        pipe.delete(f"student:{std_id}:completed_courses")
        pipe.sadd(f"student:{std_id}:completed_courses", "CS101", "MATH101", "ENG101")

        if i % 500 == 0:
            await pipe.execute()
            pipe = r.pipeline()
            print(f"  Pre-warmed {i}/3000 students...")

    await pipe.execute()
    await r.close()
    print("CACHE PRE-WARMING PIPELINE COMPLETED SUCCESSFULLY! All 3.000 students & 200 sections ready.")

if __name__ == "__main__":
    asyncio.run(warmup_cache())
