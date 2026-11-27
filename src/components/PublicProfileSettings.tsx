import {useEffect,useState} from 'react';
import {SUPABASE_CONFIGURED,supabase} from '../lib/api';
import {useAuthUser} from '../lib/auth';
import {useSavedRoutes} from '../lib/saved';

export function PublicProfileSettings(){
  const user=useAuthUser();
  const saved=useSavedRoutes();
  const [bio,setBio]=useState('');
  const [visible,setVisible]=useState(false);
  const [showSaved,setShowSaved]=useState(false);
  const [ready,setReady]=useState(false);
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState('');
  useEffect(()=>{
    if(!user||!SUPABASE_CONFIGURED)return;
    let active=true;
    void supabase.from('cima_public_profiles').select('bio,is_public,show_saved_routes')
      .eq('user_id',user.id).maybeSingle()
      .then(({data,error})=>{
        if(!active)return;
        if(error){setMessage('Database dei profili pubblici non ancora configurato.');return;}
        if(data){
          setBio(data.bio||'');setVisible(Boolean(data.is_public));setShowSaved(Boolean(data.show_saved_routes));
        }
        setReady(true);
      });
    return()=>{active=false;};
  },[user?.id]);
  if(!user||!SUPABASE_CONFIGURED)return null;

  async function save(){
    if(!user||busy)return;
    setBusy(true);setMessage('');
    try{
      const {error}=await supabase.from('cima_public_profiles').upsert({
        user_id:user.id,display_name:user.username,bio:bio.trim().slice(0,600),
        is_public:visible,show_saved_routes:visible&&showSaved,updated_at:new Date().toISOString(),
      },{onConflict:'user_id'});
      if(error)throw error;
      // Dati pubblici esplicitamente scelti, mai leggere/esporre la tabella privata saved_items.
      const {error:delError}=await supabase.from('cima_public_saved_routes').delete().eq('user_id',user.id);
      if(delError)throw delError;
      if(visible&&showSaved&&saved.size){
        const {error:addError}=await supabase.from('cima_public_saved_routes').insert(
          [...saved].slice(0,200).map(slug=>({user_id:user.id,route_slug:slug}))
        );
        if(addError)throw addError;
      }
      setMessage('Profilo aggiornato. I percorsi creati compaiono dopo la verifica della loro attribuzione.');
    }catch{
      setMessage('Impossibile salvare: la base dati dedicata deve essere attivata prima della pubblicazione.');
    }finally{setBusy(false);}
  }

  return <section className="cb-public-profile-controls">
    <span>LA TUA IDENTITÀ SUL SENTIERO</span><h2>FATTI VEDERE. O NO.</h2>
    <p>Il profilo pubblico è facoltativo. I preferiti restano privati finché non decidi di mostrarli. I GPX creati saranno attribuiti solo dopo aver verificato l’account proprietario, mai dal nome inserito in una traccia.</p>
    <label>Due parole su di te<textarea rows={3} maxLength={600} value={bio} onChange={e=>setBio(e.target.value)} placeholder="Cime, rifugi, gambe in sciopero…"/></label>
    <label className="cb-profile-check"><input type="checkbox" checked={visible} onChange={e=>setVisible(e.target.checked)}/> Pubblica il mio profilo</label>
    <label className="cb-profile-check"><input type="checkbox" checked={showSaved} onChange={e=>setShowSaved(e.target.checked)} disabled={!visible}/> Rendi pubblici anche i miei {saved.size} percorsi salvati</label>
    <div className="cb-profile-actions"><button type="button" disabled={!ready||busy} onClick={()=>void save()}>{busy?'SALVATAGGIO…':'SALVA LE PREFERENZE'}</button>
      {visible&&<a href={`#profilo/${encodeURIComponent(user.username)}`}>APRI IL MIO PROFILO ↗</a>}</div>
    {message&&<p role="status">{message}</p>}
  </section>;
}
