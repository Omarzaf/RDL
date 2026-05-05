import {useEffect,useState} from 'react';
import entities3dRaw from '../../../data/frontend/entities_3d.json';
import clustersRaw from '../../../data/frontend/clusters.json';
import gapGridRaw from '../../../data/frontend/gap_grid.json';
import revVecsRaw from '../../../data/frontend/revolving_vectors.json';
import trendsRaw from '../../../data/frontend/trends.json';
export function useData(){const [data,setData]=useState(null);useEffect(()=>{const entityMaxSize={}; for(const r of entities3dRaw){if(!entityMaxSize[r.entity_id]||r.size>entityMaxSize[r.entity_id])entityMaxSize[r.entity_id]=r.size||0;} const top2000=new Set(Object.entries(entityMaxSize).sort((a,b)=>b[1]-a[1]).slice(0,2000).map(([id])=>id)); const entities3d=entities3dRaw.filter(r=>top2000.has(r.entity_id)); setData({entities3d,entitiesAll:entities3dRaw,clusters:clustersRaw,gapGrid:gapGridRaw,revVecs:revVecsRaw,trends:trendsRaw});},[]);return data;}
