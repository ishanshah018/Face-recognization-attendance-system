import type { ReactNode } from "react";
import { BrowserRouter } from "react-router-dom";
import { AppDataProvider } from "@/app/providers/AppDataProvider";
import { ToastProvider } from "@/app/providers/ToastProvider";

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AppDataProvider>{children}</AppDataProvider>
      </ToastProvider>
    </BrowserRouter>
  );
}
