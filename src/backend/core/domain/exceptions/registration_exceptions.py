class DomainException(Exception):
    """Ngoại lệ cơ sở cho các vi phạm quy tắc nghiệp vụ domain."""
    def __init__(self, message: str, error_code: str = "DOMAIN_ERROR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code

class SectionFullException(DomainException):
    def __init__(self, message: str = "Lớp học phần đã hết chỗ khả dụng"):
        super().__init__(message, "SECTION_FULL")

class ScheduleConflictException(DomainException):
    def __init__(self, message: str = "Trùng lịch học với học phần đã đăng ký trong tuần"):
        super().__init__(message, "SCHEDULE_CONFLICT")

class PrerequisiteNotMetException(DomainException):
    def __init__(self, message: str = "Sinh viên chưa hoàn thành môn học tiên quyết bắt buộc"):
        super().__init__(message, "PREREQUISITE_NOT_MET")

class CreditLimitExceededException(DomainException):
    def __init__(self, message: str = "Vượt quá giới hạn số tín chỉ tối đa được phép đăng ký trong kỳ"):
        super().__init__(message, "CREDIT_LIMIT_EXCEEDED")

class AlreadyRegisteredException(DomainException):
    def __init__(self, message: str = "Sinh viên đã đăng ký học phần này"):
        super().__init__(message, "ALREADY_REGISTERED")
