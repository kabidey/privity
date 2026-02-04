import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../utils/api';

const DemoContext = createContext(null);

export const DEMO_TOURS = {
  DASHBOARD: 'dashboard',
  BOOKINGS: 'bookings',
  CLIENTS: 'clients',
  INVENTORY: 'inventory',
};

// Demo tour steps for each section - Employee focused
export const TOUR_STEPS = {
  [DEMO_TOURS.DASHBOARD]: [
    {
      target: '[data-testid="pe-dashboard"]',
      content: 'Welcome to your Dashboard! View your key metrics and recent activities here.',
      disableBeacon: true,
      placement: 'center',
    },
    {
      target: '[data-testid="stats-cards"]',
      content: 'Quick stats show your personal performance - bookings created, clients managed, and more.',
      placement: 'bottom',
    },
    {
      target: '[data-testid="recent-bookings"]',
      content: 'Your recent bookings appear here with real-time status updates.',
      placement: 'top',
    },
  ],
  [DEMO_TOURS.BOOKINGS]: [
    {
      target: '[data-testid="bookings-page"]',
      content: 'The Bookings page is where you create and manage client investments.',
      disableBeacon: true,
      placement: 'center',
    },
    {
      target: '[data-testid="create-booking-btn"]',
      content: 'Click here to create a new booking for your assigned clients.',
      placement: 'bottom',
    },
    {
      target: '[data-testid="booking-filters"]',
      content: 'Filter your bookings by status, date, client, or stock.',
      placement: 'bottom',
    },
    {
      target: '[data-testid="booking-table"]',
      content: 'View all your bookings with details like client, stock, quantity, and profit/loss.',
      placement: 'top',
    },
  ],
  [DEMO_TOURS.CLIENTS]: [
    {
      target: '[data-testid="clients-page"]',
      content: 'View your assigned clients and their information here.',
      disableBeacon: true,
      placement: 'center',
    },
    {
      target: '[data-testid="client-search"]',
      content: 'Search clients by name, PAN, or mobile number.',
      placement: 'bottom',
    },
    {
      target: '[data-testid="client-table"]',
      content: 'View client details and their booking history.',
      placement: 'top',
    },
  ],
  [DEMO_TOURS.INVENTORY]: [
    {
      target: '[data-testid="inventory-page"]',
      content: 'View available stock inventory and pricing information.',
      disableBeacon: true,
      placement: 'center',
    },
    {
      target: '[data-testid="inventory-table"]',
      content: 'Check available stocks, quantities, and pricing before creating bookings.',
      placement: 'top',
    },
  ],
};

// Feature showcase data - Employee Role focused features
export const FEATURE_SHOWCASES = [
  {
    id: 'bookings',
    title: 'Booking Management',
    description: 'Create and manage client bookings with automated profit/loss calculations.',
    icon: '📝',
    color: 'from-emerald-500 to-teal-600',
    features: ['One-click booking creation', 'Real-time P&L tracking', 'View booking history', 'Track booking status'],
  },
  {
    id: 'clients',
    title: 'Client Management',
    description: 'View your assigned clients and their details.',
    icon: '👥',
    color: 'from-blue-500 to-indigo-600',
    features: ['View assigned clients', 'Client portfolio overview', 'Search by name or PAN', 'Client booking history'],
  },
  {
    id: 'inventory',
    title: 'Stock Inventory',
    description: 'View available stock inventory and pricing information.',
    icon: '📦',
    color: 'from-orange-500 to-red-600',
    features: ['View available stocks', 'Check stock quantities', 'Landing price info', 'Stock availability'],
  },
  {
    id: 'dashboard',
    title: 'My Dashboard',
    description: 'Your personal dashboard with key metrics and recent activities.',
    icon: '📊',
    color: 'from-purple-500 to-pink-600',
    features: ['Personal booking stats', 'Recent activities', 'Performance overview', 'Quick actions'],
  },
];

export function DemoProvider({ children }) {
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [showFeatureShowcase, setShowFeatureShowcase] = useState(false);
  const [currentTour, setCurrentTour] = useState(null);
  const [tourStepIndex, setTourStepIndex] = useState(0);
  const [completedTours, setCompletedTours] = useState([]);
  const [showWelcome, setShowWelcome] = useState(true);
  const [exploredFeatures, setExploredFeatures] = useState([]);
  const [demoStartTime, setDemoStartTime] = useState(null);

  // Load demo state from localStorage
  useEffect(() => {
    const demoState = localStorage.getItem('privity_demo_state');
    if (demoState) {
      const parsed = JSON.parse(demoState);
      setCompletedTours(parsed.completedTours || []);
      setShowWelcome(parsed.showWelcome !== false);
    }
  }, []);

  // Save demo state to localStorage
  useEffect(() => {
    if (isDemoMode) {
      localStorage.setItem('privity_demo_state', JSON.stringify({
        completedTours,
        showWelcome,
      }));
    }
  }, [isDemoMode, completedTours, showWelcome]);

  const enterDemoMode = useCallback(() => {
    setIsDemoMode(true);
    setShowFeatureShowcase(true);
    setShowWelcome(true);
    setDemoStartTime(Date.now());
  }, []);

  const exitDemoMode = useCallback(async () => {
    // Clean up demo data on the server
    try {
      await api.post('/demo/cleanup');
      console.log('Demo data cleaned up successfully');
    } catch (error) {
      console.error('Failed to cleanup demo data:', error);
    }
    
    // Clear local state
    setIsDemoMode(false);
    setShowFeatureShowcase(false);
    setCurrentTour(null);
    setTourStepIndex(0);
    setExploredFeatures([]);
    setDemoStartTime(null);
    localStorage.removeItem('privity_demo_state');
    localStorage.removeItem('privity_demo_progress');
    localStorage.removeItem('demo_token');
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }, []);

  const trackFeatureExploration = useCallback((featureId) => {
    setExploredFeatures(prev => {
      if (!prev.includes(featureId)) {
        return [...prev, featureId];
      }
      return prev;
    });
  }, []);

  const startTour = useCallback((tourId) => {
    setCurrentTour(tourId);
    setTourStepIndex(0);
    setShowFeatureShowcase(false);
  }, []);

  const completeTour = useCallback((tourId) => {
    setCompletedTours(prev => [...new Set([...prev, tourId])]);
    setCurrentTour(null);
    setTourStepIndex(0);
  }, []);

  const skipTour = useCallback(() => {
    setCurrentTour(null);
    setTourStepIndex(0);
  }, []);

  const resetDemoProgress = useCallback(() => {
    setCompletedTours([]);
    setShowWelcome(true);
    localStorage.removeItem('privity_demo_state');
  }, []);

  const value = {
    isDemoMode,
    showFeatureShowcase,
    setShowFeatureShowcase,
    currentTour,
    tourStepIndex,
    setTourStepIndex,
    completedTours,
    showWelcome,
    setShowWelcome,
    exploredFeatures,
    demoStartTime,
    enterDemoMode,
    exitDemoMode,
    startTour,
    completeTour,
    skipTour,
    resetDemoProgress,
    trackFeatureExploration,
    tourSteps: currentTour ? TOUR_STEPS[currentTour] || [] : [],
  };

  return (
    <DemoContext.Provider value={value}>
      {children}
    </DemoContext.Provider>
  );
}

export function useDemo() {
  const context = useContext(DemoContext);
  if (!context) {
    throw new Error('useDemo must be used within a DemoProvider');
  }
  return context;
}

export default DemoContext;
