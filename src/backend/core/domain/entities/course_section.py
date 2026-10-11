from dataclasses import dataclass
from typing import Optional
from src.backend.core.domain.entities.time_slot import TimeSlot

@dataclass
class CourseSection:
    id: str
    section_code: str
    course_code: str
    credits: int
    max_capacity: int
    current_enrolled: int
    schedule_day: int
    start_period: int
    end_period: int
    prerequisite_course_code: Optional[str] = None
    instructor: str = "TBA"
    classroom: str = "TBA"
    course_name: str = ""

    @property
    def available_slots(self) -> int:
        return max(0, self.max_capacity - self.current_enrolled)

    @property
    def is_full(self) -> bool:
        return self.current_enrolled >= self.max_capacity

    @property
    def time_mask(self) -> int:
        return TimeSlot(
            schedule_day=self.schedule_day,
            start_period=self.start_period,
            end_period=self.end_period
        ).compute_mask()
