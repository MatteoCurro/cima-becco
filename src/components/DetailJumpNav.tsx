import { FaIcon } from './FaIcon';
import { scrollToDetailSection } from '../lib/detailNavigation';
import './detailSections.css';

/** Indice di sezione: button, non hash. Gli hash sono già riservati al router. */
export interface DetailJumpItem { id:string; label:string; icon?:'map'|'route'|'compass'|'house'|'camera'|'water'|'mountain'; }
export function DetailJumpNav({items}:{items:readonly DetailJumpItem[]}) {
  if (!items.length) return null;
  return <nav className="cb-detail-jump" aria-label="Naviga questa scheda">
    <strong className="cb-detail-jump-heading">Vai a</strong>
    <div className="cb-detail-jump-items">
      {items.map(item=><button key={item.id} type="button" onClick={()=>scrollToDetailSection(item.id)}>
        {item.icon&&<FaIcon name={item.icon} size={13}/>}
        <span>{item.label}</span>
      </button>)}
    </div>
  </nav>;
}
