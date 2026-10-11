from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from src.backend.core.usecases.register_course import RegisterCourseUseCase, RegisterCourseCommand
from src.backend.core.usecases.drop_course import DropCourseUseCase, DropCourseCommand
from src.backend.core.domain.exceptions.registration_exceptions import (
    SectionFullException,
    ScheduleConflictException,
    PrerequisiteNotMetException,
    CreditLimitExceededException,
    AlreadyRegisteredException,
    DomainException
)

from typing import Optional, Dict, Any, List
from src.backend.adapters.out_bound.persistence_gateway import IPersistenceGateway

router = APIRouter(prefix="/api/v1/registrations", tags=["Registrations"])

_register_usecase: Optional[RegisterCourseUseCase] = None
_drop_usecase: Optional[DropCourseUseCase] = None
_persistence_gateway: Optional[IPersistenceGateway] = None

def set_registration_usecases(
    register_uc: RegisterCourseUseCase,
    drop_uc: DropCourseUseCase,
    persistence_gw: Optional[IPersistenceGateway] = None
):
    global _register_usecase, _drop_usecase, _persistence_gateway
    _register_usecase = register_uc
    _drop_usecase = drop_uc
    _persistence_gateway = persistence_gw

def get_register_usecase() -> RegisterCourseUseCase:
    assert _register_usecase is not None, "RegisterCourseUseCase not initialized"
    return _register_usecase

def get_drop_usecase() -> DropCourseUseCase:
    assert _drop_usecase is not None, "DropCourseUseCase not initialized"
    return _drop_usecase

class RegisterRequest(BaseModel):
    section_id: str = Field(..., description="Mã ID của lớp học phần")
    semester_id: str = Field("sem-2024-1", description="Mã học kỳ")
    prerequisite_course_code: str = Field("NONE", description="Mã môn học tiên quyết (nếu có)")
    section_time_mask: int = Field(..., description="Mặt nạ 84-bit thời gian học")
    credits: int = Field(3, description="Số tín chỉ của môn học")
    student_id: Optional[str] = Field(None, description="Tùy chọn ghi đè mã sinh viên (cho testing)")

class DropRequest(BaseModel):
    student_id: Optional[str] = None
    section_id: str
    credits: int = 3
    section_time_mask: int = 0

@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def register_course(
    req: RegisterRequest,
    request: Request,
    usecase: RegisterCourseUseCase = Depends(get_register_usecase)
):
    student_id = req.student_id or getattr(request.state, "student_id", None)
    if not student_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không tìm thấy thông tin sinh viên"
        )

    command = RegisterCourseCommand(
        student_id=student_id,
        section_id=req.section_id,
        semester_id=req.semester_id,
        prerequisite_course_code=req.prerequisite_course_code,
        section_time_mask=req.section_time_mask,
        credits=req.credits
    )

    try:
        result = await usecase.execute(command)
        return result
    except AlreadyRegisteredException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e.message))
    except SectionFullException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e.message))
    except ScheduleConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e.message))
    except PrerequisiteNotMetException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.message))
    except CreditLimitExceededException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.message))
    except DomainException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.message))

@router.delete("/{registration_id}")
async def drop_course(
    registration_id: str,
    req: DropRequest,
    request: Request,
    usecase: DropCourseUseCase = Depends(get_drop_usecase)
):
    student_id = req.student_id or getattr(request.state, "student_id", None)
    if not student_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không tìm thấy thông tin sinh viên"
        )

    command = DropCourseCommand(
        registration_id=registration_id,
        student_id=student_id,
        section_id=req.section_id,
        credits=req.credits,
        section_time_mask=req.section_time_mask
    )

    return await usecase.execute(command)
@router.get("/student/{student_id}", response_model=List[Dict[str, Any]])
async def get_student_registrations(student_id: str, semester_id: Optional[str] = None):
    """Lấy danh sách các lớp học phần sinh viên đã đăng ký thành công (CONFIRMED)."""
    if not _persistence_gateway:
        return []
    return await _persistence_gateway.get_student_registrations(student_id=student_id, semester_id=semester_id)
