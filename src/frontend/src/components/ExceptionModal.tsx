import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, X } from 'lucide-react';
import { FeedbackModalState } from '../types/registration';

interface ExceptionModalProps {
  modal: FeedbackModalState;
  onClose: () => void;
}

export const ExceptionModal: React.FC<ExceptionModalProps> = ({ modal, onClose }) => {
  if (!modal.isOpen) return null;

  const isSuccess = modal.type === 'SUCCESS';
  const isConflict = modal.type === 'CONFLICT';
  const isFull = modal.type === 'FULL';
  const isPrereq = modal.type === 'PREREQ';

  const getIcon = () => {
    if (isSuccess) return <CheckCircle2 className="w-8 h-8 text-emerald-600" />;
    if (isConflict) return <XCircle className="w-8 h-8 text-rose-600" />;
    if (isFull) return <AlertTriangle className="w-8 h-8 text-amber-600" />;
    if (isPrereq) return <AlertTriangle className="w-8 h-8 text-amber-600" />;
    return <XCircle className="w-8 h-8 text-rose-600" />;
  };

  const getBorderColor = () => {
    if (isSuccess) return 'border-emerald-200';
    if (isConflict) return 'border-rose-200';
    if (isFull) return 'border-amber-200';
    if (isPrereq) return 'border-amber-200';
    return 'border-rose-200';
  };

  const getButtonBg = () => {
    if (isSuccess) return 'bg-emerald-600 hover:bg-emerald-700';
    if (isConflict) return 'bg-rose-600 hover:bg-rose-700';
    return 'bg-academic-primary hover:bg-blue-900';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div
        className={`bg-white rounded-2xl shadow-xl border ${getBorderColor()} max-w-md w-full p-6 text-center space-y-4 relative`}
      >
        <button
          onClick={onClose}
          className="absolute right-4 top-4 text-slate-400 hover:text-slate-600 p-1 rounded-full transition"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="mx-auto w-14 h-14 rounded-full bg-slate-50 flex items-center justify-center shadow-inner">
          {getIcon()}
        </div>

        <div className="space-y-1.5">
          <h3 className="text-base font-bold text-slate-900">{modal.title}</h3>
          {modal.sectionCode && (
            <div className="text-xs font-mono font-bold text-academic-primary">
              [{modal.sectionCode}]
            </div>
          )}
          <p className="text-xs text-slate-600 leading-relaxed px-2">{modal.message}</p>
        </div>

        <div className="pt-2">
          <button
            onClick={onClose}
            className={`w-full py-2 px-4 text-white text-xs font-semibold rounded-lg shadow-sm transition ${getButtonBg()}`}
          >
            Đã hiểu và Đóng
          </button>
        </div>
      </div>
    </div>
  );
};
