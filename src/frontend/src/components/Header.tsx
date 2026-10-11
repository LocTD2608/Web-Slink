import React from 'react';
import { GraduationCap, User, BookOpen } from 'lucide-react';
import { StudentProfile } from '../types/registration';

interface HeaderProps {
  student: StudentProfile;
}

export const Header: React.FC<HeaderProps> = ({ student }) => {
  const creditPercentage = Math.min(100, Math.round((student.current_credits / student.max_credits) * 100));

  return (
    <header className="bg-academic-primary text-white shadow-md border-b border-blue-900 sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Tên Cổng */}
          <div className="flex items-center space-x-3">
            <div className="bg-white/10 p-2 rounded-lg backdrop-blur-sm">
              <GraduationCap className="h-7 w-7 text-blue-200" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
                CỔNG ĐĂNG KÝ HỌC PHẦN TRỰC TUYẾN
                <span className="text-xs bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 px-2 py-0.5 rounded-full font-medium flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  Cổng đang mở
                </span>
              </h1>
              <p className="text-xs text-blue-200">Học kỳ 1 • Năm học 2024 - 2025 • Đợt 1</p>
            </div>
          </div>

          {/* Thông tin Sinh viên & Tiến độ Tín chỉ */}
          <div className="flex items-center space-x-6">
            {/* Tiến độ tín chỉ */}
            <div className="hidden sm:flex flex-col items-end">
              <div className="flex items-center space-x-2 text-xs text-blue-200 mb-1">
                <BookOpen className="w-3.5 h-3.5" />
                <span>Số tín chỉ đã đăng ký:</span>
                <span className="font-bold text-white tabular-stat text-sm">
                  {student.current_credits}/{student.max_credits} TC
                </span>
              </div>
              <div className="w-36 bg-blue-950/60 rounded-full h-2 border border-blue-800/60 overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 rounded-full ${
                    creditPercentage >= 100 ? 'bg-amber-400' : 'bg-emerald-400'
                  }`}
                  style={{ width: `${creditPercentage}%` }}
                ></div>
              </div>
            </div>

            {/* Thông tin sinh viên */}
            <div className="flex items-center space-x-3 bg-white/10 px-3 py-1.5 rounded-lg border border-white/10 backdrop-blur-sm">
              <div className="w-8 h-8 rounded-full bg-academic-secondary flex items-center justify-center font-bold text-sm">
                <User className="w-4 h-4 text-white" />
              </div>
              <div className="text-left text-xs">
                <div className="font-semibold text-white">{student.full_name}</div>
                <div className="text-blue-200 font-mono text-[11px] flex items-center gap-1">
                  <span>{student.student_code}</span>
                  <span>•</span>
                  <span>{student.major}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
