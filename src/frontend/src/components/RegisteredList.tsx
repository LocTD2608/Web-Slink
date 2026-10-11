import React from 'react';
import { CheckCircle2, Trash2, BookOpen, Clock } from 'lucide-react';
import { CourseSectionDTO } from '../types/registration';

interface RegisteredListProps {
  enrolledSections: CourseSectionDTO[];
  onDrop: (section: CourseSectionDTO) => void;
  isLoading: boolean;
}

export const RegisteredList: React.FC<RegisteredListProps> = ({
  enrolledSections,
  onDrop,
  isLoading,
}) => {
  const totalCredits = enrolledSections.reduce((acc, curr) => acc + curr.credits, 0);

  const getDayName = (day: number) => {
    return day === 8 ? 'Chủ Nhật' : `Thứ ${day}`;
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-academic-border overflow-hidden">
      <div className="p-4 border-b border-academic-border bg-slate-50/50 flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-academic-text flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-academic-success" />
            Kết Quả Ghi Danh Chính Thức
            <span className="text-xs bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded-full font-tabular">
              {enrolledSections.length} học phần ({totalCredits} tín chỉ)
            </span>
          </h2>
          <p className="text-xs text-academic-muted">
            Danh sách các học phần đã được ghi nhận bền vững (Persisted ACID) vào CSDL
          </p>
        </div>
      </div>

      <div className="p-4">
        {enrolledSections.length === 0 ? (
          <div className="py-8 text-center text-slate-400 flex flex-col items-center justify-center space-y-2">
            <BookOpen className="w-8 h-8 text-slate-300" />
            <p className="text-xs font-medium">Bạn chưa đăng ký học phần nào trong học kỳ này.</p>
            <p className="text-[11px] text-slate-400">Chọn các học phần trong bảng danh mục phía trên để tiến hành đăng ký.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100 border border-slate-200 rounded-lg overflow-hidden">
            {enrolledSections.map((sec) => (
              <div
                key={sec.id}
                className="p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50 transition"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-academic-primary font-mono text-xs">
                      {sec.section_code}
                    </span>
                    <span className="text-xs font-semibold text-slate-800">
                      {sec.course_name}
                    </span>
                    <span className="text-[11px] bg-blue-100 text-blue-800 font-bold px-1.5 py-0.2 rounded font-tabular">
                      {sec.credits} TC
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-500 font-tabular">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {getDayName(sec.schedule_day)} (Tiết {sec.start_period}-{sec.end_period})
                    </span>
                    <span>•</span>
                    <span>Phòng: {sec.classroom}</span>
                    <span>•</span>
                    <span>GV: {sec.instructor}</span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-[11px] text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded font-semibold flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                    Đã lưu CSDL
                  </span>
                  <button
                    onClick={() => onDrop(sec)}
                    disabled={isLoading}
                    className="p-1.5 text-red-600 hover:text-red-700 hover:bg-red-50 rounded-md transition border border-red-200 text-xs font-semibold flex items-center gap-1 disabled:opacity-50"
                    title="Hủy học phần này"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Hủy</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
