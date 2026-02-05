import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Play, ChevronRight, ChevronLeft, Sparkles, BookOpen, ArrowRight, Film } from 'lucide-react';
import { useDemo, FEATURE_SHOWCASES, DEMO_TOURS } from '../../contexts/DemoContext';
import { useNavigate } from 'react-router-dom';
import WorkflowAnimation, { WORKFLOW_ANIMATIONS } from './WorkflowAnimation';

const FeatureCard = ({ feature, index, onExplore, onWatchAnimation }) => {
  // Map features to workflow animations
  const workflowMap = {
    bookings: 'booking',
    clients: 'client',
    reports: 'reports',
  };
  const hasAnimation = workflowMap[feature.id];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="bg-white rounded-xl shadow-lg overflow-hidden hover:shadow-xl transition-shadow group"
    >
      <div className={`h-2 bg-gradient-to-r ${feature.color}`} />
      <div className="p-6">
        <div className="flex items-center gap-3 mb-3">
          <span className="text-3xl">{feature.icon}</span>
          <h3 className="text-lg font-semibold text-gray-800">{feature.title}</h3>
        </div>
        <p className="text-gray-600 text-sm mb-4">{feature.description}</p>
        <ul className="space-y-2">
          {feature.features.map((f, i) => (
            <li key={i} className="flex items-center gap-2 text-sm text-gray-500">
              <ChevronRight className="w-4 h-4 text-emerald-500" />
              {f}
            </li>
          ))}
        </ul>
        <div className="mt-4 flex items-center gap-2">
          {hasAnimation && (
            <button
              onClick={() => onWatchAnimation(workflowMap[feature.id])}
              className="flex items-center gap-1.5 px-3 py-2 bg-purple-100 text-purple-700 rounded-lg hover:bg-purple-200 transition-colors text-sm font-medium"
            >
              <Film className="w-4 h-4" />
              Watch Demo
            </button>
          )}
          <button
            onClick={() => onExplore(feature.id)}
            className="flex items-center gap-1.5 px-3 py-2 bg-emerald-100 text-emerald-700 rounded-lg hover:bg-emerald-200 transition-colors text-sm font-medium group-hover:bg-emerald-600 group-hover:text-white"
          >
            <Play className="w-4 h-4" />
            Explore
            <ArrowRight className="w-4 h-4 transform group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </div>
    </motion.div>
  );
};

const WelcomeAnimation = ({ onComplete }) => {
  const [step, setStep] = useState(0);
  
  const steps = [
    {
      title: "Welcome to PRIVITY",
      subtitle: "Run it to Learn it",
      description: "Experience the Employee workflow in our Private Equity Management System",
      icon: "🏦",
    },
    {
      title: "Create Bookings",
      subtitle: "Your primary task",
      description: "Learn how to create and manage client bookings with automated calculations",
      icon: "📝",
    },
    {
      title: "View Your Clients",
      subtitle: "Assigned to you",
      description: "Access your assigned clients and their portfolio information",
      icon: "👥",
    },
    {
      title: "Ready to Explore?",
      subtitle: "Let's get started",
      description: "Click below to explore PRIVITY as an Employee with guided tours",
      icon: "🚀",
    },
  ];

  const handleNext = () => {
    if (step < steps.length - 1) {
      setStep(step + 1);
    } else {
      onComplete();
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-gradient-to-br from-emerald-900 via-emerald-800 to-teal-900"
    >
      <div className="absolute inset-0 overflow-hidden">
        {[...Array(50)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-2 h-2 bg-white rounded-full opacity-20"
            initial={{
              x: Math.random() * window.innerWidth,
              y: Math.random() * window.innerHeight,
            }}
            animate={{
              y: [null, Math.random() * -200],
              opacity: [0.2, 0],
            }}
            transition={{
              duration: Math.random() * 3 + 2,
              repeat: Infinity,
              delay: Math.random() * 2,
            }}
          />
        ))}
      </div>

      <div className="relative z-10 text-center px-8 max-w-2xl">
        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <motion.div
              className="text-8xl mb-6"
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              {steps[step].icon}
            </motion.div>
            <h1 className="text-4xl md:text-5xl font-bold text-white mb-2">
              {steps[step].title}
            </h1>
            <p className="text-emerald-300 text-xl mb-4">{steps[step].subtitle}</p>
            <p className="text-gray-300 text-lg mb-8">{steps[step].description}</p>
          </motion.div>
        </AnimatePresence>

        <div className="flex items-center justify-center gap-2 mb-8">
          {steps.map((_, i) => (
            <div
              key={i}
              className={`w-3 h-3 rounded-full transition-colors ${
                i === step ? 'bg-emerald-400' : 'bg-white/30'
              }`}
            />
          ))}
        </div>

        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleNext}
          className="px-8 py-4 bg-white text-emerald-700 rounded-full font-semibold text-lg shadow-lg hover:shadow-xl transition-shadow flex items-center gap-2 mx-auto"
        >
          {step < steps.length - 1 ? (
            <>
              Next <ChevronRight className="w-5 h-5" />
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5" /> Start Exploring
            </>
          )}
        </motion.button>

        {step > 0 && (
          <button
            onClick={() => setStep(step - 1)}
            className="mt-4 text-white/70 hover:text-white flex items-center gap-1 mx-auto"
          >
            <ChevronLeft className="w-4 h-4" /> Back
          </button>
        )}
      </div>
    </motion.div>
  );
};

export default function FeatureShowcase() {
  const { 
    showFeatureShowcase, 
    setShowFeatureShowcase, 
    showWelcome, 
    setShowWelcome,
    startTour,
    exitDemoMode,
    completedTours 
  } = useDemo();
  const navigate = useNavigate();
  const [showWelcomeAnim, setShowWelcomeAnim] = useState(showWelcome);
  const [activeWorkflow, setActiveWorkflow] = useState(null);

  const handleExplore = (featureId) => {
    // Map feature to tour and route
    const featureRoutes = {
      bookings: { route: '/bookings', tour: DEMO_TOURS.BOOKINGS },
      clients: { route: '/clients', tour: DEMO_TOURS.CLIENTS },
      inventory: { route: '/inventory', tour: DEMO_TOURS.INVENTORY },
      reports: { route: '/reports', tour: DEMO_TOURS.REPORTS },
      security: { route: '/roles', tour: null },
      partners: { route: '/business-partners', tour: null },
    };

    const config = featureRoutes[featureId];
    if (config) {
      setShowFeatureShowcase(false);
      navigate(config.route);
      if (config.tour) {
        setTimeout(() => startTour(config.tour), 500);
      }
    }
  };

  const handleWatchAnimation = (workflowId) => {
    setActiveWorkflow(workflowId);
  };

  const handleWelcomeComplete = () => {
    setShowWelcomeAnim(false);
    setShowWelcome(false);
  };

  if (!showFeatureShowcase) return null;

  return (
    <>
      <AnimatePresence>
        {showWelcomeAnim && <WelcomeAnimation onComplete={handleWelcomeComplete} />}
      </AnimatePresence>

      {/* Workflow Animation Modal */}
      <AnimatePresence>
        {activeWorkflow && (
          <WorkflowAnimation
            workflowId={activeWorkflow}
            onClose={() => setActiveWorkflow(null)}
          />
        )}
      </AnimatePresence>

      {!showWelcomeAnim && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed inset-0 z-40 bg-gray-50 overflow-y-auto ml-0 md:ml-[220px]"
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-emerald-600 to-teal-600 text-white">
            <div className="max-w-6xl mx-auto px-6 py-8">
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <BookOpen className="w-8 h-8" />
                    <h1 className="text-3xl font-bold">PRIVITY Demo</h1>
                  </div>
                  <p className="text-emerald-100 text-lg">Run it to Learn it</p>
                </div>
                <button
                  onClick={exitDemoMode}
                  className="p-2 hover:bg-white/20 rounded-full transition-colors"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
            </div>
          </div>

          {/* Progress */}
          <div className="bg-white border-b shadow-sm">
            <div className="max-w-6xl mx-auto px-6 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-gray-600">Tour Progress:</span>
                  <span className="font-semibold text-emerald-600">
                    {completedTours.length} / {Object.keys(DEMO_TOURS).length} completed
                  </span>
                </div>
                <button
                  onClick={() => {
                    setShowFeatureShowcase(false);
                    navigate('/dashboard');
                    setTimeout(() => startTour(DEMO_TOURS.DASHBOARD), 500);
                  }}
                  className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors flex items-center gap-2"
                >
                  <Play className="w-4 h-4" />
                  Start Guided Tour
                </button>
              </div>
            </div>
          </div>

          {/* Feature Cards */}
          <div className="max-w-6xl mx-auto px-6 py-8">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">Explore Features</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {FEATURE_SHOWCASES.map((feature, index) => (
                <FeatureCard
                  key={feature.id}
                  feature={feature}
                  index={index}
                  onExplore={handleExplore}
                  onWatchAnimation={handleWatchAnimation}
                />
              ))}
            </div>

            {/* Video Animations Section */}
            <div className="mt-12 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-xl p-6">
              <div className="flex items-center gap-3 mb-4">
                <Film className="w-6 h-6 text-purple-600" />
                <h3 className="text-xl font-semibold text-gray-800">Video Walkthroughs</h3>
              </div>
              <p className="text-gray-600 mb-4">Watch animated demonstrations of key workflows</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(WORKFLOW_ANIMATIONS).map(([id, workflow]) => (
                  <button
                    key={id}
                    onClick={() => handleWatchAnimation(id)}
                    className="p-4 bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow text-left"
                  >
                    <div className="text-2xl mb-2">
                      {id === 'booking' ? '📝' : id === 'client' ? '👤' : id === 'approval' ? '✅' : '📊'}
                    </div>
                    <div className="font-medium text-gray-800 text-sm">{workflow.title}</div>
                    <div className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                      <Play className="w-3 h-3" />
                      {Math.round(workflow.duration / 1000)}s
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="mt-12 bg-white rounded-xl shadow-lg p-6">
              <h3 className="text-xl font-semibold text-gray-800 mb-4">Quick Actions</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <button
                  onClick={() => {
                    setShowFeatureShowcase(false);
                    navigate('/bookings');
                  }}
                  className="p-4 bg-emerald-50 hover:bg-emerald-100 rounded-lg text-center transition-colors"
                >
                  <span className="text-2xl block mb-2">📝</span>
                  <span className="text-sm font-medium text-gray-700">Create Booking</span>
                </button>
                <button
                  onClick={() => {
                    setShowFeatureShowcase(false);
                    navigate('/clients');
                  }}
                  className="p-4 bg-blue-50 hover:bg-blue-100 rounded-lg text-center transition-colors"
                >
                  <span className="text-2xl block mb-2">👤</span>
                  <span className="text-sm font-medium text-gray-700">Add Client</span>
                </button>
                <button
                  onClick={() => {
                    setShowFeatureShowcase(false);
                    navigate('/reports');
                  }}
                  className="p-4 bg-purple-50 hover:bg-purple-100 rounded-lg text-center transition-colors"
                >
                  <span className="text-2xl block mb-2">📊</span>
                  <span className="text-sm font-medium text-gray-700">View Reports</span>
                </button>
                <button
                  onClick={() => {
                    setShowFeatureShowcase(false);
                    navigate('/dashboard');
                  }}
                  className="p-4 bg-orange-50 hover:bg-orange-100 rounded-lg text-center transition-colors"
                >
                  <span className="text-2xl block mb-2">🏠</span>
                  <span className="text-sm font-medium text-gray-700">Go to Dashboard</span>
                </button>
              </div>
            </div>

            {/* Demo Info */}
            <div className="mt-8 bg-amber-50 border border-amber-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <span className="text-2xl">💡</span>
                <div>
                  <h4 className="font-semibold text-amber-800">Demo Mode Active</h4>
                  <p className="text-amber-700 text-sm mt-1">
                    You're exploring PRIVITY with sample data. All changes are temporary and won't affect real data.
                    Click the "Exit Demo" button in the top bar to return to the login page.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </>
  );
}
