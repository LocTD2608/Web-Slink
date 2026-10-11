import os
import sys
import asyncio
import random

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.backend.infrastructure.database.db_connection import AsyncSessionLocal, create_tables
from src.backend.infrastructure.database.models import (
    StudentModel,
    CourseModel,
    SemesterModel,
    CourseSectionModel
)
from src.backend.core.domain.entities.time_slot import TimeSlot

COURSES_SPEC = [
    ("CS101", "Nhập môn Lập trình", 3, None, "CNTT"),
    ("CS102", "Kỹ thuật Lập trình", 3, "CS101", "CNTT"),
    ("CS201", "Cấu trúc Dữ liệu & Giải thuật", 4, "CS102", "CNTT"),
    ("CS202", "Cơ sở Dữ liệu", 3, "CS101", "HTTT"),
    ("CS203", "Kiến trúc Máy tính", 3, None, "KTPM"),
    ("CS301", "Mạng Máy tính", 3, "CS203", "MMT"),
    ("CS302", "Hệ Điều hành", 3, "CS203", "CNTT"),
    ("CS303", "Công nghệ Phần mềm", 3, "CS201", "KTPM"),
    ("CS304", "Lập trình Web Nâng cao", 3, "CS202", "HTTT"),
    ("CS305", "Trí tuệ Nhân tạo", 4, "CS201", "KHMT"),
    ("CS306", "Học máy Cơ bản", 3, "CS305", "KHMT"),
    ("CS307", "An toàn & Bảo mật Thông tin", 3, "CS301", "ATTT"),
    ("CS308", "Phát triển Ứng dụng Di động", 3, "CS303", "KTPM"),
    ("CS309", "Điện toán Đám mây & DevOps", 3, "CS301", "CNTT"),
    ("CS310", "Xử lý Ngôn ngữ Tự nhiên", 3, "CS306", "KHMT"),
    ("MATH101", "Giải tích 1", 3, None, "TOAN"),
    ("MATH102", "Đại số Tuyến tính", 3, None, "TOAN"),
    ("MATH201", "Xác suất Thống kê", 3, "MATH101", "TOAN"),
    ("MATH202", "Toán Rời rạc", 3, None, "TOAN"),
    ("PHYS101", "Vật lý Đại cương", 3, None, "VATLY"),
    ("ENG101", "Tiếng Anh Chuyên ngành 1", 2, None, "NGOAINGU"),
    ("ENG102", "Tiếng Anh Chuyên ngành 2", 2, "ENG101", "NGOAINGU"),
    ("MGMT101", "Kinh tế Đại cương", 2, None, "KINHTE"),
    ("LAW101", "Pháp luật Đại cương", 2, None, "LUAT"),
    ("CS401", "Đồ án Tốt nghiệp", 6, "CS303", "CNTT"),
    ("CS402", "Thực tập Doanh nghiệp", 4, "CS303", "CNTT"),
    ("CS403", "Kiểm thử Phần mềm", 3, "CS303", "KTPM"),
    ("CS404", "Hệ thống Phân tán", 3, "CS301", "CNTT"),
    ("CS405", "Thị giác Máy tính", 3, "CS305", "KHMT"),
    ("CS406", "Quản trị Dự án CNTT", 3, None, "HTTT")
]

INSTRUCTORS = [
    "TS. Nguyễn Văn Hùng", "PGS.TS. Trần Đình Long", "ThS. Lê Thị Mai",
    "TS. Phạm Quốc Bảo", "ThS. Hoàng Minh Tuấn", "PGS.TS. Đỗ Thị Thu",
    "TS. Vũ Hải Đăng", "ThS. Ngô Văn Nam", "TS. Bùi Đức Thành"
]

ROOMS = ["A1-201", "A1-305", "B2-102", "B2-401", "C3-101", "C3-205", "E1-502", "Lab-01", "Lab-02"]

PERIOD_RANGES = [(1, 3), (4, 6), (7, 9), (10, 12)]

async def init_database():
    print("Creating tables in PostgreSQL...")
    await create_tables()
    
    async with AsyncSessionLocal() as session:
        print("Seeding Semester...")
        semester = SemesterModel(
            id="sem-2024-1",
            semester_code="2024-1",
            name="Học kỳ 1 Năm học 2024-2025",
            is_active=True
        )
        session.add(semester)

        print("Seeding 30 Courses...")
        course_map = {}
        for code, name, credits, prereq, dept in COURSES_SPEC:
            course = CourseModel(
                id=f"course-{code.lower()}",
                course_code=code,
                course_name=name,
                credits=credits,
                department=dept
            )
            session.add(course)
            course_map[code] = course

        await session.flush()

        # Update prerequisite links
        for code, name, credits, prereq, dept in COURSES_SPEC:
            if prereq and prereq in course_map:
                course_map[code].prerequisite_course_id = course_map[prereq].id

        print("Seeding 200 Course Sections...")
        section_idx = 1
        # Loop through courses to create approximately 200 sections
        while section_idx <= 200:
            for code, name, credits, prereq, dept in COURSES_SPEC:
                if section_idx > 200:
                    break
                
                day = random.randint(2, 7) # Mon -> Sat
                start_p, end_p = random.choice(PERIOD_RANGES)
                mask = TimeSlot(schedule_day=day, start_period=start_p, end_period=end_p).compute_mask()
                
                section = CourseSectionModel(
                    id=f"sec-{section_idx:03d}",
                    section_code=f"{code}-{section_idx % 5 + 1:02d}",
                    course_id=course_map[code].id,
                    semester_id="sem-2024-1",
                    instructor=random.choice(INSTRUCTORS),
                    classroom=random.choice(ROOMS),
                    schedule_day=day,
                    start_period=start_p,
                    end_period=end_p,
                    time_mask=mask,
                    max_capacity=30 if section_idx == 1 else random.choice([30, 40, 50]),
                    current_enrolled=0
                )
                session.add(section)
                section_idx += 1

        print("Seeding 3.000 Students...")
        BATCH_SIZE = 500
        for b in range(0, 3000, BATCH_SIZE):
            for i in range(b + 1, b + BATCH_SIZE + 1):
                student = StudentModel(
                    id=f"std-{i:04d}",
                    student_code=f"SV2024{i:04d}",
                    full_name=f"Sinh Viên {i:04d}",
                    email=f"sv{i:04d}@daihoc.edu.vn",
                    major=random.choice(["CNTT", "KTPM", "HTTT", "KHMT", "ATTT"]),
                    academic_year=random.choice([2021, 2022, 2023, 2024]),
                    max_credits=24
                )
                session.add(student)
            await session.flush()
            print(f"  Flushed students up to {b + BATCH_SIZE}...")

        await session.commit()
        print("Database initialization successfully completed! (3.000 Students, 30 Courses, 200 Sections)")

if __name__ == "__main__":
    asyncio.run(init_database())
