import {useEffect,useState} from 'react';
import {SUPABASE_CONFIGURED,supabase,fetchCommunityRoutes} from '../lib/api';
import {SiteFooter,SiteHeader} from './SiteChrome';
import {usePageTitle} from '../lib/pageTitle';
import type {Route} from '../types';
import '../alpineAtlas.css';

interface PublicProfile {
  username:string;
  bio:string;
  avatarUrl:string|null;
  saved:string[];
  uploaded:string[];
}

export function PublicProfilePage(){
  const [profile,setProfile]=useState<PublicProfile|null>(null);
  const [routes,setRoutes]=useState<Route[]>([]);
  const [loading,setLoading]=useState(true);
  const [missing,setMissing]=useState(false);
  const username=decodeURIComponent(window.location.hash.replace(/^#profilo\//,'')).slice(0,40);
  usePageTitle(username?'Profilo di '+username:'Profili Cima Becco');
  useEffect(()=>{
    let active=true;
    setLoading(true);setMissing(false);setProfile(null);
    if(!SUPABASE_CONFIGURED||!/^[A-Za-z0-9_.-]{3,24}$/.test(username)){
      setLoading(false);setMissing(true);return;
    }
    void (async()=>{
      // Si leggono SOLO profili dichiaratamente pubblici; nessuna email.
      const {data:users,error:usersError}=await supabase.from('profiles').select('id,username,avatar_path').eq('username',username).limit(1);
      const found=users?.[0];
      if(usersError||!found)throw new Error('profilo inesistente');
      const {data:settings,error:settingsError}=await supabase.from('cima_public_profiles')
        .select('bio,is_public,show_saved_routes').eq('user_id',found.id).maybeSingle();
      if(settingsError||!settings?.is_public)throw new Error('profilo privato');
      const [saved,owned,all]=await Promise.all([
        settings.show_saved_routes
          ?supabase.from('cima_public_saved_routes').select('route_slug').eq('user_id',found.id).limit(200)
          :Promise.resolve({data:[]}),
        supabase.from('cima_public_route_owners').select('route_slug').eq('user_id',found.id).limit(200),
        fetchCommunityRoutes().catch(()=>[]),
      ]);
      if(!active)return;
      setRoutes(all);
      setProfile({
        username:found.username,bio:settings.bio||'',avatarUrl:null,
        saved:(saved.data||[]).map((row:{route_slug:string})=>row.route_slug),
        uploaded:(owned.data||[]).map((row:{route_slug:string})=>row.route_slug),
      });
    })().catch(()=>{if(active)setMissing(true);}).finally(()=>{if(active)setLoading(false);});
    return()=>{active=false;};
  },[username]);
  function cards(slugs:string[],title:string){
    return <section className="cb-atlas-nearby"><h2>{title} <span>{slugs.length}</span></h2>
      {slugs.length?<div className="cb-atlas-routes">{slugs.map(slug=>{
        const r=routes.find(x=>x.slug===slug);
        return <a key={slug} href={`#route/${slug}`}>
          <strong>{r?.name||'Percorso '+slug}</strong><span>{r?`${(r.distanceM/1000).toFixed(1)} km · `:''}VEDI GPX ↗</span>
        </a>;
      })}</div>:<p>Nessun itinerario condiviso per ora.</p>}
    </section>;
  }
  return <div className="cb-atlas-page"><SiteHeader sticky/><main className="cb-atlas-shell cb-public-profile-page">
    <div className="cb-atlas-overline">CIMA BECCO / PROFILI PUBBLICI</div>
    {loading?<p>Carico il profilo pubblico…</p>:profile?<>
      <h1>{profile.username}</h1><p className="cb-atlas-lead">{profile.bio||'Uno che in montagna ci va. Il resto lo raccontano i sentieri.'}</p>
      {cards(profile.uploaded,'TRACCE CREATE E ATTRIBUITE')}
      {cards(profile.saved,'PERCORSI SALVATI E RESI PUBBLICI')}
    </>:<div className="cb-atlas-empty"><h1>QUI NON C’È NESSUNO. ANCORA.</h1>
      <p>{SUPABASE_CONFIGURED?'Questo profilo non esiste oppure il proprietario non lo ha reso pubblico.':'La sezione è pronta, ma il database Cima Becco non è ancora collegato. Nessun dato privato viene pubblicato.'}</p>
      <a href="#routes">Esplora i sentieri ↗</a></div>}
    {missing&&SUPABASE_CONFIGURED&&<p className="cb-atlas-sourcing">I profili sono pubblici esclusivamente per scelta del proprietario.</p>}
  </main><SiteFooter/></div>;
}
