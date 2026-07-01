import { createClient, type SupabaseClient } from "@supabase/supabase-js";

// Server-side Supabase client (service role — full access; NEVER send to the browser).
// Used to validate access tokens and, later, to mint Storage signed-upload URLs.
let admin: SupabaseClient | null = null;

export function supabaseAdmin(): SupabaseClient {
  if (admin) return admin;
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) throw new Error("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set");
  admin = createClient(url, key, { auth: { persistSession: false, autoRefreshToken: false } });
  return admin;
}
