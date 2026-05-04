import { useMemo, useState } from 'react';
import { INDUSTRY_COLORS } from '../utils/colors';

export function FilterPanel({ data, filters, setFilters }) {
  const [open, setOpen] = useState(false);
  const industries = useMemo(() => [...new Set((data.entities3d || []).map((r) => r.industry).filter(Boolean))], [data]);

  const toggleIndustry = (industry) => {
    setFilters((prev) => {
      const next = new Set(prev.industries);
      if (next.has(industry)) next.delete(industry); else next.add(industry);
      return { ...prev, industries: next };
    });
  };

  return <div style={{position:'fixed',left:16,top:72,zIndex:120}}>
    <button onClick={() => setOpen((v) => !v)} style={{background:'rgba(5,10,20,0.85)',color:'#e2e8f0',border:'1px solid rgba(99,102,241,0.3)',borderRadius:10,padding:'8px 12px'}}>≡ Filters</button>
    {open && <div style={{marginTop:8,width:300,maxHeight:460,overflow:'auto',background:'rgba(5,10,20,0.85)',backdropFilter:'blur(12px)',border:'1px solid rgba(99,102,241,0.3)',borderRadius:10,padding:12,color:'#e2e8f0'}}>
      <div style={{fontWeight:700,marginBottom:8}}>Industries</div>
      <div style={{display:'flex',flexWrap:'wrap',gap:8}}>{industries.map((i) => <button key={i} onClick={() => toggleIndustry(i)} style={{border: filters.industries.has(i) ? '2px solid #fff' : '1px solid transparent', background: INDUSTRY_COLORS[i] || '#64748b', color:'#fff', borderRadius:999, padding:'4px 10px', fontSize:12}}>{i}</button>)}</div>
    </div>}
  </div>;
}
