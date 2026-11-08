from dataclasses import dataclass, asdict

@dataclass
class Operation:
    ticket_id: str
    student_id: str
    section_id: str
    kind: str
    status: str
    generation: int = 0
    reason: str = ""
    registration_id: str | None = None

    def to_dict(self):
        return asdict(self)

class RegistrationError(ValueError):
    def __init__(self, code: str, status_code: int = 409):
        super().__init__(code)
        self.code = code
        self.status_code = status_code
