import {Text} from '@react-three/drei'; import {YEAR_TO_Z,YEARS} from '../utils/scales';
export function YearLabels(){return <>{YEARS.map(y=><Text key={y} position={[-460,-460,YEAR_TO_Z(y)]} fontSize={22} color='#475569' anchorX='left' anchorY='middle'>{String(y)}</Text>)}</>}
