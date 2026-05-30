"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Marketplace browse removed from PMF nav — redirect to deployments. */
export default function AgentsPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/deployments");
  }, [router]);
  return (
    <div className="py-12 text-center text-neutral-500">
      Redirecting to Deployments…
    </div>
  );
}
