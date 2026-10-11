import React from 'react';
import { Loader2, ShieldCheck, Clock } from 'lucide-react';

interface WaitingRoomModalProps {
  isOpen: boolean;
  ticketId: string;
  attempt: number;
  sectionCode: string;
  courseName: string;
}

export const WaitingRoomModal: React.FC<WaitingRoomModalProps> = ({
  isOpen,
  ticketId,
  attempt,
  sectionCode,
  courseName,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl border border-academic-border max-w-md w-full p-6 text-center space-y-5">
        {/* Animated Radar / Spinner */}
        <div className="relative mx-auto w-16 h-16 flex items-center justify-center">
          <div className="absolute inset-0 rounded-full bg-blue-100 animate-ping opacity-75"></div>
          <div className="relative w-14 h-14 rounded-full bg-blue-50 border border-blue-200 flex items-center justify-center text-academic-secondary shadow-sm">
            <Loader2 className="w-7 h-7 animate-spin" />
          </div>
        </div>

        {/* Tiêu đề & Thông báo */}
        <div className="space-y-2">
          <h3 className="text-base font-bold text-academic-text flex items-center justify-center gap-1.5">
            <span>Hàng Đợi Xử Lý Đồng Thời</span>
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
          </h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            Hệ thống đã <span className="font-bold text-emerald-600">giữ chỗ thành công</span> trên bộ nhớ đệm Redis. 
            Thông điệp đang được hàng đợi RabbitMQ phân bổ để ghi nhận bền vững vào PostgreSQL.
          </p>
        </div>

        {/* Thông tin vé & môn học */}
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-left text-xs space-y-2">
          <div className="flex justify-between items-center text-slate-500 border-b border-slate-200 pb-2">
            <span>Mã lượt đăng ký (Ticket):</span>
            <span className="font-mono font-bold text-slate-800 text-[11px] truncate max-w-[160px]">
              {ticketId}
            </span>
          </div>
          <div className="flex justify-between items-center text-slate-700">
            <span>Lớp học phần:</span>
            <span className="font-bold font-mono text-academic-primary">{sectionCode}</span>
          </div>
          <div className="flex justify-between items-center text-slate-600 truncate">
            <span>Tên môn học:</span>
            <span className="font-medium truncate max-w-[200px]">{courseName}</span>
          </div>
          <div className="flex justify-between items-center text-slate-500 pt-1 border-t border-slate-200">
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              Controlled Short Polling:
            </span>
            <span className="font-bold text-blue-600 font-tabular text-[11px]">
              Lần thăm dò #{attempt}/3 (1s/lần)
            </span>
          </div>
        </div>

        {/* Chân trang modal */}
        <div className="text-[11px] text-slate-400 flex items-center justify-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
          <span>Bảo đảm không bán vượt sĩ số (Zero Overselling Guaranteed)</span>
        </div>
      </div>
    </div>
  );
};
