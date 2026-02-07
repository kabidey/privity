/**
 * FloatingIcons Component
 * Interactive, draggable floating icons that hover around the login page
 * Features: Mouse tracking, drag & drop, collision avoidance, smooth animations
 */
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { FLOATING_KEYWORDS } from './constants';

const FloatingIcons = ({ theme }) => {
  const containerRef = useRef(null);
  const [icons, setIcons] = useState([]);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [draggedIcon, setDraggedIcon] = useState(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const animationRef = useRef(null);

  // Define the center exclusion zone (login section) - roughly 30% width, 60% height centered
  const exclusionZone = useMemo(() => ({
    left: 35,
    right: 65,
    top: 15,
    bottom: 85
  }), []);

  // Check if position is in exclusion zone
  const isInExclusionZone = useCallback((x, y) => {
    return x > exclusionZone.left && x < exclusionZone.right &&
           y > exclusionZone.top && y < exclusionZone.bottom;
  }, [exclusionZone]);

  // Generate initial positions avoiding the center
  const generatePosition = useCallback((existingPositions) => {
    let x, y, attempts = 0;
    do {
      // Generate positions on left or right side
      const side = Math.random() > 0.5 ? 'left' : 'right';
      if (side === 'left') {
        x = Math.random() * 30 + 2; // 2-32%
      } else {
        x = Math.random() * 30 + 68; // 68-98%
      }
      y = Math.random() * 90 + 5; // 5-95%
      attempts++;
    } while (
      attempts < 100 &&
      (isInExclusionZone(x, y) ||
       existingPositions.some(pos => 
         Math.abs(pos.x - x) < 10 && Math.abs(pos.y - y) < 10
       ))
    );
    return { x, y };
  }, [isInExclusionZone]);

  // Initialize icons
  useEffect(() => {
    const positions = [];
    const initialIcons = FLOATING_KEYWORDS.slice(0, 20).map((item, index) => {
      const pos = generatePosition(positions);
      positions.push(pos);
      return {
        id: index,
        ...pos,
        vx: (Math.random() - 0.5) * 0.3, // velocity x
        vy: (Math.random() - 0.5) * 0.3, // velocity y
        scale: 1,
        rotation: Math.random() * 10 - 5,
        item
      };
    });
    setIcons(initialIcons);
  }, [generatePosition]);

  // Mouse move handler
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      setMousePos({ x, y });

      // Update dragged icon position
      if (draggedIcon !== null) {
        setIcons(prev => prev.map(icon => {
          if (icon.id === draggedIcon) {
            let newX = x - dragOffset.x;
            let newY = y - dragOffset.y;
            
            // Clamp to bounds
            newX = Math.max(2, Math.min(98, newX));
            newY = Math.max(2, Math.min(98, newY));
            
            // Push away from exclusion zone
            if (isInExclusionZone(newX, newY)) {
              if (newX < 50) newX = exclusionZone.left - 5;
              else newX = exclusionZone.right + 5;
            }
            
            return { ...icon, x: newX, y: newY, vx: 0, vy: 0 };
          }
          return icon;
        }));
      }
    };

    const handleMouseUp = () => {
      setDraggedIcon(null);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [draggedIcon, dragOffset, isInExclusionZone, exclusionZone]);

  // Animation loop for floating effect
  useEffect(() => {
    const animate = () => {
      setIcons(prev => prev.map(icon => {
        if (icon.id === draggedIcon) return icon;

        let { x, y, vx, vy } = icon;

        // Add slight random movement
        vx += (Math.random() - 0.5) * 0.02;
        vy += (Math.random() - 0.5) * 0.02;

        // Mouse repulsion effect (icons move away from cursor)
        const dx = x - mousePos.x;
        const dy = y - mousePos.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 15 && dist > 0) {
          const force = (15 - dist) * 0.01;
          vx += (dx / dist) * force;
          vy += (dy / dist) * force;
        }

        // Repulsion from exclusion zone
        if (isInExclusionZone(x, y)) {
          const centerX = (exclusionZone.left + exclusionZone.right) / 2;
          const centerY = (exclusionZone.top + exclusionZone.bottom) / 2;
          const edx = x - centerX;
          const edy = y - centerY;
          vx += edx * 0.05;
          vy += edy * 0.05;
        }

        // Boundary repulsion
        if (x < 5) vx += 0.1;
        if (x > 95) vx -= 0.1;
        if (y < 5) vy += 0.1;
        if (y > 95) vy -= 0.1;

        // Friction
        vx *= 0.98;
        vy *= 0.98;

        // Clamp velocity
        const maxV = 0.5;
        vx = Math.max(-maxV, Math.min(maxV, vx));
        vy = Math.max(-maxV, Math.min(maxV, vy));

        // Update position
        x += vx;
        y += vy;

        // Clamp position
        x = Math.max(2, Math.min(98, x));
        y = Math.max(2, Math.min(98, y));

        return { ...icon, x, y, vx, vy };
      }));

      animationRef.current = requestAnimationFrame(animate);
    };

    animationRef.current = requestAnimationFrame(animate);
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [mousePos, draggedIcon, isInExclusionZone, exclusionZone]);

  // Handle icon drag start
  const handleMouseDown = (e, iconId) => {
    e.preventDefault();
    const icon = icons.find(i => i.id === iconId);
    if (!icon || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const mouseX = ((e.clientX - rect.left) / rect.width) * 100;
    const mouseY = ((e.clientY - rect.top) / rect.height) * 100;

    setDragOffset({ x: mouseX - icon.x, y: mouseY - icon.y });
    setDraggedIcon(iconId);
    
    // Scale up the dragged icon
    setIcons(prev => prev.map(i => 
      i.id === iconId ? { ...i, scale: 1.2 } : i
    ));
  };

  // Handle icon release
  const handleIconRelease = (iconId) => {
    setIcons(prev => prev.map(i => 
      i.id === iconId ? { ...i, scale: 1 } : i
    ));
  };

  return (
    <div 
      ref={containerRef}
      className="absolute inset-0 overflow-hidden"
      style={{ zIndex: 1 }}
    >
      {icons.map((icon) => {
        const Icon = icon.item.icon;
        const isDragging = draggedIcon === icon.id;
        
        return (
          <div
            key={icon.id}
            className={`absolute cursor-grab select-none transition-transform duration-100 ${isDragging ? 'cursor-grabbing z-50' : 'z-10'}`}
            style={{
              left: `${icon.x}%`,
              top: `${icon.y}%`,
              transform: `translate(-50%, -50%) scale(${icon.scale}) rotate(${icon.rotation}deg)`,
              transition: isDragging ? 'none' : 'transform 0.1s ease-out',
            }}
            onMouseDown={(e) => handleMouseDown(e, icon.id)}
            onMouseUp={() => handleIconRelease(icon.id)}
            onMouseEnter={() => {
              if (draggedIcon === null) {
                setIcons(prev => prev.map(i => 
                  i.id === icon.id ? { ...i, scale: 1.15, rotation: 0 } : i
                ));
              }
            }}
            onMouseLeave={() => {
              if (draggedIcon === null) {
                setIcons(prev => prev.map(i => 
                  i.id === icon.id ? { ...i, scale: 1, rotation: Math.random() * 10 - 5 } : i
                ));
              }
            }}
          >
            <div 
              className={`
                p-3 rounded-xl backdrop-blur-md
                bg-gradient-to-br from-${theme.primary}-500/25 to-${theme.secondary}-500/15
                border-2 border-${theme.primary}-400/40
                shadow-lg shadow-${theme.primary}-500/25
                hover:shadow-xl hover:shadow-${theme.primary}-400/40
                hover:border-${theme.primary}-300/60
                hover:from-${theme.primary}-400/40 hover:to-${theme.secondary}-400/25
                transition-all duration-300
                ${isDragging ? `ring-2 ring-${theme.primary}-300 scale-110` : ''}
              `}
            >
              <Icon className={`w-6 h-6 text-${theme.primary}-300 drop-shadow-md`} />
            </div>
            <p className={`
              text-${theme.primary}-200 text-[10px] mt-1.5 text-center 
              font-bold tracking-wider drop-shadow-lg uppercase
            `}>
              {icon.item.word}
            </p>
          </div>
        );
      })}
    </div>
  );
};

export default FloatingIcons;
