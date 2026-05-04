import { Color } from 'three';
export const INDUSTRY_COLORS={"Law & Lobbying":"#6366f1","Healthcare & Pharma":"#10b981","Defense & Aerospace":"#ef4444","Finance & Banking":"#f59e0b","Technology & Telecom":"#3b82f6","Energy & Environment":"#84cc16","Agriculture & Food":"#f97316","Transportation & Auto":"#8b5cf6","Education & Research":"#14b8a6","Real Estate & Construction":"#ec4899","Government & Nonprofit":"#94a3b8","Healthcare - Insurance":"#06b6d4","Other / Multi-sector":"#64748b"};
export function getColor(industry){return INDUSTRY_COLORS[industry]??INDUSTRY_COLORS['Other / Multi-sector'];}
export function hexToThreeColor(hex){return new Color(hex);}
