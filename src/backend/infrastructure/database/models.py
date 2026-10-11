from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, BigInteger, Numeric, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

def generate_uuid() -> str:
    return str(uuid.uuid4())

class StudentModel(Base):
    __tablename__ = "students"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    student_code = Column(String(20), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    major = Column(String(50), nullable=False)
    academic_year = Column(Integer, nullable=False)
    max_credits = Column(Integer, default=24, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    registrations = relationship("RegistrationModel", back_populates="student")

class CourseModel(Base):
    __tablename__ = "courses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    course_code = Column(String(20), unique=True, nullable=False, index=True)
    course_name = Column(String(150), nullable=False)
    credits = Column(Integer, nullable=False)
    prerequisite_course_id = Column(String(36), ForeignKey("courses.id"), nullable=True)
    prerequisite_course = relationship("CourseModel", remote_side=[id])
    department = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SemesterModel(Base):
    __tablename__ = "semesters"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    semester_code = Column(String(20), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)

class CourseSectionModel(Base):
    __tablename__ = "course_sections"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    section_code = Column(String(30), unique=True, nullable=False, index=True)
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False)
    semester_id = Column(String(36), ForeignKey("semesters.id"), nullable=False, index=True)
    instructor = Column(String(100), nullable=False)
    classroom = Column(String(50), nullable=False)
    schedule_day = Column(Integer, nullable=False) # 2 -> 8
    start_period = Column(Integer, nullable=False) # 1 -> 12
    end_period = Column(Integer, nullable=False)   # 1 -> 12
    time_mask = Column(Numeric(38, asdecimal=False), nullable=False)
    max_capacity = Column(Integer, nullable=False)
    current_enrolled = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    registrations = relationship("RegistrationModel", back_populates="section")

class RegistrationModel(Base):
    __tablename__ = "registrations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    ticket_id = Column(String(64), unique=True, nullable=False, index=True)
    student_id = Column(String(36), ForeignKey("students.id"), nullable=False, index=True)
    section_id = Column(String(36), ForeignKey("course_sections.id"), nullable=False, index=True)
    semester_id = Column(String(36), ForeignKey("semesters.id"), nullable=False)
    status = Column(String(20), default="CONFIRMED", nullable=False) # CONFIRMED, CANCELLED, FAILED
    registered_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("StudentModel", back_populates="registrations")
    section = relationship("CourseSectionModel", back_populates="registrations")

    __table_args__ = (
        UniqueConstraint("student_id", "section_id", name="uq_student_section"),
    )
