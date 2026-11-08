from dataclasses import dataclass, field

@dataclass
class RegistrationContext:
    student_id: str
    section_id: str
    semester_id: str
    credits: int
    max_credits: int
    prerequisite_course_code: str | None
    time_slots: list[int]
    run_id: str | None = None
    generation: int = 0
    completed_courses: list[str] = field(default_factory=list)
