import { useMemo } from 'react';
import { Sphere } from '@react-three/drei';
import { getColor } from '../utils/colors';
import { YEAR_TO_Z, COORD_SCALE, sizeToRadius } from '../utils/scales';

export function Nodes({ data, activeYear, filters, onNodeClick }) {
  const { entities3d = [] } = data;
  const year = activeYear ?? 2023;

  const visible = useMemo(() => {
    const industries = filters?.industries ?? new Set();
    const entityTypes = filters?.entityTypes ?? new Set();
    return entities3d.filter((e) => {
      if (e.z !== year) return false;
      if (industries.size && !industries.has(e.industry)) return false;
      if (entityTypes.size && !entityTypes.has(e.entity_type)) return false;
      if (filters?.showRevolvingOnly && (e.revolving_door_count ?? 0) <= 0) return false;
      return true;
    });
  }, [entities3d, year, filters]);

  return (
    <group>
      {visible.map((node) => (
        <Sphere
          key={`${node.entity_id}-${node.z}`}
          args={[sizeToRadius(node.size ?? 0), 10, 10]}
          position={[
            (node.x ?? 0) * COORD_SCALE,
            (node.y ?? 0) * COORD_SCALE,
            YEAR_TO_Z(node.z ?? year),
          ]}
          onClick={(e) => {
            e.stopPropagation();
            onNodeClick?.(node);
          }}
        >
          <meshStandardMaterial
            color={getColor(node.industry)}
            emissive={getColor(node.industry)}
            emissiveIntensity={0.25}
            roughness={0.35}
            metalness={0.1}
            transparent
            opacity={0.88}
          />
        </Sphere>
      ))}
    </group>
  );
}
