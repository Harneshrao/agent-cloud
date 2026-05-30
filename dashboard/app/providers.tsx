"use client";

import { SWRConfig } from "swr";
import { ActiveProjectProvider } from "@/context/active-project";
import { PlatformStateProvider } from "@/context/platform-state";
import { apiFetch } from "@/lib/api";

export default function Providers({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <PlatformStateProvider>
      <SWRConfig
        value={{
          fetcher: apiFetch,
          revalidateOnFocus: false,
          shouldRetryOnError: true,
        }}
      >
        <ActiveProjectProvider>{children}</ActiveProjectProvider>
      </SWRConfig>
    </PlatformStateProvider>
  );
}
