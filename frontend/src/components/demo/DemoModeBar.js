import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { X, BookOpen, Play, RotateCcw, LogOut, HelpCircle, Trophy, Star } from 'lucide-react';
import { useDemo, DEMO_TOURS, FEATURE_SHOWCASES } from '../../contexts/DemoContext';
import { useNavigate, useLocation } from 'react-router-dom';
import DemoProgressTracker from './DemoProgressTracker';

export default function DemoModeBar() {
  const { 
    isDemoMode, 
    exitDemoMode, 
    setShowFeatureShowcase,
    startTour,
    resetDemoProgress,
    completedTours 
  } = useDemo();
  const navigate = useNavigate();
  const location = useLocation();
  const [showProgressTracker, setShowProgressTracker] = useState(false);

  // Calculate total points (10 for starting + 25 per tour)
  const totalPoints = 10 + (completedTours.length * 25);

  if (!isDemoMode) return null;

  // Determine current section for contextual tour
  const getCurrentTour = () => {
    const path = location.pathname;
    if (path.includes('/dashboard')) return DEMO_TOURS.DASHBOARD;
    if (path.includes('/bookings')) return DEMO_TOURS.BOOKINGS;
    if (path.includes('/clients')) return DEMO_TOURS.CLIENTS;
    if (path.includes('/inventory')) return DEMO_TOURS.INVENTORY;
    if (path.includes('/reports')) return DEMO_TOURS.REPORTS;
    return null;
  };

  const currentTourId = getCurrentTour();
  const currentFeature = FEATURE_SHOWCASES.find(f => {
    const tourMap = {
      bookings: DEMO_TOURS.BOOKINGS,
      clients: DEMO_TOURS.CLIENTS,
      inventory: DEMO_TOURS.INVENTORY,
      reports: DEMO_TOURS.REPORTS,
    };
    return tourMap[f.id] === currentTourId;
  });

  return (
    <>
      <DemoProgressTracker 
        isOpen={showProgressTracker} 
        onClose={() => setShowProgressTracker(false)} 
      />
      
      <motion.div
        initial={{ y: -50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="fixed top-0 left-0 right-0 z-50 bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-lg"
      >
        <div className="max-w-full mx-auto px-4 py-2">
          <div className="flex items-center justify-between">
            {/* Left: Demo Badge */}
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 bg-white/20 rounded-full px-3 py-1">
                <BookOpen className="w-4 h-4" />
                <span className="font-semibold text-sm">DEMO MODE</span>
              </div>
              <span className="text-white/90 text-sm hidden md:inline">
                Run it to Learn it
              </span>
            </div>

            {/* Center: Progress & Actions */}
            <div className="flex items-center gap-4">
              {/* Points & Progress Button */}
              <button
                onClick={() => setShowProgressTracker(true)}
                className="flex items-center gap-2 bg-white/20 hover:bg-white/30 rounded-lg px-3 py-1.5 text-sm transition-colors"
              >
                <Trophy className="w-4 h-4 text-yellow-200" />
                <span className="font-semibold">{totalPoints} pts</span>
                <span className="hidden sm:inline text-white/80">•</span>
                <span className="hidden sm:inline">
                  {completedTours.length}/{Object.keys(DEMO_TOURS).length} tours
                </span>
              </button>

              {currentTourId && (
                <button
                  onClick={() => startTour(currentTourId)}
                  className="flex items-center gap-1 bg-white/20 hover:bg-white/30 rounded-lg px-3 py-1.5 text-sm transition-colors"
                >
                  <Play className="w-4 h-4" />
                  <span className="hidden sm:inline">
                    Tour {currentFeature?.title || 'this page'}
                  </span>
                </button>
              )}

              <button
                onClick={() => setShowFeatureShowcase(true)}
                className="flex items-center gap-1 bg-white/20 hover:bg-white/30 rounded-lg px-3 py-1.5 text-sm transition-colors"
              >
                <HelpCircle className="w-4 h-4" />
                <span className="hidden sm:inline">Feature Guide</span>
              </button>
            </div>

            {/* Right: Controls */}
            <div className="flex items-center gap-2">
              <button
                onClick={resetDemoProgress}
                className="p-2 hover:bg-white/20 rounded-lg transition-colors"
                title="Reset Progress"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
              <button
                onClick={() => {
                  exitDemoMode();
                  navigate('/login');
                }}
                className="flex items-center gap-1 bg-white text-orange-600 hover:bg-orange-50 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors"
              >
                <LogOut className="w-4 h-4" />
                <span>Exit Demo</span>
              </button>
            </div>
          </div>
        </div>
      </motion.div>
    </>
  );
}
