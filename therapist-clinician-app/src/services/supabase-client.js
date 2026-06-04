import { createClient } from "@supabase/supabase-js";

// Read environment variables (Vite-specific) or fallback to global window objects
const supabaseUrl = (typeof import.meta !== "undefined" ? import.meta.env?.VITE_SUPABASE_URL : null) || (typeof window !== "undefined" ? window.__ASD_SUPABASE_URL__ : null) || "";
const supabaseAnonKey = (typeof import.meta !== "undefined" ? import.meta.env?.VITE_SUPABASE_ANON_KEY : null) || (typeof window !== "undefined" ? window.__ASD_SUPABASE_ANON_KEY__ : null) || "";

export const supabase = (supabaseUrl && supabaseAnonKey)
  ? createClient(supabaseUrl, supabaseAnonKey)
  : null;

if (!supabase) {
  console.warn("Supabase client is not initialized. Supabase-related operations will fallback or report errors. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in your env.");
}
