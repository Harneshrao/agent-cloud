"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-[#F3F2EF] px-4">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-primary">Something went wrong</h1>
        <p className="mt-2 text-foreground-secondary">
          An error occurred. You can try again or return to the dashboard.
        </p>
      </div>
      <div className="flex gap-3">
        <Button onClick={reset} variant="default">
          Try again
        </Button>
        <Button onClick={() => (window.location.href = "/")} variant="outline">
          Go to dashboard
        </Button>
      </div>
    </div>
  );
}
