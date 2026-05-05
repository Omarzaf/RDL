import { useEffect } from 'react';

const btnStyle = {
  background: 'rgba(99,102,241,0.15)',
  border: '1px solid rgba(99,102,241,0.3)',
  color: '#e2e8f0',
  borderRadius: 8,
  padding: '6px 14px',
  cursor: 'pointer',
  fontSize: 13,
};

export function TimeControls({ activeYear, setActiveYear, isPlaying, setIsPlaying }) {
  useEffect(() => {
    if (!isPlaying) return undefined;
    const interval = setInterval(() => {
      setActiveYear((y) => {
        if (y >= 2025) {
          setIsPlaying(false);
          return y;
        }
        return y + 1;
      });
    }, 1800);
    return () => clearInterval(interval);
  }, [isPlaying, setActiveYear, setIsPlaying]);

  return (
    <div style={{position:'fixed',bottom:80,left:'50%',transform:'translateX(-50%)',background:'rgba(5,10,20,0.85)',backdropFilter:'blur(12px)',border:'1px solid rgba(99,102,241,0.3)',borderRadius:12,padding:'12px 24px',display:'flex',gap:16,alignItems:'center',zIndex:100}}>
      <button style={btnStyle} onClick={() => setActiveYear((y) => Math.max(2018, y - 1))}>◀</button>
      <span style={{fontSize:20,fontWeight:700,minWidth:50,textAlign:'center',color:'#818cf8'}}>{activeYear}</span>
      <button style={btnStyle} onClick={() => setActiveYear((y) => Math.min(2025, y + 1))}>▶</button>
      <button style={{...btnStyle, background: isPlaying ? '#4f46e5' : btnStyle.background}} onClick={() => setIsPlaying((v) => !v)}>{isPlaying ? '⏸ Pause' : '▷ Play'}</button>
    </div>
  );
}
