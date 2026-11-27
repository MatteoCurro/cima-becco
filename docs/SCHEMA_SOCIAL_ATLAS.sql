-- Cima Becco / schema preparatorio. NON applicato a nessun database.
-- Richiede un progetto Supabase SEPARATO da U.Venice Transport.
-- Tutte le tabelle esposte hanno RLS; solo il proprietario accede ai propri dati.
-- Le approvazioni sono riservate a un amministratore registrato DAL SERVER.

create table if not exists public.cima_admins (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);
alter table public.cima_admins enable row level security;
revoke all on public.cima_admins from anon, authenticated;
grant select on public.cima_admins to authenticated;
create policy "cima_admins_self_select" on public.cima_admins for select to authenticated
  using (user_id = (select auth.uid()));
-- Nessuna INSERT/UPDATE/DELETE sul client; l'admin si configura solo con SQL editor/server.

create table if not exists public.hut_claim_requests (
  id uuid primary key default gen_random_uuid(),
  place_slug text not null check(place_slug ~ '^osm-[nwr]-[0-9]+$'),
  requester_id uuid not null references auth.users(id) on delete cascade,
  notes text not null check(length(notes) between 12 and 700),
  status text not null default 'pending' check(status in ('pending','approved','rejected')),
  reviewed_by uuid references auth.users(id),
  reviewed_at timestamptz,
  review_note text check(length(review_note) <= 1000),
  created_at timestamptz not null default now(),
  unique(place_slug, requester_id)
);
create index if not exists hut_claim_requests_status_idx on public.hut_claim_requests(status,created_at desc);
alter table public.hut_claim_requests enable row level security;
revoke all on public.hut_claim_requests from anon, authenticated;
grant select,insert,update on public.hut_claim_requests to authenticated;
create policy "hut_claim_requests_owner_or_admin_read" on public.hut_claim_requests for select to authenticated
  using(requester_id=(select auth.uid()) or exists(
    select 1 from public.cima_admins a where a.user_id=(select auth.uid())
  ));
create policy "hut_claim_requests_owner_create" on public.hut_claim_requests for insert to authenticated
  with check(requester_id=(select auth.uid()) and status='pending' and reviewed_by is null and reviewed_at is null
    and (select auth.jwt()->>'is_anonymous') is distinct from 'true');
create policy "hut_claim_requests_admin_approve" on public.hut_claim_requests for update to authenticated
  using(exists(select 1 from public.cima_admins a where a.user_id=(select auth.uid())))
  with check(exists(select 1 from public.cima_admins a where a.user_id=(select auth.uid())));

create table if not exists public.hut_manager_access (
  place_slug text not null check(place_slug ~ '^osm-[nwr]-[0-9]+$'),
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'editor' check(role in ('editor','manager')),
  granted_by uuid not null references auth.users(id),
  created_at timestamptz not null default now(),
  primary key(place_slug,user_id)
);
alter table public.hut_manager_access enable row level security;
revoke all on public.hut_manager_access from anon,authenticated;
grant select,insert,update,delete on public.hut_manager_access to authenticated;
create policy "hut_manager_access_read_self_admin" on public.hut_manager_access for select to authenticated
  using(user_id=(select auth.uid()) or exists(select 1 from public.cima_admins a where a.user_id=(select auth.uid())));
create policy "hut_manager_access_insert_admin" on public.hut_manager_access for insert to authenticated
  with check(exists(select 1 from public.cima_admins a where a.user_id=(select auth.uid()))
    and granted_by=(select auth.uid()));
create policy "hut_manager_access_update_admin" on public.hut_manager_access for update to authenticated
  using(exists(select 1 from public.cima_admins a where a.user_id=(select auth.uid())))
  with check(exists(select 1 from public.cima_admins a where a.user_id=(select auth.uid())));
create policy "hut_manager_access_delete_admin" on public.hut_manager_access for delete to authenticated
  using(exists(select 1 from public.cima_admins a where a.user_id=(select auth.uid())));

-- Il profilo pubblico è opt-in; non pubblicare e-mail, GPS privati, cronologie.
create table if not exists public.cima_public_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text check(length(display_name)<=70),
  bio text check(length(bio)<=600),
  is_public boolean not null default false,
  show_saved_routes boolean not null default false,
  updated_at timestamptz not null default now()
);
alter table public.cima_public_profiles enable row level security;
revoke all on public.cima_public_profiles from anon,authenticated;
grant select to anon,authenticated;
grant insert,update,delete to authenticated;
create policy "cima_public_profiles_read" on public.cima_public_profiles for select to anon,authenticated
  using(is_public or user_id=(select auth.uid()));
create policy "cima_public_profiles_insert_self" on public.cima_public_profiles for insert to authenticated
  with check(user_id=(select auth.uid()));
create policy "cima_public_profiles_update_self" on public.cima_public_profiles for update to authenticated
  using(user_id=(select auth.uid())) with check(user_id=(select auth.uid()));
create policy "cima_public_profiles_delete_self" on public.cima_public_profiles for delete to authenticated
  using(user_id=(select auth.uid()));

-- Preferiti esplicitamente pubblicati. I preferiti in saved_items restano privati!
create table if not exists public.cima_public_saved_routes (
  user_id uuid not null references auth.users(id) on delete cascade,
  route_slug text not null check(length(route_slug) between 3 and 150),
  created_at timestamptz not null default now(),
  primary key(user_id,route_slug)
);
create index if not exists cima_public_saved_routes_slug_idx on public.cima_public_saved_routes(route_slug);
alter table public.cima_public_saved_routes enable row level security;
revoke all on public.cima_public_saved_routes from anon,authenticated;
grant select to anon,authenticated;
grant insert,delete to authenticated;
create policy "cima_public_saved_routes_read" on public.cima_public_saved_routes for select to anon,authenticated
  using(user_id=(select auth.uid()) or exists(
    select 1 from public.cima_public_profiles p where p.user_id=cima_public_saved_routes.user_id
    and p.is_public and p.show_saved_routes
  ));
create policy "cima_public_saved_routes_create_self" on public.cima_public_saved_routes for insert to authenticated
  with check(user_id=(select auth.uid()));
create policy "cima_public_saved_routes_delete_self" on public.cima_public_saved_routes for delete to authenticated
  using(user_id=(select auth.uid()));

-- Attribution verificata dei GPX: scrittura SOLO lato server dopo aver
-- controllato routes.user_id e status='approved'. Nessun INSERT client.
create table if not exists public.cima_public_route_owners (
  route_slug text primary key check(length(route_slug) between 3 and 150),
  user_id uuid not null references auth.users(id) on delete cascade,
  published_at timestamptz not null default now()
);
create index if not exists cima_public_route_owners_user_idx on public.cima_public_route_owners(user_id);
alter table public.cima_public_route_owners enable row level security;
revoke all on public.cima_public_route_owners from anon,authenticated;
grant select on public.cima_public_route_owners to anon,authenticated;
create policy "cima_public_route_owners_read" on public.cima_public_route_owners for select to anon,authenticated
  using(exists(select 1 from public.cima_public_profiles p
    where p.user_id=cima_public_route_owners.user_id and p.is_public));

-- Eventi identificabili solo dall'utente proprietario, lettura agli admin.
-- Nessuna telemetria anonima in questo schema: servirà un endpoint rate-limited.
create table if not exists public.cima_site_events (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  event_type text not null check(event_type in (
    'search','route_open','gpx_download','route_bookmarked','atlas_place_view','hut_claim_request'
  )),
  target text not null default '' check(length(target)<=100),
  created_at timestamptz not null default now()
);
create index if not exists cima_site_events_time_idx on public.cima_site_events(created_at desc);
create index if not exists cima_site_events_type_target_idx on public.cima_site_events(event_type,target);
alter table public.cima_site_events enable row level security;
revoke all on public.cima_site_events from anon,authenticated;
grant insert,select on public.cima_site_events to authenticated;
create policy "cima_site_events_insert_self" on public.cima_site_events for insert to authenticated
  with check(user_id=(select auth.uid())
    and (select auth.jwt()->>'is_anonymous') is distinct from 'true');
create policy "cima_site_events_read_admin" on public.cima_site_events for select to authenticated
  using(exists(select 1 from public.cima_admins a where a.user_id=(select auth.uid())));
