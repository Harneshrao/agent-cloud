"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface AuthInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

const AuthInput = React.forwardRef<HTMLInputElement, AuthInputProps>(
  ({ label, error, className, id, ...props }, ref) => {
    const inputId = id ?? `auth-${label.replace(/\s/g, "-").toLowerCase()}`;
    return (
      <div className="space-y-1.5">
        <label htmlFor={inputId} className="block text-sm font-medium text-black">
          {label}
        </label>
        <input
          ref={ref}
          id={inputId}
          className={cn(
            "w-full rounded-md border border-gray-300 px-4 py-2.5 text-black transition-colors",
            "placeholder:text-neutral-500",
            "focus:border-[#0A66C2] focus:outline-none focus:ring-2 focus:ring-[#0A66C2]/20",
            "disabled:cursor-not-allowed disabled:opacity-50",
            error && "border-red-500 focus:border-red-500 focus:ring-red-500/20",
            className
          )}
          {...props}
        />
        {error && (
          <p className="text-sm text-red-600" role="alert">
            {error}
          </p>
        )}
      </div>
    );
  }
);
AuthInput.displayName = "AuthInput";

export { AuthInput };
