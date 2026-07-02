import type { Metadata } from "next";

import { Providers } from "@/app/providers";
import { SupabaseAuthRuntimeBridge } from "@/components/supabase-auth-runtime-bridge";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "lingualens",
  description: "Case-centered clinical decision-support prototype for therapist review workflows."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <SupabaseAuthRuntimeBridge />
          {children}
        </Providers>
      </body>
    </html>
  );
}
