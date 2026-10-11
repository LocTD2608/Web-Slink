import React from 'react';
import { GraduationCap, User, BookOpen, Zap, RotateCcw, RefreshCw } from 'lucide-react';
import { StudentProfile } from '../types/registration';

interface HeaderProps {
  student: StudentProfile;
  onRunDemo?: () => void;
  onResetDemo?: () => void;
  onRefresh?: () => void;
  isDemoRunning?: boolean;
  isResetting?: boolean;
  isRefreshing?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  student,
  onRunDemo,
  onResetDemo,
  onRefresh,
  isDemoRunning,
  isResetting,
  isRefreshing,
}) => {
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

          {/* Thanh Công Cụ Demo Phản Biện & Thông Tin Sinh Viên */}
          <div className="flex items-center space-x-3 sm:space-x-5">
            {/* Bộ Nút Demo Phản Biện Trực Tiếp */}
            <div className="flex items-center space-x-2 bg-blue-950/60 p-1 rounded-lg border border-blue-800/80">
              {onRunDemo && (
                <button
                  onClick={onRunDemo}
                  disabled={isDemoRunning || isResetting}
                  className="px-2.5 py-1 text-xs font-bold rounded bg-amber-500 hover:bg-amber-600 active:bg-amber-700 text-slate-900 flex items-center gap-1 transition shadow-sm disabled:opacity-50"
                  title="Mô phỏng 500 sinh viên tranh 30 chỗ lớp CS101-01"
                >
                  <Zap className={`w-3.5 h-3.5 ${isDemoRunning ? 'animate-bounce' : ''}`} />
                  {isDemoRunning ? 'Đang test 500 SV...' : '⚡ Demo 500 SV'}
                </button>
              )}

              {onResetDemo && (
                <button
                  onClick={onResetDemo}
                  disabled={isDemoRunning || isResetting}
                  className="px-2 py-1 text-xs font-semibold rounded bg-white/10 hover:bg-white/20 text-blue-200 flex items-center gap-1 transition disabled:opacity-50"
                  title="Khôi phục toàn bộ 200 lớp về trạng thái trống ban đầu"
                >
                  <RotateCcw className={`w-3 h-3 ${isResetting ? 'animate-spin' : ''}`} />
                  Reset
                </button>
              )}

              {onRefresh && (
                <button
                  onClick={onRefresh}
                  disabled={isRefreshing}
                  className="p-1 rounded bg-white/10 hover:bg-white/20 text-blue-200 transition disabled:opacity-50"
                  title="Đồng bộ danh mục tức thì từ Redis"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
                </button>
              )}
            </div>

            {/* Tiến độ tín chỉ */}
            <div className="hidden md:flex flex-col items-end">
              <div className="flex items-center space-x-2 text-xs text-blue-200 mb-1">
                <BookOpen className="w-3.5 h-3.5" />
                <span>Số tín chỉ đã đăng ký:</span>
                <span className="font-bold text-white tabular-stat text-sm">
                  {student.current_credits}/{student.max_credits} TC
                </span>
              </div>
              <div className="w-32 bg-blue-950/60 rounded-full h-2 border border-blue-800/60 overflow-hidden">
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
