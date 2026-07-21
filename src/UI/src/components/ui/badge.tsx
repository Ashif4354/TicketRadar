import * as React from "react"
import { cn } from "@/lib/utils"

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning' | 'info' | 'running'
}

function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-all border",
        {
          "border-transparent bg-primary text-primary-foreground shadow": variant === 'default',
          "border-transparent bg-secondary text-secondary-foreground": variant === 'secondary',
          "border-transparent bg-destructive text-destructive-foreground shadow": variant === 'destructive',
          "text-foreground border-border bg-muted/10": variant === 'outline',
          "border-emerald-500/30 bg-emerald-500/10 text-emerald-400 shadow-sm shadow-emerald-500/5": variant === 'success',
          "border-amber-500/30 bg-amber-500/10 text-amber-400 shadow-sm shadow-amber-500/5": variant === 'warning',
          "border-blue-500/30 bg-blue-500/10 text-blue-400 shadow-sm shadow-blue-500/5": variant === 'info',
          "border-violet-500/30 bg-violet-500/10 text-violet-400 shadow-sm shadow-violet-500/5 animate-pulse": variant === 'running',
        },
        className
      )}
      {...props}
    />
  )
}

export { Badge }
