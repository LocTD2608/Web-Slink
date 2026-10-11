import React, { useState, useEffect, useMemo } from 'react';
import { Header } from './components/Header';
import { CourseCatalog } from './components/CourseCatalog';
import { TimetableMatrix } from './components/TimetableMatrix';
import { RegisteredList } from './components/RegisteredList';
import { WaitingRoomModal } from './components/WaitingRoomModal';
import { ExceptionModal } from './components/ExceptionModal';

import { CourseSectionDTO, StudentProfile, FeedbackModalState } from './types/registration';
import { fetchSections, submitRegistration, dropRegistration } from './services/api';
import { startControlledShortPolling } from './services/pollingService';

export const App: React.FC = () => {
  // 1. Hồ sơ sinh viên mẫu (demo)
  const [student, setStudent] = useState<StudentProfile>({
    id: 'std-0001',
    student_code: 'SV20240001',
    full_name: 'Nguyễn Văn A',
    major: 'Khoa Công Nghệ Thông Tin',
    max_credits: 24,
    current_credits: 0,
  });

  // 2. Dữ liệu danh mục và học phần đã đăng ký
  const [sections, setSections] = useState<CourseSectionDTO[]>([]);
  const [enrolledSections, setEnrolledSections] = useState<CourseSectionDTO[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'CATALOG' | 'TIMETABLE'>('CATALOG');

  // 3. Trạng thái Modal phòng chờ (Waiting Room)
  const [waitingState, setWaitingState] = useState<{
    isOpen: boolean;
    ticketId: string;
    attempt: number;
    section: CourseSectionDTO | null;
  }>({
    isOpen: false,
    ticketId: '',
    attempt: 0,
    section: null,
  });

  // 4. Trạng thái Modal thông báo nghiệp vụ (Feedback Modals)
  const [modalState, setModalState] = useState<FeedbackModalState>({
    isOpen: false,
    type: 'SUCCESS',
    title: '',
    message: '',
  });

  // Tải danh mục lớp học phần từ backend
  useEffect(() => {
    async function loadCatalog() {
      try {
        const data = await fetchSections();
        setSections(data);
      } catch (err: any) {
        console.error('Lỗi nạp danh mục:', err);
      }
    }
    loadCatalog();
  }, []);

  const enrolledSectionIds = useMemo(() => {
    return new Set(enrolledSections.map((s) => s.id));
  }, [enrolledSections]);

  // Cập nhật lại số tín chỉ khi danh sách thay đổi
  useEffect(() => {
    const total = enrolledSections.reduce((acc, curr) => acc + curr.credits, 0);
    setStudent((prev) => ({ ...prev, current_credits: total }));
  }, [enrolledSections]);

  // Xử lý gửi yêu cầu đăng ký học phần
  const handleRegister = async (section: CourseSectionDTO) => {
    setIsLoading(true);

    try {
      // Gửi yêu cầu đăng ký (nhận 202 Accepted tức thì từ Redis)
      const res = await submitRegistration({
        section_id: section.id,
        semester_id: 'sem-2024-1',
        prerequisite_course_code: section.prerequisite_course_code || 'NONE',
        section_time_mask: section.time_mask,
        credits: section.credits,
        student_id: student.id,
      });

      // Mở modal phòng chờ (Waiting Room)
      setWaitingState({
        isOpen: true,
        ticketId: res.ticket_id,
        attempt: 1,
        section,
      });

      // Kích hoạt Controlled Short Polling thăm dò mỗi 1.0s
      startControlledShortPolling({
        ticketId: res.ticket_id,
        intervalMs: 1000,
        maxAttempts: 3,
        onUpdate: (_data, attempt) => {
          setWaitingState((prev) => ({ ...prev, attempt }));
        },
        onSuccess: () => {
          setWaitingState((prev) => ({ ...prev, isOpen: false }));
          setEnrolledSections((prev) => [...prev, section]);
          setIsLoading(false);

          setModalState({
            isOpen: true,
            type: 'SUCCESS',
            title: 'Ghi Danh Học Phần Thành Công!',
            sectionCode: section.section_code,
            message: `Học phần "${section.course_name}" (${section.credits} tín chỉ) đã được xác nhận lưu trữ bền vững vào hệ thống đào tạo.`,
          });
        },
        onFailed: (data) => {
          setWaitingState((prev) => ({ ...prev, isOpen: false }));
          setIsLoading(false);

          setModalState({
            isOpen: true,
            type: 'ERROR',
            title: 'Đăng Ký Thất Bại',
            sectionCode: section.section_code,
            message: data.reason || 'Không thể lưu trữ vào cơ sở dữ liệu. Slot đã được tự động hoàn trả.',
          });
        },
      });
    } catch (err: any) {
      setIsLoading(false);
      const detail = err.message || 'Lỗi không xác định khi đăng ký';

      let modalType: FeedbackModalState['type'] = 'ERROR';
      let title = 'Không Thể Đăng Ký';

      if (detail.includes('hết chỗ')) {
        modalType = 'FULL';
        title = 'Lớp Học Phần Đã Hết Chỗ';
      } else if (detail.includes('trùng lịch')) {
        modalType = 'CONFLICT';
        title = 'Xung Đột Thời Khóa Biểu';
      } else if (detail.includes('tiên quyết')) {
        modalType = 'PREREQ';
        title = 'Chưa Đạt Môn Tiên Quyết';
      }

      setModalState({
        isOpen: true,
        type: modalType,
        title,
        sectionCode: section.section_code,
        message: detail,
      });
    }
  };

  // Xử lý hủy môn học
  const handleDrop = async (section: CourseSectionDTO) => {
    if (!window.confirm(`Bạn có chắc chắn muốn hủy đăng ký lớp ${section.section_code} (${section.course_name})?`)) {
      return;
    }

    setIsLoading(true);
    try {
      await dropRegistration(
        `reg-${section.id}`,
        section.id,
        section.credits,
        section.time_mask,
        student.id
      );

      setEnrolledSections((prev) => prev.filter((s) => s.id !== section.id));
      setIsLoading(false);
      setModalState({
        isOpen: true,
        type: 'SUCCESS',
        title: 'Hủy Môn Thành Công',
        sectionCode: section.section_code,
        message: `Đã hủy học phần "${section.course_name}". Sĩ số khả dụng đã được hoàn trả lập tức vào hệ thống.`,
      });
    } catch (err: any) {
      setIsLoading(false);
      alert(`Lỗi hủy môn: ${err.message}`);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-academic-canvas">
      {/* 1. Header chuẩn Stitch */}
      <Header student={student} />

      {/* 2. Nội dung chính */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Navigation Tabs */}
        <div className="flex items-center space-x-2 border-b border-academic-border pb-2">
          <button
            onClick={() => setActiveTab('CATALOG')}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition-all ${
              activeTab === 'CATALOG'
                ? 'bg-academic-primary text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-200/60'
            }`}
          >
            Danh Mục Lớp Mở ({sections.length})
          </button>
          <button
            onClick={() => setActiveTab('TIMETABLE')}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition-all ${
              activeTab === 'TIMETABLE'
                ? 'bg-academic-primary text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-200/60'
            }`}
          >
            Ma Trận Thời Khóa Biểu ({enrolledSections.length} môn)
          </button>
        </div>

        {/* Tab 1: Danh Mục Học Phần (Client-side Search) */}
        {activeTab === 'CATALOG' ? (
          <div className="grid grid-cols-1 gap-6">
            <CourseCatalog
              sections={sections}
              enrolledSectionIds={enrolledSectionIds}
              onRegister={handleRegister}
              isLoading={isLoading}
            />
          </div>
        ) : (
          /* Tab 2: Ma Trận Thời Khóa Biểu Tuần */
          <div className="grid grid-cols-1 gap-6">
            <TimetableMatrix enrolledSections={enrolledSections} />
          </div>
        )}

        {/* Kết Quả Đã Đăng Ký (Luôn hiển thị ở dưới để theo dõi) */}
        <RegisteredList
          enrolledSections={enrolledSections}
          onDrop={handleDrop}
          isLoading={isLoading}
        />
      </main>

      {/* 3. Footer */}
      <footer className="border-t border-academic-border bg-white py-4 text-center text-xs text-slate-500">
        Hệ thống Đăng ký Học phần Trực tuyến (Quy mô 3.000 Sinh viên) • Kiến trúc Monorepo Clean Architecture
      </footer>

      {/* 4. Modals */}
      <WaitingRoomModal
        isOpen={waitingState.isOpen}
        ticketId={waitingState.ticketId}
        attempt={waitingState.attempt}
        sectionCode={waitingState.section?.section_code || ''}
        courseName={waitingState.section?.course_name || ''}
      />

      <ExceptionModal
        modal={modalState}
        onClose={() => setModalState((prev) => ({ ...prev, isOpen: false }))}
      />
    </div>
  );
};
