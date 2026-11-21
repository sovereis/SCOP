-- Run once in the chosen Supabase project. No sample personal data.
create table public.scop_signups (
  id uuid primary key,
  email text not null check (char_length(email) between 1 and 254),
  tool text not null check (char_length(tool) between 1 and 120),
  problem text not null check (char_length(problem) between 1 and 2000),
  consent boolean not null check (consent = true),
  consent_version text not null,
  submitted_at timestamptz not null default now()
);
alter table public.scop_signups enable row level security;
revoke all on public.scop_signups from anon, authenticated;
grant insert, select on public.scop_signups to service_role;
