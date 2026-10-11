import React from 'react';
import { Calendar, Clock } from 'lucide-react';
import { CourseSectionDTO } from '../types/registration';

interface TimetableMatrixProps {
  enrolledSections: CourseSectionDTO[];
}

const DAYS = [
  { day: 2, name: 'Thứ Hai' },
  { day: 3, name: 'Thứ Ba' },
  { day: 4, name: 'Thứ Tư' },
  { day: 5, name: 'Thứ Năm' },
  { day: 6, name: 'Thứ Sáu' },
  { day: 7, name: 'Thứ Bảy' },
];

const PERIOD_SLOTS = [
  { period: 1, time: '07:00 - 07:50' },
  { period: 2, time: '07:55 - 08:45' },
  { period: 3, time: '08:50 - 09:40' },
  { period: 4, time: '09:45 - 10:35' },
  { period: 5, time: '10:40 - 11:30' },
  { period: 6, time: '12:30 - 13:20' },
  { period: 7, time: '13:25 - 14:15' },
  { period: 8, time: '14:20 - 15:10' },
  { period: 9, time: '15:15 - 16:05' },
  { period: 10, time: '16:10 - 17:00' },
  { period: 11, time: '17:30 - 18:20' },
  { period: 12, time: '18:25 - 19:15' },
];

export const TimetableMatrix: React.FC<TimetableMatrixProps> = ({ enrolledSections }) => {
  // Tìm section chiếm slot (day, period)
  const getSectionForSlot = (day: number, period: number) => {
    return enrolledSections.find(
      (sec) => sec.schedule_day === day && period >= sec.start_period && period <= sec.end_period
    );
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-academic-border overflow-hidden">
      <div className="p-4 border-b border-academic-border bg-slate-50/50 flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-academic-text flex items-center gap-2">
            <Calendar className="w-5 h-5 text-academic-secondary" />
            Thời Khóa Biểu Tuần Trực Quan
          </h2>
          <p className="text-xs text-academic-muted">
            Trực quan hóa ma trận lịch học 6 ngày trong tuần • Tự động phát hiện và cảnh báo xung đột tiết học
          </p>
        </div>
      </div>

      <div className="overflow-x-auto p-4">
        <div className="min-w-[650px] border border-slate-200 rounded-lg overflow-hidden">
          {/* Header Row: Days of Week */}
          <div className="grid grid-cols-7 bg-slate-100 text-slate-700 font-bold text-xs text-center border-b border-slate-200">
            <div className="py-2.5 px-2 border-r border-slate-200 flex items-center justify-center gap-1">
              <Clock className="w-3.5 h-3.5 text-slate-500" />
              <span>Tiết / Giờ</span>
            </div>
            {DAYS.map((d) => (
              <div key={d.day} className="py-2.5 px-2 border-r border-slate-200 last:border-r-0">
                {d.name}
              </div>
            ))}
          </div>

          {/* Matrix Rows: 12 Periods */}
          <div className="divide-y divide-slate-200">
            {PERIOD_SLOTS.map(({ period, time }) => (
              <div key={period} className="grid grid-cols-7 text-xs items-stretch min-h-[44px]">
                {/* Cột Tiết & Giờ */}
                <div className="bg-slate-50 border-r border-slate-200 p-1.5 flex flex-col justify-center items-center font-mono">
                  <span className="font-bold text-slate-800 text-xs">Tiết {period}</span>
                  <span className="text-[10px] text-slate-400 font-tabular">{time}</span>
                </div>

                {/* 6 Cột từ Thứ 2 đến Thứ 7 */}
                {DAYS.map(({ day }) => {
                  const sec = getSectionForSlot(day, period);
                  const isFirstPeriod = sec && sec.start_period === period;

                  return (
                    <div
                      key={day}
                      className="border-r border-slate-200 last:border-r-0 p-1 relative flex items-center justify-center"
                    >
                      {sec ? (
                        <div
                          className={`w-full h-full rounded p-1.5 flex flex-col justify-center transition-all ${
                            isFirstPeriod ? 'bg-blue-600 text-white shadow-sm' : 'bg-blue-500/90 text-white'
                          }`}
                        >
                          <div className="font-bold text-[11px] leading-tight flex justify-between items-center">
                            <span>{sec.section_code}</span>
                            <span className="text-[10px] opacity-80">{sec.credits}TC</span>
                          </div>
                          {isFirstPeriod && (
                            <div className="text-[10px] font-medium opacity-90 truncate mt-0.5">
                              {sec.course_name}
                            </div>
                          )}
                          <div className="text-[9px] opacity-75 truncate">
                            P.{sec.classroom} • {sec.instructor}
                          </div>
                        </div>
                      ) : (
                        <div className="text-[10px] text-slate-200 select-none">•</div>
                      )}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
