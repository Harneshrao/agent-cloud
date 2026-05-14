"use client";

import { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";

export function ChromeLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isPublic = pathname === "/";

  if (isPublic) {
    return <main className="mx-auto w-full max-w-[1100px] px-9 py-9">{children}</main>;
  }

  return (
    <>
      <Sidebar />
      <div className="ml-56 min-h-screen">
        <Topbar />
        <main className="mx-auto w-full max-w-[1100px] px-9 py-9">{children}</main>
      </div>
    </>
  );
}

