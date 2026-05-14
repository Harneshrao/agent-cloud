import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-12 w-full rounded-xl border border-border bg-card px-4 py-3 text-sm font-normal tracking-[0.01em] text-foreground placeholder:text-neutral-500 focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/30 focus:ring-offset-0 focus:ring-offset-background focus:shadow-[0_0_0_3px_rgba(124,58,237,0.16)] disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
