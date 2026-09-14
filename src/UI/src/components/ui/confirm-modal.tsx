import React from 'react';
import { AlertTriangle, Pause, Trash2, StopCircle, Play, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description: React.ReactNode;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning' | 'info' | 'success';
  icon?: 'pause' | 'delete' | 'stop' | 'warning' | 'play';
  isLoading?: boolean;
}

export function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = 'warning',
  icon = 'warning',
  isLoading = false
}: ConfirmModalProps) {
  if (!isOpen) return null;

  const renderIcon = () => {
    switch (icon) {
      case 'pause':
        return (
          <div className="h-10 w-10 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center shrink-0">
            <Pause className="h-5 w-5" />
          </div>
        );
      case 'delete':
        return (
          <div className="h-10 w-10 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center shrink-0">
            <Trash2 className="h-5 w-5" />
          </div>
        );
      case 'stop':
        return (
          <div className="h-10 w-10 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center shrink-0">
            <StopCircle className="h-5 w-5" />
          </div>
        );
      case 'play':
        return (
          <div className="h-10 w-10 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
            <Play className="h-5 w-5 fill-current" />
          </div>
        );
      case 'warning':
      default:
        return (
          <div className="h-10 w-10 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center shrink-0">
            <AlertTriangle className="h-5 w-5" />
          </div>
        );
    }
  };

  const getConfirmButtonStyle = () => {
    if (variant === 'danger') {
      return "bg-rose-600 hover:bg-rose-500 text-white font-bold";
    }
    if (variant === 'success') {
      return "bg-emerald-600 hover:bg-emerald-500 text-white font-bold";
    }
    return "bg-amber-600 hover:bg-amber-500 text-white font-bold";
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-in fade-in duration-150 overflow-y-auto"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isLoading) onClose();
      }}
    >
      <div 
        className="relative w-full max-w-md bg-slate-900 border border-border/80 rounded-2xl p-5 sm:p-6 shadow-2xl space-y-4 my-auto animate-in zoom-in-95 duration-150"
        role="dialog"
        aria-modal="true"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            {renderIcon()}
            <div>
              <h3 className="text-base font-bold text-foreground leading-snug">{title}</h3>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isLoading}
            className="text-muted-foreground hover:text-foreground p-1 rounded-lg transition-colors shrink-0 disabled:opacity-50 cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="text-xs text-muted-foreground leading-relaxed pl-1">
          {description}
        </div>

        <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-border/30 flex-wrap sm:flex-nowrap">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onClose}
            disabled={isLoading}
            className="h-9 px-4 text-xs font-semibold w-full sm:w-auto cursor-pointer"
          >
            {cancelText}
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={onConfirm}
            disabled={isLoading}
            className={`h-9 px-4 text-xs w-full sm:w-auto cursor-pointer ${getConfirmButtonStyle()}`}
          >
            {isLoading ? "Processing..." : confirmText}
          </Button>
        </div>
      </div>
    </div>
  );
}
