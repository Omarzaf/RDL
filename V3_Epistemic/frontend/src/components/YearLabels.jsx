import { Text } from '@react-three/drei';
import { YEAR_TO_Z, YEARS } from '../utils/scales';

export function YearLabels() {
  return (
    <group>
      {YEARS.map((year) => (
        <Text
          key={year}
          position={[-460, -460, YEAR_TO_Z(year)]}
          fontSize={18}
          color="#475569"
          anchorX="left"
          anchorY="middle"
        >
          {String(year)}
        </Text>
      ))}
    </group>
  );
}
