from dataclasses import dataclass, field
from typing import Set
from src.backend.core.domain.entities.course_section import CourseSection
from src.backend.core.domain.exceptions.registration_exceptions import (
    SectionFullException,
    ScheduleConflictException,
    PrerequisiteNotMetException,
    CreditLimitExceededException,
)

@dataclass
class Student:
    id: str
    student_code: str
    full_name: str
    max_credits: int = 24
    current_credits: int = 0
    completed_course_codes: Set[str] = field(default_factory=set)
    registered_time_mask: int = 0
    enrolled_section_ids: Set[str] = field(default_factory=set)

    def validate_can_enroll(self, section: CourseSection) -> None:
        # 1. Kiểm tra sĩ số lớp
        if section.is_full:
            raise SectionFullException(f"Lớp {section.section_code} đã hết chỗ ({section.current_enrolled}/{section.max_capacity})")

        # 2. Kiểm tra môn tiên quyết
        if section.prerequisite_course_code:
            if section.prerequisite_course_code not in self.completed_course_codes:
                raise PrerequisiteNotMetException(
                    f"Cần hoàn thành môn tiên quyết {section.prerequisite_course_code} trước khi đăng ký {section.course_code}"
                )

        # 3. Kiểm tra hạn mức tín chỉ
        if self.current_credits + section.credits > self.max_credits:
            raise CreditLimitExceededException(
                f"Đăng ký {section.credits} tín chỉ sẽ vượt quá hạn mức tối đa ({self.current_credits + section.credits} > {self.max_credits})"
            )

        # 4. Kiểm tra trùng lịch thời khóa biểu (BITOP AND)
        section_mask = section.time_mask
        if (self.registered_time_mask & section_mask) != 0:
            raise ScheduleConflictException(
                f"Lớp {section.section_code} bị trùng lịch học với thời khóa biểu hiện tại (Thứ {section.schedule_day}, Tiết {section.start_period}-{section.end_period})"
            )

    def enroll_section(self, section: CourseSection) -> None:
        self.validate_can_enroll(section)
        self.registered_time_mask |= section.time_mask
        self.current_credits += section.credits
        self.enrolled_section_ids.add(section.id)
        section.current_enrolled += 1

    def drop_section(self, section: CourseSection) -> None:
        if section.id in self.enrolled_section_ids:
            self.enrolled_section_ids.remove(section.id)
            self.registered_time_mask &= ~section.time_mask
            self.current_credits = max(0, self.current_credits - section.credits)
            section.current_enrolled = max(0, section.current_enrolled - 1)
