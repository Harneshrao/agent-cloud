"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { useApiHealth } from "@/hooks/use-api-health";
import { getApiBaseUrl } from "@/lib/api";

type ApiConnectionBannerProps = {
  /** Called when API becomes ready (e.g. refetch dashboard data). */
  onReady?: () => void;
};

export function ApiConnectionBanner({ onReady }: ApiConnectionBannerProps) {
  const { apiReady, checkHealth } = useApiHealth();
  const [retrying, setRetrying] = useState(false);
  const [apiUrl, setApiUrl] = useState("");

  useEffect(() => {
    setApiUrl(getApiBaseUrl());
  }, []);

  useEffect(() => {
    if (apiReady && onReady) {
      onReady();
    }
  }, [apiReady, onReady]);

  const handleRetry = async () => {
    setRetrying(true);
    try {
      const ok = await checkHealth();
      if (ok && onReady) onReady();
    } finally {
      setRetrying(false);
    }
  };

  // Remove the blocking connectivity banner entirely. Pages should handle their own
  // loading/error states and the app should call the API directly.
  void apiReady;
  void checkHealth;
  void retrying;
  void apiUrl;
  void handleRetry;
  void setApiUrl;
  void setRetrying;
  void onReady;
  return null;
}
