import React, { useState, useMemo } from 'react';
import { Search, Filter, BookOpen, Clock, CheckCircle, AlertTriangle } from 'lucide-react';
import { CourseSectionDTO } from '../types/registration';

interface CourseCatalogProps {
  sections: CourseSectionDTO[];
  enrolledSectionIds: Set<string>;
  onRegister: (section: CourseSectionDTO) => void;
  isLoading: boolean;
}

export const CourseCatalog: React.FC<CourseCatalogProps> = ({
  sections,
  enrolledSectionIds,
  onRegister,
  isLoading,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDept, setSelectedDept] = useState('ALL');
  const [selectedDay, setSelectedDay] = useState('ALL');

  // Lấy danh sách các khoa/bộ môn duy nhất
  const departments = useMemo(() => {
    const set = new Set(sections.map((s) => s.department).filter(Boolean));
    return ['ALL', ...Array.from(set)];
  }, [sections]);

  // Client-side search & filtering cực nhanh trên RAM trình duyệt (Zero CPU trên server)
  const filteredSections = useMemo(() => {
    return sections.filter((sec) => {
      // 1. Lọc theo từ khóa
      if (searchTerm.trim()) {
        const term = searchTerm.toLowerCase();
        const matchCode = sec.course_code.toLowerCase().includes(term);
        const matchName = sec.course_name.toLowerCase().includes(term);
        const matchSec = sec.section_code.toLowerCase().includes(term);
        const matchInstructor = sec.instructor.toLowerCase().includes(term);
        if (!matchCode && !matchName && !matchSec && !matchInstructor) {
          return false;
        }
      }

      // 2. Lọc theo khoa
      if (selectedDept !== 'ALL' && sec.department !== selectedDept) {
        return false;
      }

      // 3. Lọc theo thứ trong tuần
      if (selectedDay !== 'ALL' && sec.schedule_day.toString() !== selectedDay) {
        return false;
      }

      return true;
    });
  }, [sections, searchTerm, selectedDept, selectedDay]);

  const getDayName = (day: number) => {
    return day === 8 ? 'Chủ Nhật' : `Thứ ${day}`;
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-academic-border overflow-hidden flex flex-col h-full">
      {/* Thanh Tiêu Đề & Bộ Lọc Client-side */}
      <div className="p-4 border-b border-academic-border bg-slate-50/50 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-academic-text flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-academic-secondary" />
              Danh Mục Lớp Học Phần Mở
              <span className="text-xs bg-blue-100 text-blue-800 font-semibold px-2 py-0.5 rounded-full font-tabular">
                {filteredSections.length}/{sections.length} lớp
              </span>
            </h2>
            <p className="text-xs text-academic-muted">
              Tra cứu tức thì trong bộ nhớ trình duyệt • Hỗ trợ tìm kiếm theo mã, tên môn và giảng viên
            </p>
          </div>

          {/* Ô Tìm Kiếm Tức Thì */}
          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Tìm môn học, mã lớp, GV... (Ctrl+K)"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-academic-secondary focus:border-transparent transition"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs font-bold"
              >
                ×
              </button>
            )}
          </div>
        </div>

        {/* Bộ Lọc Khoa & Thứ trong tuần */}
        <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
          <span className="text-slate-500 font-medium flex items-center gap-1">
            <Filter className="w-3.5 h-3.5" /> Bộ lọc:
          </span>

          {/* Lọc Khoa */}
          <select
            value={selectedDept}
            onChange={(e) => setSelectedDept(e.target.value)}
            className="bg-white border border-slate-300 rounded-md px-2 py-1 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-academic-secondary"
          >
            <option value="ALL">Tất cả ngành / khoa</option>
            {departments.filter((d) => d !== 'ALL').map((dept) => (
              <option key={dept} value={dept}>
                Khoa {dept}
              </option>
            ))}
          </select>

          {/* Lọc Thứ */}
          <select
            value={selectedDay}
            onChange={(e) => setSelectedDay(e.target.value)}
            className="bg-white border border-slate-300 rounded-md px-2 py-1 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-academic-secondary"
          >
            <option value="ALL">Tất cả các ngày trong tuần</option>
            <option value="2">Thứ Hai</option>
            <option value="3">Thứ Ba</option>
            <option value="4">Thứ Tư</option>
            <option value="5">Thứ Năm</option>
            <option value="6">Thứ Sáu</option>
            <option value="7">Thứ Bảy</option>
          </select>

          {(searchTerm || selectedDept !== 'ALL' || selectedDay !== 'ALL') && (
            <button
              onClick={() => {
                setSearchTerm('');
                setSelectedDept('ALL');
                setSelectedDay('ALL');
              }}
              className="text-academic-secondary hover:underline text-xs ml-auto font-medium"
            >
              Đặt lại bộ lọc
            </button>
          )}
        </div>
      </div>

      {/* Bảng Danh Sách Học Phần */}
      <div className="overflow-x-auto flex-1">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-100/80 text-slate-600 font-semibold border-b border-academic-border uppercase text-[11px] tracking-wider sticky top-0 bg-slate-100 z-10">
              <th className="py-2.5 px-3">Mã Lớp / Môn</th>
              <th className="py-2.5 px-3">Tên Học Phần</th>
              <th className="py-2.5 px-2 text-center">TC</th>
              <th className="py-2.5 px-3">Thời Khóa Biểu</th>
              <th className="py-2.5 px-3">Giảng Viên / Phòng</th>
              <th className="py-2.5 px-3 text-center">Sĩ Số / Còn Lại</th>
              <th className="py-2.5 px-3 text-right">Thao Tác</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {filteredSections.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-slate-400">
                  <div className="flex flex-col items-center justify-center space-y-2">
                    <Search className="w-8 h-8 text-slate-300" />
                    <p className="font-medium">Không tìm thấy lớp học phần phù hợp với bộ lọc</p>
                    <p className="text-xs text-slate-400">Thử tìm kiếm với từ khóa khác hoặc đặt lại bộ lọc</p>
                  </div>
                </td>
              </tr>
            ) : (
              filteredSections.map((sec) => {
                const isEnrolled = enrolledSectionIds.has(sec.id);
                const isFull = sec.available_slots <= 0;
                const isScarce = sec.available_slots > 0 && sec.available_slots < 5;

                return (
                  <tr
                    key={sec.id}
                    className={`hover:bg-blue-50/40 transition-colors ${
                      isEnrolled ? 'bg-emerald-50/30' : ''
                    }`}
                  >
                    {/* Mã lớp & Mã môn */}
                    <td className="py-2.5 px-3 font-medium">
                      <div className="font-bold text-academic-primary font-mono text-[13px]">
                        {sec.section_code}
                      </div>
                      <div className="text-[11px] text-slate-500 font-mono">
                        {sec.course_code}
                      </div>
                    </td>

                    {/* Tên môn & Tiên quyết */}
                    <td className="py-2.5 px-3">
                      <div className="font-semibold text-slate-800 text-xs">
                        {sec.course_name}
                      </div>
                      {sec.prerequisite_course_code && sec.prerequisite_course_code !== 'NONE' ? (
                        <span className="inline-flex items-center gap-1 text-[11px] text-amber-700 bg-amber-50 px-1.5 py-0.2 rounded border border-amber-200/60 mt-0.5">
                          <AlertTriangle className="w-2.5 h-2.5" /> Tiên quyết: {sec.prerequisite_course_code}
                        </span>
                      ) : (
                        <span className="text-[11px] text-slate-400">Không có tiên quyết</span>
                      )}
                    </td>

                    {/* Số tín chỉ */}
                    <td className="py-2.5 px-2 text-center font-bold text-slate-700 font-tabular text-sm">
                      {sec.credits}
                    </td>

                    {/* Lịch học */}
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-1 font-semibold text-slate-700">
                        <Clock className="w-3.5 h-3.5 text-blue-600" />
                        <span>{getDayName(sec.schedule_day)}</span>
                      </div>
                      <div className="text-[11px] text-slate-500 font-tabular">
                        Tiết {sec.start_period} - {sec.end_period}
                      </div>
                    </td>

                    {/* Giảng viên & Phòng */}
                    <td className="py-2.5 px-3">
                      <div className="text-slate-800 font-medium">{sec.instructor}</div>
                      <div className="text-[11px] text-slate-500 font-mono">P. {sec.classroom}</div>
                    </td>

                    {/* Sĩ số & Trạng thái slot */}
                    <td className="py-2.5 px-3 text-center">
                      <div className="font-bold text-slate-800 font-tabular text-xs">
                        {sec.current_enrolled}/{sec.max_capacity}
                      </div>
                      {isFull ? (
                        <span className="inline-block mt-0.5 px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-700 border border-red-200">
                          Hết chỗ
                        </span>
                      ) : isScarce ? (
                        <span className="inline-block mt-0.5 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300 font-tabular animate-pulse">
                          Còn {sec.available_slots} chỗ
                        </span>
                      ) : (
                        <span className="inline-block mt-0.5 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200 font-tabular">
                          Còn {sec.available_slots} chỗ
                        </span>
                      )}
                    </td>

                    {/* Nút hành động */}
                    <td className="py-2.5 px-3 text-right">
                      {isEnrolled ? (
                        <span className="inline-flex items-center gap-1 text-emerald-700 font-bold bg-emerald-100/80 px-2.5 py-1 rounded text-xs border border-emerald-300">
                          <CheckCircle className="w-3.5 h-3.5" /> Đã đăng ký
                        </span>
                      ) : isFull ? (
                        <button
                          disabled
                          className="px-3 py-1 bg-slate-100 text-slate-400 font-semibold rounded text-xs cursor-not-allowed border border-slate-200"
                        >
                          Hết chỗ
                        </button>
                      ) : (
                        <button
                          onClick={() => onRegister(sec)}
                          disabled={isLoading}
                          className="px-3 py-1 bg-academic-secondary hover:bg-blue-700 active:bg-blue-800 text-white font-semibold rounded text-xs transition-colors shadow-sm disabled:opacity-50"
                        >
                          Đăng ký
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
