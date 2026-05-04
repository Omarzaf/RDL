import { useMemo } from 'react';
import { Line } from '@react-three/drei';
import { getColor } from '../utils/colors';
import { YEAR_TO_Z, COORD_SCALE } from '../utils/scales';

export function Trails({ data }) {
  const { entities3d = [] } = data;

  const topEntities = useMemo(() => {
    const byEntity = new Map();
    for (const r of entities3d) {
      const arr = byEntity.get(r.entity_id) ?? [];
      arr.push(r);
      byEntity.set(r.entity_id, arr);
    }

    const entries = [...byEntity.entries()].map(([id, records]) => {
      const sorted = records.sort((a, b) => a.z - b.z);
      const maxSize = Math.max(...sorted.map((r) => r.size ?? 0), 0);
      return { id, records: sorted, maxSize };
    });

    return entries.sort((a, b) => b.maxSize - a.maxSize).slice(0, 250);
  }, [entities3d]);

  return (
    <group>
      {topEntities.map(({ id, records }) => (
        <Line
          key={id}
          points={records.map((r) => [
            (r.x ?? 0) * COORD_SCALE,
            (r.y ?? 0) * COORD_SCALE,
            YEAR_TO_Z(r.z),
          ])}
          color={getColor(records[0]?.industry)}
          lineWidth={0.5}
          transparent
          opacity={0.2}
        />
      ))}
    </group>
  );
}
