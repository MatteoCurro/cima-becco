import { useState } from 'react';
import { useAuthUser } from '../lib/auth';
import { SUPABASE_CONFIGURED, supabase } from '../lib/api';
import { CONTACT_EMAIL } from '../lib/contribute';
import { AuthModal } from './AuthModal';
import type { AlpinePlace } from '../lib/alpinePlaces';

export function HutClaimRequest({place}:{place:AlpinePlace}) {
  const user=useAuthUser();
  const [open,setOpen]=useState(false);
  const [authOpen,setAuthOpen]=useState(false);
  const [note,setNote]=useState('');
  const [submitting,setSubmitting]=useState(false);
  const [done,setDone]=useState(false);
  const [error,setError]=useState<string|null>(null);
  if(place.kind!=='rifugio')return null;
  const email=CONTACT_EMAIL ? `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent('Cima Becco · Richiesta gestione '+place.name)}&body=${encodeURIComponent('Ciao, vorrei richiedere la gestione della scheda '+place.name+' ('+place.osmUrl+').\nSono: ...\nRuolo nella struttura: ...\nContatto ufficiale per verifica: ...\n')}` : null;

  async function submit(){
    if(!user||!SUPABASE_CONFIGURED||submitting)return;
    setError(null);setSubmitting(true);
    try{
      const {error}=await supabase.from('hut_claim_requests').insert({
        place_slug:place.slug,requester_id:user.id,notes:note.trim().slice(0,700),
      });
      if(error)throw error;
      setDone(true);
    }catch{
      setError('La richiesta non è stata registrata. Il servizio di approvazione potrebbe non essere ancora attivo.');
    }finally{setSubmitting(false);}
  }

  return <section className="cb-hut-claim">
    <div><small>RIFUGISTA? TOCCA A TE.</small><h2>GESTISCI TU QUESTA SCHEDA.</h2>
      <p>Se rappresenti questo rifugio, puoi chiedere la gestione di informazioni, fotografie e aggiornamenti. L’accesso non è automatico: approvazione manuale dell’amministratore.</p></div>
    {!open ? <button type="button" onClick={()=>setOpen(true)}>CHIEDI L’ACCESSO ↗</button>
      : done ? <p role="status">Richiesta registrata. La gestione resta bloccata fino alla verifica dell’amministratore.</p>
      : <div className="cb-hut-claim-form">
          {SUPABASE_CONFIGURED && user ? <>
            <p>Stai richiedendo come <strong>{user.username}</strong>. Indica il ruolo e un contatto ufficiale verificabile.</p>
            <textarea aria-label="Ruolo e contatto verificabile" value={note} rows={3} maxLength={700} onChange={e=>setNote(e.target.value)} placeholder="Sono il gestore / collaboratore del rifugio…"/>
            <button type="button" disabled={submitting||note.trim().length<12} onClick={()=>void submit()}>{submitting?'INVIO…':'INVIA RICHIESTA'}</button>
          </> : SUPABASE_CONFIGURED ? <>
            <p>Serve un account Cima Becco, poi la richiesta sarà verificata manualmente.</p>
            <button type="button" onClick={()=>setAuthOpen(true)}>ACCEDI / REGISTRATI</button>
          </> : <>
            <p>Le richieste online saranno disponibili quando attiveremo il database. Per ora puoi contattare direttamente l’amministratore.</p>
            {email ? <a href={email}>SCRIVI PER CHIEDERE LA GESTIONE ↗</a> : <span>Canale richieste non ancora configurato.</span>}
          </>}
          {error&&<p role="alert">{error} {email&&<a href={email}>Contatta l’amministratore</a>}</p>}
          <button type="button" className="cb-hut-claim-cancel" onClick={()=>setOpen(false)}>Chiudi</button>
        </div>}
    {authOpen&&<AuthModal onClose={()=>setAuthOpen(false)}/>}
  </section>;
}
