import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Trophy, ChevronUp, ChevronDown, Star, Target, Sparkles } from 'lucide-react';
import { useDemo, DEMO_TOURS } from '../../contexts/DemoContext';
import DemoProgressTracker from './DemoProgressTracker';

export default function FloatingProgressWidget() {
  const { isDemoMode, completedTours } = useDemo();
  const [isExpanded, setIsExpanded] = useState(false);
  const [showTracker, setShowTracker] = useState(false);
  const [showCelebration, setShowCelebration] = useState(false);
  const [lastTourCount, setLastTourCount] = useState(0);

  // Calculate progress
  const totalTours = Object.keys(DEMO_TOURS).length;
  const progress = (completedTours.length / totalTours) * 100;
  const totalPoints = 10 + (completedTours.length * 25);

  // Show celebration when a new tour is completed
  useEffect(() => {
    if (completedTours.length > lastTourCount && lastTourCount > 0) {
      setShowCelebration(true);
      setTimeout(() => setShowCelebration(false), 3000);
    }
    setLastTourCount(completedTours.length);
  }, [completedTours.length, lastTourCount]);

  if (!isDemoMode) return null;

  return (
    <>
      <DemoProgressTracker 
        isOpen={showTracker} 
        onClose={() => setShowTracker(false)} 
      />

      {/* Floating Widget */}
      <motion.div
        initial={{ x: 100, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        className="fixed bottom-24 right-4 z-40"
      >
        {/* Celebration particles */}
        <AnimatePresence>
          {showCelebration && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute -top-8 -left-8 -right-8"
            >
              {[...Array(10)].map((_, i) => (
                <motion.div
                  key={i}
                  className="absolute"
                  initial={{ 
                    x: 40, 
                    y: 40, 
                    scale: 0 
                  }}
                  animate={{ 
                    x: 40 + ((i % 5) - 2) * 25,
                    y: 40 - (i + 1) * 8,
                    scale: [0, 1, 0],
                    rotate: i * 36
                  }}
                  transition={{ duration: 1, delay: i * 0.1 }}
                >
                  <Sparkles className="w-4 h-4 text-yellow-400" />
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        <motion.div
          layout
          className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden"
          style={{ width: isExpanded ? 200 : 'auto' }}
        >
          {/* Main button */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full p-3 flex items-center gap-3 hover:bg-gray-50 transition-colors"
          >
            <div className="relative">
              <div className="w-10 h-10 bg-gradient-to-br from-amber-400 to-orange-500 rounded-full flex items-center justify-center">
                <Trophy className="w-5 h-5 text-white" />
              </div>
              {/* Progress ring */}
              <svg
                className="absolute -inset-1 -rotate-90"
                width="48"
                height="48"
              >
                <circle
                  className="text-gray-200"
                  strokeWidth="3"
                  stroke="currentColor"
                  fill="transparent"
                  r="20"
                  cx="24"
                  cy="24"
                />
                <motion.circle
                  className="text-emerald-500"
                  strokeWidth="3"
                  strokeLinecap="round"
                  stroke="currentColor"
                  fill="transparent"
                  r="20"
                  cx="24"
                  cy="24"
                  initial={{ strokeDashoffset: 126 }}
                  animate={{ strokeDashoffset: 126 - (126 * progress) / 100 }}
                  style={{ strokeDasharray: 126 }}
                />
              </svg>
            </div>

            {isExpanded && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex-1 text-left"
              >
                <div className="text-sm font-semibold text-gray-800">
                  {totalPoints} points
                </div>
                <div className="text-xs text-gray-500">
                  {completedTours.length}/{totalTours} tours
                </div>
              </motion.div>
            )}

            <motion.div
              animate={{ rotate: isExpanded ? 180 : 0 }}
              className="text-gray-400"
            >
              <ChevronUp className="w-4 h-4" />
            </motion.div>
          </button>

          {/* Expanded content */}
          <AnimatePresence>
            {isExpanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="border-t"
              >
                <div className="p-3 space-y-3">
                  {/* Progress bar */}
                  <div>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-gray-500">Tour Progress</span>
                      <span className="font-medium text-emerald-600">{Math.round(progress)}%</span>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-gradient-to-r from-emerald-400 to-teal-500 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${progress}%` }}
                      />
                    </div>
                  </div>

                  {/* Quick stats */}
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1 text-amber-600">
                      <Star className="w-3 h-3" />
                      <span>{totalPoints} pts</span>
                    </div>
                    <div className="flex items-center gap-1 text-emerald-600">
                      <Target className="w-3 h-3" />
                      <span>{completedTours.length} done</span>
                    </div>
                  </div>

                  {/* View all button */}
                  <button
                    onClick={() => {
                      setShowTracker(true);
                      setIsExpanded(false);
                    }}
                    className="w-full py-2 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-sm font-medium rounded-lg hover:from-amber-600 hover:to-orange-600 transition-colors"
                  >
                    View All Progress
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* New achievement notification */}
        <AnimatePresence>
          {showCelebration && (
            <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.9 }}
              className="absolute -top-16 left-1/2 -translate-x-1/2 whitespace-nowrap"
            >
              <div className="bg-emerald-500 text-white px-4 py-2 rounded-full text-sm font-medium shadow-lg flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                Tour Completed! +25 pts
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </>
  );
}
