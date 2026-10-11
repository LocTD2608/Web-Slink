import unittest
from src.backend.core.domain.entities.time_slot import TimeSlot
from src.backend.core.domain.entities.student import Student
from src.backend.core.domain.entities.course_section import CourseSection
from src.backend.core.domain.exceptions.registration_exceptions import (
    SectionFullException,
    ScheduleConflictException,
    PrerequisiteNotMetException,
    CreditLimitExceededException,
)

class TestDomainRules(unittest.TestCase):
    def setUp(self):
        # Student with 24 max credits, passed CS101, initially 0 credits
        self.student = Student(
            id="std-001",
            student_code="SV2024001",
            full_name="Nguyen Van A",
            max_credits=24,
            current_credits=0,
            completed_course_codes={"CS101"},
            registered_time_mask=0
        )

    def test_time_slot_bitmap_calculation(self):
        # Monday (day 2), periods 1 to 3 -> bits 0, 1, 2
        slot = TimeSlot(schedule_day=2, start_period=1, end_period=3)
        expected_mask = (1 << 0) | (1 << 1) | (1 << 2)  # 7
        self.assertEqual(slot.compute_mask(), expected_mask)

    def test_schedule_conflict_detection(self):
        # Section A on Monday periods 1-3
        section_a = CourseSection(
            id="sec-001",
            section_code="CS102-01",
            course_code="CS102",
            credits=3,
            max_capacity=30,
            current_enrolled=10,
            schedule_day=2,
            start_period=1,
            end_period=3
        )
        self.student.enroll_section(section_a)
        self.assertEqual(self.student.current_credits, 3)

        # Section B on Monday periods 2-4 -> Conflicts on periods 2 & 3
        section_b = CourseSection(
            id="sec-002",
            section_code="MATH101-01",
            course_code="MATH101",
            credits=3,
            max_capacity=30,
            current_enrolled=5,
            schedule_day=2,
            start_period=2,
            end_period=4
        )
        with self.assertRaises(ScheduleConflictException):
            self.student.validate_can_enroll(section_b)

    def test_prerequisite_course_validation(self):
        # Section requires CS101 which student already completed
        section_adv = CourseSection(
            id="sec-003",
            section_code="CS201-01",
            course_code="CS201",
            prerequisite_course_code="CS101",
            credits=3,
            max_capacity=30,
            current_enrolled=10,
            schedule_day=3,
            start_period=1,
            end_period=3
        )
        # Should pass
        self.student.validate_can_enroll(section_adv)

        # Section requires CS301 which student has NOT completed
        section_master = CourseSection(
            id="sec-004",
            section_code="CS401-01",
            course_code="CS401",
            prerequisite_course_code="CS301",
            credits=3,
            max_capacity=30,
            current_enrolled=10,
            schedule_day=4,
            start_period=1,
            end_period=3
        )
        with self.assertRaises(PrerequisiteNotMetException):
            self.student.validate_can_enroll(section_master)

    def test_credit_limit_exceeded(self):
        self.student.current_credits = 22
        # Adding a 3-credit course exceeds 24 limit
        section = CourseSection(
            id="sec-005",
            section_code="PHYS101-01",
            course_code="PHYS101",
            credits=3,
            max_capacity=30,
            current_enrolled=10,
            schedule_day=5,
            start_period=1,
            end_period=3
        )
        with self.assertRaises(CreditLimitExceededException):
            self.student.validate_can_enroll(section)

    def test_section_full_exception(self):
        section_full = CourseSection(
            id="sec-006",
            section_code="CHEM101-01",
            course_code="CHEM101",
            credits=3,
            max_capacity=30,
            current_enrolled=30,
            schedule_day=6,
            start_period=1,
            end_period=3
        )
        with self.assertRaises(SectionFullException):
            self.student.validate_can_enroll(section_full)

if __name__ == "__main__":
    unittest.main()
