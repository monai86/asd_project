# Use Supabase-first clinical platform

We will use Supabase Auth, Postgres, Row Level Security, and Storage as the default product platform for the full clinical web application because the project needs owner-isolated case data, relational reporting, signed private file storage, and a Python backend boundary. Firebase remains a possible alternative for teams already committed to Google infrastructure, but it would make relational clinical reporting and Python pipeline integration more indirect.

