export interface CourseSectionDTO {
  id: string;
  section_code: string;
  course_code: string;
  course_name: string;
  credits: number;
  prerequisite_course_code?: string;
  instructor: string;
  classroom: string;
  schedule_day: number; // 2 -> 7 (Mon -> Sat)
  start_period: number; // 1 -> 12
  end_period: number;
  time_slots: number[];
  registration_id?: string;
  ticket_id?: string;
  max_capacity: number;
  current_enrolled: number;
  available_slots: number;
  department: string;
}

export interface RegisterRequestPayload {
  section_id: string;
}

export interface TicketStatusDTO {
  ticket_id: string;
  status: 'PENDING' | 'CONFIRMED' | 'FAILED' | 'CANCEL_PENDING' | 'CANCELLED';
  reason?: string;
}

export interface StudentProfile {
  id: string;
  student_code: string;
  full_name: string;
  major: string;
  max_credits: number;
  current_credits: number;
}

export interface FeedbackModalState {
  isOpen: boolean;
  type: 'SUCCESS' | 'CONFLICT' | 'FULL' | 'PREREQ' | 'ERROR';
  title: string;
  message: string;
  sectionCode?: string;
}
