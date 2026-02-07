/**
 * FloatingIcons Component
 * Renders animated floating icons on the login page background
 */
import { useMemo } from 'react';
import { FLOATING_KEYWORDS } from './constants';

const FloatingIcons = ({ theme }) => {
  // Generate random positions for floating icons
  const floatingIcons = useMemo(() => {
    const positions = [];
    const usedPositions = new Set();
    
    // Generate 24 random positions avoiding overlap
    for (let i = 0; i < 24; i++) {
      let attempts = 0;
      let x, y;
      do {
        x = Math.random() * 90 + 5;
        y = Math.random() * 85 + 5;
        attempts++;
      } while (
        attempts < 50 &&
        Array.from(usedPositions).some(pos => {
          const [px, py] = pos.split(',').map(Number);
          return Math.abs(px - x) < 8 && Math.abs(py - y) < 8;
        })
      );
      usedPositions.add(`${x},${y}`);
      positions.push({ x, y, delay: Math.random() * 5, duration: 15 + Math.random() * 10 });
    }
    return positions;
  }, []);

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {floatingIcons.map((pos, index) => {
        const item = FLOATING_KEYWORDS[index % FLOATING_KEYWORDS.length];
        const Icon = item.icon;
        return (
          <div
            key={index}
            className="absolute animate-float"
            style={{
              left: `${pos.x}%`,
              top: `${pos.y}%`,
              animationDelay: `${pos.delay}s`,
              animationDuration: `${pos.duration}s`,
            }}
          >
            <div className={`p-3 rounded-xl bg-${theme.primary}-500/10 border border-${theme.primary}-400/20 backdrop-blur-sm group hover:bg-${theme.primary}-500/20 transition-all duration-300`}>
              <Icon className={`w-5 h-5 text-${theme.primary}-400/70`} />
            </div>
            <p className={`text-${theme.primary}-300 text-[10px] mt-1 text-center font-bold tracking-wider drop-shadow-md`}>{item.word}</p>
          </div>
        );
      })}
    </div>
  );
};

export default FloatingIcons;
