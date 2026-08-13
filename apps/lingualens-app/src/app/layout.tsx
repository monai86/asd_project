import type { Metadata } from "next";

import { Providers } from "@/app/providers";
import { SupabaseAuthRuntimeBridge } from "@/components/supabase-auth-runtime-bridge";
import "@/styles/globals.css";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL?.trim() || "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
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
