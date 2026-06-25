import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL as string;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

// Browser Supabase client. Uses the public anon key; persists the session in
// localStorage and auto-refreshes the access token.
export const supabase = createClient(url, anonKey);
