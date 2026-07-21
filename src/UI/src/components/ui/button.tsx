import * as React from "react"
import { cn } from "@/lib/utils"

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link' | 'premium'
  size?: 'default' | 'sm' | 'lg' | 'icon'
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => {
    return (
      <button
        className={cn(
          "inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 cursor-pointer gap-2",
          {
            "bg-primary text-primary-foreground shadow-sm hover:bg-primary/90": variant === 'default',
            "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90": variant === 'destructive',
            "border border-border bg-transparent shadow-sm hover:bg-muted hover:text-foreground": variant === 'outline',
            "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80": variant === 'secondary',
            "hover:bg-muted hover:text-foreground": variant === 'ghost',
            "text-primary underline-offset-4 hover:underline": variant === 'link',
            "bg-gradient-to-r from-rose-500 via-pink-500 to-red-500 text-white font-semibold shadow-lg hover:brightness-110 active:scale-98 transition-all": variant === 'premium',
          },
          {
            "h-10 px-4 py-2": size === 'default',
            "h-8 rounded-md px-3 text-xs": size === 'sm',
            "h-11 rounded-md px-8": size === 'lg',
            "h-10 w-10 p-0": size === 'icon',
          },
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button }
