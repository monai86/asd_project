export function createUser({
  user_id,
  name,
  email,
  credentials = "",
  role = "therapist",
  organization = "",
  created_at = new Date().toISOString(),
  last_login = null
}) {
  return {
    user_id,
    name,
    email,
    credentials,
    role, // 'therapist' | 'clinician' | 'admin'
    organization,
    created_at,
    last_login
  };
}
