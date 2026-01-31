import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { getChangelog } from '../changelog';
import { getFullVersion } from '../version';
import { 
  Sparkles, 
  Bug, 
  Zap, 
  Shield, 
  Calendar, 
  ChevronRight,
  Rocket,
  X
} from 'lucide-react';

const ChangelogModal = ({ isOpen, onClose }) => {
  const [changelog] = useState(getChangelog());
  const currentVersion = getFullVersion();

  const getTypeIcon = (type) => {
    switch (type) {
      case 'feature':
        return <Sparkles className="h-4 w-4 text-purple-500" />;
      case 'fix':
        return <Bug className="h-4 w-4 text-red-500" />;
      case 'improvement':
        return <Zap className="h-4 w-4 text-amber-500" />;
      case 'security':
        return <Shield className="h-4 w-4 text-green-500" />;
      default:
        return <ChevronRight className="h-4 w-4 text-gray-500" />;
    }
  };

  const getTypeBadge = (type) => {
    const styles = {
      feature: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
      fix: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
      improvement: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
      security: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    };
    return styles[type] || 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300';
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg max-h-[85vh] p-0 overflow-hidden" data-testid="changelog-modal">
        {/* Header */}
        <div className="relative bg-gradient-to-br from-emerald-500 to-teal-600 p-6 text-white">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-white/20 rounded-xl">
              <Rocket className="h-6 w-6" />
            </div>
            <div>
              <DialogTitle className="text-xl font-bold text-white">
                Version History
              </DialogTitle>
              <DialogDescription className="text-emerald-100">
                Current version: {currentVersion}
              </DialogDescription>
            </div>
          </div>
        </div>

        {/* Content */}
        <ScrollArea className="max-h-[50vh] p-4">
          <div className="space-y-6">
            {changelog.map((release, idx) => (
              <div key={release.version} className="space-y-3">
                {/* Version Header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="font-mono font-bold text-emerald-600 dark:text-emerald-400 border-emerald-500">
                      {release.version}
                    </Badge>
                    {idx === 0 && (
                      <Badge className="bg-emerald-500 text-white text-xs">Latest</Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                    <Calendar className="h-3 w-3" />
                    {release.date}
                  </div>
                </div>

                {/* Release Title */}
                {release.title && (
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                    {release.title}
                  </h3>
                )}

                {/* Changes List */}
                <div className="space-y-2">
                  {release.changes.map((change, changeIdx) => (
                    <div 
                      key={changeIdx}
                      className="flex items-start gap-3 p-2 rounded-lg bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                    >
                      <div className="mt-0.5">
                        {getTypeIcon(change.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${getTypeBadge(change.type)}`}>
                            {change.type}
                          </span>
                        </div>
                        <p className="text-sm text-gray-700 dark:text-gray-300">
                          {change.description}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                {idx < changelog.length - 1 && (
                  <Separator className="my-4" />
                )}
              </div>
            ))}
          </div>
        </ScrollArea>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50">
          <div className="flex items-center justify-end">
            <Button
              onClick={onClose}
              className="bg-emerald-500 hover:bg-emerald-600 text-white"
              data-testid="changelog-close-btn"
            >
              Close
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// Simple hook - no auto-show, just manual control
export const useChangelogModal = () => {
  const [showChangelog, setShowChangelog] = useState(false);

  return {
    showChangelog,
    setShowChangelog,
    openChangelog: () => setShowChangelog(true),
    closeChangelog: () => setShowChangelog(false),
  };
};

export default ChangelogModal;
