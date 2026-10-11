import time
import asyncio
from typing import Dict, Any, Optional
from fastapi import APIRouter

from src.backend.core.usecases.register_course import RegisterCourseUseCase, RegisterCourseCommand
from src.backend.core.domain.exceptions.registration_exceptions import SectionFullException, DomainException
from scripts.init_db import init_database
from scripts.warmup_cache import warmup_cache

router = APIRouter(prefix="/api/v1/demo", tags=["Demo Simulation"])

_register_usecase: Optional[RegisterCourseUseCase] = None

def set_demo_register_usecase(uc: RegisterCourseUseCase):
    global _register_usecase
    _register_usecase = uc

@router.post("/race-condition")
async def run_race_condition_simulation(
    target_section: str = "sec-001",
    total_users: int = 500
) -> Dict[str, Any]:
    """
    Kích hoạt mô phỏng tải tranh chấp đồng thời 500 sinh viên tranh 30 slot của lớp target_section.
    Chạy trực tiếp từ giao diện Web để phục vụ thuyết trình đồ án.
    """
    assert _register_usecase is not None, "RegisterCourseUseCase not initialized"

    start_time = time.perf_counter()
    success_count = 0
    conflict_count = 0
    error_count = 0

    async def simulate_single_user(user_idx: int):
        nonlocal success_count, conflict_count, error_count
        student_id = f"std-{user_idx:04d}"
        command = RegisterCourseCommand(
            student_id=student_id,
            section_id=target_section,
            semester_id="sem-2024-1",
            prerequisite_course_code="NONE",
            section_time_mask=7,
            credits=3
        )
        try:
            await _register_usecase.execute(command)
            success_count += 1
        except SectionFullException:
            conflict_count += 1
        except Exception:
            error_count += 1

    tasks = [simulate_single_user(i) for i in range(1, total_users + 1)]
    await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - start_time
    throughput = round(total_users / elapsed, 1) if elapsed > 0 else 0

    return {
        "target_section": target_section,
        "total_users": total_users,
        "slots_allocated": success_count,
        "rejected_full": conflict_count,
        "errors": error_count,
        "elapsed_seconds": round(elapsed, 2),
        "throughput_rps": throughput,
        "zero_overselling": (success_count == 30 and conflict_count == (total_users - 30))
    }

@router.post("/reset-data")
async def reset_demo_data() -> Dict[str, Any]:
    """
    Làm sạch và đồng bộ lại toàn bộ CSDL PostgreSQL và Redis Cache về trạng thái ban đầu.
    """
    await init_database()
    await warmup_cache()
    return {
        "success": True,
        "message": "Đã thiết lập lại dữ liệu mẫu thành công. Tất cả 200 lớp học phần sẵn sàng!"
    }
