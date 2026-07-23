import React, { useState, useRef, useEffect } from 'react';
import { Calendar as CalendarIcon, X } from 'lucide-react';
import { format, parseISO, isValid, isBefore, startOfDay } from 'date-fns';
import { DayPicker } from 'react-day-picker';
import 'react-day-picker/style.css';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface DatePickerProps {
  value: string; // Expected format: YYYY-MM-DD
  onChange: (dateStr: string) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
}

export function DatePicker({
  value,
  onChange,
  placeholder = "Pick a show date",
  className,
  disabled = false
}: DatePickerProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Parse current date string to Date object
  const selectedDate = React.useMemo(() => {
    if (!value) return undefined;
    const parsed = parseISO(value);
    return isValid(parsed) ? parsed : undefined;
  }, [value]);

  // Handle outside click to close popover
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    if (open) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [open]);

  const handleSelect = (day: Date | undefined) => {
    if (day) {
      const formatted = format(day, 'yyyy-MM-dd');
      onChange(formatted);
    } else {
      onChange('');
    }
    setOpen(false);
  };

  const today = startOfDay(new Date());

  return (
    <div className="relative inline-block w-full" ref={containerRef}>
      {/* Trigger Button */}
      <Button
        type="button"
        variant="outline"
        disabled={disabled}
        onClick={() => setOpen(!open)}
        className={cn(
          "w-full h-9.5 px-3 text-xs justify-between font-normal bg-muted/10 border-border/80 hover:bg-muted/20 focus:border-rose-500/40 text-left transition-colors",
          !selectedDate && "text-muted-foreground/60",
          selectedDate && "text-foreground font-semibold",
          open && "border-rose-500/60 ring-1 ring-rose-500/20",
          className
        )}
      >
        <div className="flex items-center gap-2 truncate">
          <CalendarIcon className="h-3.5 w-3.5 text-rose-500 shrink-0" />
          <span className="truncate">
            {selectedDate ? format(selectedDate, "EEE, MMM d, yyyy") : placeholder}
          </span>
        </div>
        {selectedDate ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onChange('');
            }}
            className="p-0.5 rounded-full hover:bg-muted text-muted-foreground hover:text-foreground shrink-0"
            title="Clear date"
          >
            <X className="h-3 w-3" />
          </button>
        ) : (
          <span className="text-[10px] text-muted-foreground/50 uppercase font-mono">Select</span>
        )}
      </Button>

      {/* Popover Content */}
      {open && (
        <div className="absolute z-50 mt-1.5 w-auto p-3 rounded-2xl border border-rose-500/30 bg-[#0e0e14]/98 text-foreground shadow-2xl backdrop-blur-xl animate-in fade-in-80 zoom-in-95 left-0 ring-1 ring-black/60 font-sans">
          <DayPicker
            mode="single"
            selected={selectedDate}
            onSelect={handleSelect}
            disabled={(date) => isBefore(startOfDay(date), today)}
            showOutsideDays={false}
          />
        </div>
      )}
    </div>
  );
}
