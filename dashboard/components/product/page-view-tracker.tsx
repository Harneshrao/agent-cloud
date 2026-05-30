"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { trackPageView } from "@/lib/analytics";

/** Fire page_viewed on route changes for founder funnel diagnostics. */
export function PageViewTracker() {
  const pathname = usePathname();
  const last = useRef<string | null>(null);

  useEffect(() => {
    const path = pathname ?? "/";
    if (path === last.current) return;
    last.current = path;
    trackPageView(path);
  }, [pathname]);

  return null;
}
