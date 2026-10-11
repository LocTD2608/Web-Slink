from fastapi import APIRouter, Depends, Query
from typing import List, Dict, Any, Optional
from src.backend.core.usecases.view_curriculum import ViewCurriculumUseCase

router = APIRouter(prefix="/api/v1/sections", tags=["Catalog"])

# Dependency container injection
_curriculum_usecase: Optional[ViewCurriculumUseCase] = None

def set_curriculum_usecase(usecase: ViewCurriculumUseCase):
    global _curriculum_usecase
    _curriculum_usecase = usecase

def get_curriculum_usecase() -> ViewCurriculumUseCase:
    assert _curriculum_usecase is not None, "CurriculumUseCase not initialized"
    return _curriculum_usecase

@router.get("", response_model=List[Dict[str, Any]])
async def get_sections(
    semester_id: Optional[str] = Query(None, description="Mã học kỳ tra cứu"),
    usecase: ViewCurriculumUseCase = Depends(get_curriculum_usecase)
):
    """
    Tra cứu toàn bộ danh mục 150-200 lớp học phần đang mở.
    Dữ liệu được nạp sẵn trên Redis In-Memory key 'catalog:active_sections'.
    Phản hồi cực nhanh (< 1ms). Frontend thực hiện toàn bộ việc tìm kiếm và lọc Client-side.
    """
    return await usecase.execute(semester_id=semester_id)
