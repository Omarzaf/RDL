import { format } from 'd3-format';
import { getColor } from '../utils/colors';

const money = format('$,.0f');

export function NodeDetail({ node, onClose }) {
  return <div style={{position:'fixed',right:16,top:72,width:360,zIndex:130,background:'rgba(5,10,20,0.9)',backdropFilter:'blur(12px)',border:'1px solid rgba(99,102,241,0.3)',borderRadius:12,padding:16,color:'#e2e8f0'}}>
    <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}><h3 style={{margin:0,fontSize:16}}>{node.name}</h3><button onClick={onClose}>✕</button></div>
    <div style={{marginTop:8,fontSize:13}}><span style={{display:'inline-block',width:10,height:10,borderRadius:10,background:getColor(node.industry),marginRight:8}}/>{node.entity_type} · {node.industry}</div>
    <hr style={{borderColor:'rgba(99,102,241,0.2)',margin:'12px 0'}}/>
    <div>Total Spend: {money(node.size || 0)}</div>
    <div>Total Filings: {(node.filings || 0).toLocaleString()}</div>
    <div>Revolving Door: {(node.revolving_door_count || 0).toLocaleString()} people</div>
    <div>Gap Score: {Number(node.gap_score || 0).toFixed(2)}</div>
    <div>Cluster: {node.cluster_label || 'Unknown'}</div>
  </div>;
}
