"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface AuthButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean;
}

const AuthButton = React.forwardRef<HTMLButtonElement, AuthButtonProps>(
  ({ className, loading, disabled, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        type="submit"
        disabled={disabled ?? loading}
        className={cn(
          "w-full rounded-lg bg-[#0A66C2] py-2.5 font-semibold text-white transition-colors",
          "hover:bg-[#004182] focus:outline-none focus:ring-2 focus:ring-[#0A66C2]/30 focus:ring-offset-2",
          "disabled:cursor-not-allowed disabled:opacity-60",
          className
        )}
        {...props}
      >
        {loading ? (
          <span className="inline-flex items-center gap-2">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            Please wait…
          </span>
        ) : (
          children
        )}
      </button>
    );
  }
);
AuthButton.displayName = "AuthButton";

export { AuthButton };
