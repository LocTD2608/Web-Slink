from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Registration:
    id: str
    ticket_id: str
    student_id: str
    section_id: str
    semester_id: str
    status: str = "CONFIRMED" # PENDING, CONFIRMED, CANCELLED, FAILED
    registered_at: Optional[datetime] = None
