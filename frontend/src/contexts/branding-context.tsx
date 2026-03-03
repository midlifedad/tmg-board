"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { brandingApi, type BrandingSettings } from "@/lib/api";

const DEFAULT_BRANDING: BrandingSettings = {
  app_name: "Board Portal",
  organization_name: "",
  organization_logo_url: null,
};

interface BrandingContextValue {
  branding: BrandingSettings;
  isLoading: boolean;
  refresh: () => Promise<void>;
}

const BrandingContext = createContext<BrandingContextValue>({
  branding: DEFAULT_BRANDING,
  isLoading: true,
  refresh: async () => {},
});

export function BrandingProvider({ children }: { children: ReactNode }) {
  const [branding, setBranding] = useState<BrandingSettings>(DEFAULT_BRANDING);
  const [isLoading, setIsLoading] = useState(true);

  const fetchBranding = async () => {
    try {
      const data = await brandingApi.getBranding();
      setBranding(data);
      document.title = data.app_name;
    } catch {
      // Keep defaults on error
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchBranding();
  }, []);

  return (
    <BrandingContext.Provider value={{ branding, isLoading, refresh: fetchBranding }}>
      {children}
    </BrandingContext.Provider>
  );
}

export function useBranding() {
  return useContext(BrandingContext);
}
