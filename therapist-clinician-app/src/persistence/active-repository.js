import { api } from "../services/api-client.js";
import { supabase } from "../services/supabase-client.js";
import { createApiRepository } from "./api-repository.js";
import { createSupabaseRepository } from "./supabase-repository.js";

export function isRemoteDataMode(mode) {
  return mode === "api" || mode === "supabase";
}

export function createActiveClinicalRepository(mode) {
  if (mode === "supabase") {
    return createSupabaseRepository({ client: supabase });
  }
  return createApiRepository({ apiClient: api });
}
