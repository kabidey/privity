import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Trophy, Star, Award, Medal, Target, Zap, Crown, Flame,
  CheckCircle, Circle, Lock, ChevronRight, X, Sparkles,
  BookOpen, Users, ShoppingCart, BarChart3, Shield, Handshake
} from 'lucide-react';
import { useDemo, DEMO_TOURS, FEATURE_SHOWCASES } from '../../contexts/DemoContext';

// Badge definitions
const BADGES = {
  explorer: {
    id: 'explorer',
    name: 'Explorer',
    description: 'Started your PRIVITY journey',
    icon: Star,
    color: 'from-yellow-400 to-orange-500',
    requirement: 'Start demo mode',
    points: 10,
  },
  bookingMaster: {
    id: 'bookingMaster',
    name: 'Booking Master',
    description: 'Completed the Bookings tour',
    icon: BookOpen,
    color: 'from-emerald-400 to-teal-500',
    requirement: 'Complete bookings tour',
    tourId: DEMO_TOURS.BOOKINGS,
    points: 25,
  },
  clientPro: {
    id: 'clientPro',
    name: 'Client Pro',
    description: 'Mastered client management',
    icon: Users,
    color: 'from-blue-400 to-indigo-500',
    requirement: 'Complete clients tour',
    tourId: DEMO_TOURS.CLIENTS,
    points: 25,
  },
  inventoryGuru: {
    id: 'inventoryGuru',
    name: 'Inventory Guru',
    description: 'Understood inventory tracking',
    icon: ShoppingCart,
    color: 'from-purple-400 to-pink-500',
    requirement: 'Complete inventory tour',
    tourId: DEMO_TOURS.INVENTORY,
    points: 25,
  },
  analyticsWizard: {
    id: 'analyticsWizard',
    name: 'Analytics Wizard',
    description: 'Explored reports and analytics',
    icon: BarChart3,
    color: 'from-cyan-400 to-blue-500',
    requirement: 'Complete reports tour',
    tourId: DEMO_TOURS.REPORTS,
    points: 25,
  },
  dashboardChampion: {
    id: 'dashboardChampion',
    name: 'Dashboard Champion',
    description: 'Mastered the PE Dashboard',
    icon: Target,
    color: 'from-orange-400 to-red-500',
    requirement: 'Complete dashboard tour',
    tourId: DEMO_TOURS.DASHBOARD,
    points: 25,
  },
  tourComplete: {
    id: 'tourComplete',
    name: 'Tour Complete',
    description: 'Completed all guided tours',
    icon: Trophy,
    color: 'from-amber-400 to-yellow-500',
    requirement: 'Complete all tours',
    points: 50,
  },
  speedRunner: {
    id: 'speedRunner',
    name: 'Speed Runner',
    description: 'Explored 3 features in under 5 minutes',
    icon: Zap,
    color: 'from-violet-400 to-purple-500',
    requirement: 'Quick exploration',
    points: 30,
  },
  privityMaster: {
    id: 'privityMaster',
    name: 'PRIVITY Master',
    description: 'Achieved 100% demo completion',
    icon: Crown,
    color: 'from-gradient-to-r from-yellow-300 via-amber-400 to-orange-500',
    requirement: 'Complete everything',
    points: 100,
  },
};

// Feature exploration tracking
const FEATURES_TO_EXPLORE = [
  { id: 'dashboard', name: 'Dashboard', icon: Target, path: '/dashboard' },
  { id: 'bookings', name: 'Bookings', icon: BookOpen, path: '/bookings' },
  { id: 'clients', name: 'Clients', icon: Users, path: '/clients' },
  { id: 'inventory', name: 'Inventory', icon: ShoppingCart, path: '/inventory' },
  { id: 'reports', name: 'Reports', icon: BarChart3, path: '/reports' },
  { id: 'roles', name: 'Role Management', icon: Shield, path: '/roles' },
  { id: 'partners', name: 'Partners', icon: Handshake, path: '/business-partners' },
];

// Badge unlock celebration component
const BadgeUnlockCelebration = ({ badge, onClose }) => {
  const IconComponent = badge.icon;
  
  // Pre-generate confetti positions for stable rendering
  const confettiPositions = React.useMemo(() => 
    [...Array(20)].map((_, i) => ({
      color: ['#fbbf24', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6'][i % 5],
      left: `${(i * 5) % 100}%`,
      xOffset: ((i % 3) - 1) * 50,
      rotateDir: i % 2 === 0 ? 1 : -1,
      duration: 2 + (i % 3) * 0.5,
      delay: (i % 10) * 0.05,
    }))
  , []);
  
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0, rotate: -180 }}
        animate={{ scale: 1, rotate: 0 }}
        transition={{ type: 'spring', damping: 15 }}
        className="bg-white rounded-2xl p-8 max-w-sm text-center relative overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Confetti effect */}
        <div className="absolute inset-0 pointer-events-none">
          {confettiPositions.map((conf, i) => (
            <motion.div
              key={i}
              className="absolute w-2 h-2 rounded-full"
              style={{
                backgroundColor: conf.color,
                left: conf.left,
                top: '-10%',
              }}
              animate={{
                y: ['0%', '1000%'],
                x: [0, conf.xOffset],
                rotate: [0, 360 * conf.rotateDir],
              }}
              transition={{
                duration: conf.duration,
                delay: conf.delay,
                repeat: Infinity,
              }}
            />
          ))}
        </div>

        <motion.div
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 1, repeat: Infinity }}
          className={`w-24 h-24 mx-auto rounded-full bg-gradient-to-br ${badge.color} flex items-center justify-center mb-4 shadow-lg`}
        >
          <IconComponent className="w-12 h-12 text-white" />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <div className="flex items-center justify-center gap-2 mb-2">
            <Sparkles className="w-5 h-5 text-amber-500" />
            <span className="text-sm font-medium text-amber-600">Badge Unlocked!</span>
            <Sparkles className="w-5 h-5 text-amber-500" />
          </div>
          
          <h2 className="text-2xl font-bold text-gray-800 mb-2">{badge.name}</h2>
          <p className="text-gray-600 mb-4">{badge.description}</p>
          
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-amber-100 rounded-full">
            <Trophy className="w-4 h-4 text-amber-600" />
            <span className="font-semibold text-amber-700">+{badge.points} points</span>
          </div>
        </motion.div>

        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
        >
          <X className="w-5 h-5" />
        </button>
      </motion.div>
    </motion.div>
  );
};

// Single badge display
const BadgeCard = ({ badge, isUnlocked, onClick }) => {
  const IconComponent = badge.icon;
  
  return (
    <motion.div
      whileHover={{ scale: isUnlocked ? 1.05 : 1 }}
      whileTap={{ scale: 0.95 }}
      onClick={() => isUnlocked && onClick?.(badge)}
      className={`relative p-4 rounded-xl border-2 transition-all cursor-pointer ${
        isUnlocked
          ? 'bg-white border-amber-200 shadow-md hover:shadow-lg'
          : 'bg-gray-50 border-gray-200 opacity-60'
      }`}
    >
      <div
        className={`w-12 h-12 mx-auto rounded-full flex items-center justify-center mb-2 ${
          isUnlocked
            ? `bg-gradient-to-br ${badge.color}`
            : 'bg-gray-300'
        }`}
      >
        {isUnlocked ? (
          <IconComponent className="w-6 h-6 text-white" />
        ) : (
          <Lock className="w-5 h-5 text-gray-500" />
        )}
      </div>
      
      <h4 className={`text-sm font-semibold text-center ${isUnlocked ? 'text-gray-800' : 'text-gray-500'}`}>
        {badge.name}
      </h4>
      
      <p className="text-xs text-center text-gray-500 mt-1">
        {isUnlocked ? `+${badge.points} pts` : badge.requirement}
      </p>
      
      {isUnlocked && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="absolute -top-1 -right-1 w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center"
        >
          <CheckCircle className="w-4 h-4 text-white" />
        </motion.div>
      )}
    </motion.div>
  );
};

// Progress ring component
const ProgressRing = ({ progress, size = 120, strokeWidth = 8 }) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (progress / 100) * circumference;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg className="transform -rotate-90" width={size} height={size}>
        <circle
          className="text-gray-200"
          strokeWidth={strokeWidth}
          stroke="currentColor"
          fill="transparent"
          r={radius}
          cx={size / 2}
          cy={size / 2}
        />
        <motion.circle
          className="text-emerald-500"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          stroke="currentColor"
          fill="transparent"
          r={radius}
          cx={size / 2}
          cy={size / 2}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: 'easeOut' }}
          style={{
            strokeDasharray: circumference,
          }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="text-center">
          <span className="text-2xl font-bold text-gray-800">{Math.round(progress)}%</span>
          <p className="text-xs text-gray-500">Complete</p>
        </div>
      </div>
    </div>
  );
};

// Main Progress Tracker Component
export default function DemoProgressTracker({ isOpen, onClose }) {
  const { completedTours, isDemoMode, demoStartTime, exploredFeatures } = useDemo();
  const [unlockedBadges, setUnlockedBadges] = useState(['explorer']);
  const [totalPoints, setTotalPoints] = useState(10);
  const [newBadge, setNewBadge] = useState(null);

  // Load progress from localStorage
  useEffect(() => {
    const savedProgress = localStorage.getItem('privity_demo_progress');
    if (savedProgress) {
      const parsed = JSON.parse(savedProgress);
      setUnlockedBadges(parsed.unlockedBadges || ['explorer']);
      setTotalPoints(parsed.totalPoints || 10);
    }
  }, []);

  // Save progress to localStorage
  useEffect(() => {
    if (isDemoMode) {
      localStorage.setItem('privity_demo_progress', JSON.stringify({
        unlockedBadges,
        exploredFeatures,
        totalPoints,
      }));
    }
  }, [unlockedBadges, exploredFeatures, totalPoints, isDemoMode]);

  // Check for badge unlocks based on completed tours
  useEffect(() => {
    const newBadges = [];

    // Check tour-based badges
    Object.values(BADGES).forEach(badge => {
      if (badge.tourId && completedTours.includes(badge.tourId) && !unlockedBadges.includes(badge.id)) {
        newBadges.push(badge.id);
      }
    });

    // Check if all tours completed
    const allToursCompleted = Object.values(DEMO_TOURS).every(tour => completedTours.includes(tour));
    if (allToursCompleted && !unlockedBadges.includes('tourComplete')) {
      newBadges.push('tourComplete');
    }

    // Check speed runner (3 features in 5 minutes)
    const timeElapsed = (Date.now() - demoStartTime) / 1000 / 60; // minutes
    if (exploredFeatures.length >= 3 && timeElapsed < 5 && !unlockedBadges.includes('speedRunner')) {
      newBadges.push('speedRunner');
    }

    // Check PRIVITY Master (everything complete)
    if (unlockedBadges.length >= Object.keys(BADGES).length - 1 && !unlockedBadges.includes('privityMaster')) {
      newBadges.push('privityMaster');
    }

    if (newBadges.length > 0) {
      const badgeToShow = BADGES[newBadges[0]];
      setNewBadge(badgeToShow);
      setUnlockedBadges(prev => [...prev, ...newBadges]);
      setTotalPoints(prev => prev + newBadges.reduce((sum, id) => sum + BADGES[id].points, 0));
    }
  }, [completedTours, exploredFeatures, unlockedBadges, demoStartTime]);

  // Calculate progress
  const totalBadges = Object.keys(BADGES).length;
  const progress = (unlockedBadges.length / totalBadges) * 100;
  const toursProgress = (completedTours.length / Object.keys(DEMO_TOURS).length) * 100;

  if (!isOpen) return null;

  return (
    <>
      {/* Badge unlock celebration */}
      <AnimatePresence>
        {newBadge && (
          <BadgeUnlockCelebration badge={newBadge} onClose={() => setNewBadge(null)} />
        )}
      </AnimatePresence>

      {/* Main tracker modal */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.9, y: 20 }}
          className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-amber-500 to-orange-500 text-white p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-white/20 rounded-full flex items-center justify-center">
                  <Trophy className="w-8 h-8" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold">Demo Progress</h2>
                  <p className="text-amber-100">Track your exploration journey</p>
                </div>
              </div>
              <button onClick={onClose} className="p-2 hover:bg-white/20 rounded-full">
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* Stats bar */}
            <div className="flex items-center gap-6 mt-6">
              <div className="flex items-center gap-2">
                <Award className="w-5 h-5 text-amber-200" />
                <span className="font-semibold">{unlockedBadges.length}/{totalBadges} Badges</span>
              </div>
              <div className="flex items-center gap-2">
                <Star className="w-5 h-5 text-amber-200" />
                <span className="font-semibold">{totalPoints} Points</span>
              </div>
              <div className="flex items-center gap-2">
                <Target className="w-5 h-5 text-amber-200" />
                <span className="font-semibold">{completedTours.length}/{Object.keys(DEMO_TOURS).length} Tours</span>
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto max-h-[60vh]">
            {/* Progress Overview */}
            <div className="flex items-center justify-center gap-8 mb-8">
              <ProgressRing progress={progress} />
              <div>
                <h3 className="text-lg font-semibold text-gray-800 mb-2">Your Progress</h3>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-emerald-500" />
                    <span className="text-sm text-gray-600">{unlockedBadges.length} badges unlocked</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-emerald-500" />
                    <span className="text-sm text-gray-600">{completedTours.length} tours completed</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Flame className="w-4 h-4 text-orange-500" />
                    <span className="text-sm text-gray-600">{totalPoints} total points earned</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Tours Progress */}
            <div className="mb-8">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Guided Tours</h3>
              <div className="space-y-3">
                {Object.entries(DEMO_TOURS).map(([key, tourId]) => {
                  const isCompleted = completedTours.includes(tourId);
                  return (
                    <div
                      key={key}
                      className={`flex items-center justify-between p-3 rounded-lg ${
                        isCompleted ? 'bg-emerald-50' : 'bg-gray-50'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        {isCompleted ? (
                          <CheckCircle className="w-5 h-5 text-emerald-500" />
                        ) : (
                          <Circle className="w-5 h-5 text-gray-300" />
                        )}
                        <span className={isCompleted ? 'text-emerald-700' : 'text-gray-600'}>
                          {key.charAt(0) + key.slice(1).toLowerCase()} Tour
                        </span>
                      </div>
                      {isCompleted && (
                        <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-1 rounded-full">
                          +25 pts
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Badges Collection */}
            <div>
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Badge Collection</h3>
              <div className="grid grid-cols-3 md:grid-cols-4 gap-4">
                {Object.values(BADGES).map((badge) => (
                  <BadgeCard
                    key={badge.id}
                    badge={badge}
                    isUnlocked={unlockedBadges.includes(badge.id)}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="border-t bg-gray-50 p-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-500">
                Keep exploring to unlock all badges!
              </p>
              <button
                onClick={onClose}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700"
              >
                Continue Exploring
              </button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </>
  );
}

export { BADGES, BadgeUnlockCelebration };
