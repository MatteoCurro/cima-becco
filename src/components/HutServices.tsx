import type { AlpinePlace } from '../lib/alpinePlaces';
import { hutServiceChapters } from '../lib/hutEditorial';
import { FaIcon, type FaIconName } from './FaIcon';

/** Stessa presentazione per rifugi e bivacchi, senza supposizioni su campi ignoti. */
const ICONS:Record<string,FaIconName>={
  meals:'utensils',kitchen:'utensils',showers:'shower',hotWater:'shower',
  sleepingBagLiner:'bed',wifi:'wifi',cardPayments:'credit-card',
  electricity:'bolt',mobileSignal:'signal',solarPower:'leaf',
  hydropower:'water',generatorPower:'bolt',
  waterAvailableReported:'water',drinkingWater:'glass-water',outsideWater:'water',
  pets:'paw',accessibility:'wheelchair',defibrillator:'heart-pulse',
  accessibleToilets:'toilet',toiletAvailableReported:'toilet',
  mattressAvailableReported:'bed',blanketAvailableReported:'bed',
  stoveAvailableReported:'fire',firewoodAvailableReported:'fire',
  gasAvailableReported:'fire',
};

export function HutServices({place}:{place:AlpinePlace}){
  const chapters=hutServiceChapters(place);
  if(!chapters.length)return null;
  return <div className="cb-hut-service-chapters">
    {chapters.map((chapter,index)=><section key={chapter.id} className="cb-hut-service-chapter">
      <header><span className="cb-hut-chapter-index">{String(index+1).padStart(2,'0')}</span>
        <h3>{chapter.title}</h3></header>
      <div className="cb-hut-service-list">
        {chapter.items.map(item=><div key={item.key}
          className={'cb-hut-service'+(item.value?' is-available':' is-unavailable')}
          aria-label={item.label+(item.value?' disponibile':' non disponibile')}>
          <span className="cb-hut-service-icon" aria-hidden="true">
            <FaIcon name={ICONS[item.key]||'circle-question'} size={20}/>
          </span>
          <span className="cb-hut-service-label">{item.label}
            {!item.value&&<small>Non disponibile</small>}
          </span>
        </div>)}
      </div>
    </section>)}
  </div>;
}
