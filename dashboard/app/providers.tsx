"use client";

import { SWRConfig } from "swr";
import { apiFetch } from "@/lib/api";

export default function Providers({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SWRConfig
      value={{
        fetcher: apiFetch,
        revalidateOnFocus: false,
        shouldRetryOnError: true,
      }}
    >
      {children}
    </SWRConfig>
  );
}

