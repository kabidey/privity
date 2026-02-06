import { useTheme, THEMES } from '../context/ThemeContext';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from '@/components/ui/dropdown-menu';
import { Palette, Check } from 'lucide-react';

const ThemeSelector = ({ variant = 'dropdown' }) => {
  const { theme, setTheme, themes } = useTheme();

  // Grid variant - shows all themes in a grid
  if (variant === 'grid') {
    return (
      <div className="grid grid-cols-5 gap-2 p-2">
        {Object.entries(themes).map(([key, { name, icon }]) => (
          <button
            key={key}
            onClick={() => setTheme(key)}
            className={`
              flex flex-col items-center gap-1 p-2 rounded-lg transition-all
              ${theme === key 
                ? 'bg-primary text-primary-foreground ring-2 ring-primary ring-offset-2' 
                : 'bg-muted hover:bg-muted/80'
              }
            `}
            title={name}
          >
            <span className="text-lg">{icon}</span>
            <span className="text-[10px] font-medium truncate w-full text-center">{name}</span>
          </button>
        ))}
      </div>
    );
  }

  // Dropdown variant - compact dropdown menu
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-1.5" data-testid="theme-selector">
          <span className="text-sm">{themes[theme]?.icon || '🎨'}</span>
          <Palette className="h-3.5 w-3.5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuLabel className="text-xs text-muted-foreground">
          Choose Theme
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        
        {/* Light themes */}
        <DropdownMenuLabel className="text-[10px] text-muted-foreground uppercase tracking-wide">
          Light
        </DropdownMenuLabel>
        {['light', 'sunset', 'forest', 'lavender', 'rose', 'coral', 'mint'].map(key => (
          <DropdownMenuItem
            key={key}
            onClick={() => setTheme(key)}
            className="flex items-center gap-2 cursor-pointer"
          >
            <span>{themes[key].icon}</span>
            <span className="flex-1 text-xs">{themes[key].name}</span>
            {theme === key && <Check className="h-3 w-3 text-primary" />}
          </DropdownMenuItem>
        ))}
        
        <DropdownMenuSeparator />
        
        {/* Dark themes */}
        <DropdownMenuLabel className="text-[10px] text-muted-foreground uppercase tracking-wide">
          Dark
        </DropdownMenuLabel>
        {['dark', 'ocean', 'midnight'].map(key => (
          <DropdownMenuItem
            key={key}
            onClick={() => setTheme(key)}
            className="flex items-center gap-2 cursor-pointer"
          >
            <span>{themes[key].icon}</span>
            <span className="flex-1 text-xs">{themes[key].name}</span>
            {theme === key && <Check className="h-3 w-3 text-primary" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default ThemeSelector;
