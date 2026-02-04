import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../utils/api';

const DemoContext = createContext(null);

export const DEMO_TOURS = {
  DASHBOARD: 'dashboard',
  BOOKINGS: 'bookings',
  CLIENTS: 'clients',
  INVENTORY: 'inventory',
  REPORTS: 'reports',
  USERS: 'users',
  SETTINGS: 'settings',
};

// Demo tour steps for each section
export const TOUR_STEPS = {
  [DEMO_TOURS.DASHBOARD]: [
    {
      target: '[data-testid="pe-dashboard"]',
      content: 'Welcome to the PE Dashboard! This is your command center for managing all private equity operations.',
      disableBeacon: true,
      placement: 'center',
    },
    {
      target: '[data-testid="stats-cards"]',
      content: 'Quick stats show your key metrics at a glance - total bookings, revenue, clients, and more.',
      placement: 'bottom',
    },
    {
      target: '[data-testid="recent-bookings"]',
      content: 'Recent bookings appear here with real-time status updates.',
      placement: 'top',
    },
    {
      target: '[data-testid="pending-approvals"]',
      content: 'Pending items requiring your attention are highlighted for quick action.',
      placement: 'left',
    },
  ],
  [DEMO_TOURS.BOOKINGS]: [
    {
      target: '[data-testid="bookings-page"]',
      content: 'The Bookings module is the heart of PRIVITY - manage all client investments here.',
      disableBeacon: true,
      placement: 'center',
    },
    {
      target: '[data-testid="create-booking-btn"]',
      content: 'Click here to create a new booking for a client.',
      placement: 'bottom',
    },
    {
      target: '[data-testid="booking-filters"]',
      content: 'Filter bookings by status, date, client, or stock.',
      placement: 'bottom',
    },
    {
      target: '[data-testid="booking-table"]',
      content: 'View all bookings with details like client, stock, quantity, and profit/loss.',
      placement: 'top',
    },
  ],
  [DEMO_TOURS.CLIENTS]: [
    {
      target: '[data-testid="clients-page"]',
      content: 'Manage all your clients and their KYC documents in one place.',
      disableBeacon: true,
      placement: 'center',
    },
    {
      target: '[data-testid="add-client-btn"]',
      content: 'Add new clients with complete KYC verification workflow.',
      placement: 'bottom',
    },
    {
      target: '[data-testid="client-search"]',
      content: 'Search clients by name, PAN, or mobile number.',
      placement: 'bottom',
    },
  ],
  [DEMO_TOURS.INVENTORY]: [
    {
      target: '[data-testid="inventory-page"]',
      content: 'Track your stock inventory with real-time pricing and availability.',
      disableBeacon: true,
      placement: 'center',
    },
    {
      target: '[data-testid="inventory-table"]',
      content: 'View available stocks, quantities, and weighted average pricing.',
      placement: 'top',
    },
  ],
  [DEMO_TOURS.REPORTS]: [
    {
      target: '[data-testid="reports-page"]',
      content: 'Generate comprehensive reports for revenue, bookings, and analytics.',
      disableBeacon: true,
      placement: 'center',
    },
    {
      target: '[data-testid="report-filters"]',
      content: 'Filter reports by date range, client, or stock.',
      placement: 'bottom',
    },
    {
      target: '[data-testid="export-btn"]',
      content: 'Export reports to Excel or PDF for offline analysis.',
      placement: 'left',
    },
  ],
};

// Feature showcase data
export const FEATURE_SHOWCASES = [
  {
    id: 'bookings',
    title: 'Smart Booking Management',
    description: 'Create, track, and manage client bookings with automated profit/loss calculations.',
    icon: '📝',
    color: 'from-emerald-500 to-teal-600',
    features: ['One-click booking creation', 'Real-time P&L tracking', 'Multi-level approval workflow', 'Contract note generation'],
  },
  {
    id: 'clients',
    title: 'Client Management',
    description: 'Complete KYC management with document verification and approval workflows.',
    icon: '👥',
    color: 'from-blue-500 to-indigo-600',
    features: ['Digital KYC submission', 'Document verification', 'Approval workflow', 'Client portfolio view'],
  },
  {
    id: 'inventory',
    title: 'Inventory Tracking',
    description: 'Real-time stock inventory with weighted average pricing and availability.',
    icon: '📦',
    color: 'from-orange-500 to-red-600',
    features: ['Live inventory levels', 'WAP calculation', 'Purchase management', 'Stock transfers'],
  },
  {
    id: 'reports',
    title: 'Business Intelligence',
    description: 'Comprehensive reporting with custom filters and export capabilities.',
    icon: '📊',
    color: 'from-purple-500 to-pink-600',
    features: ['Revenue reports', 'Client analytics', 'Booking summaries', 'Excel/PDF export'],
  },
  {
    id: 'security',
    title: 'Role-Based Access',
    description: 'Granular permission system with 26+ permission categories.',
    icon: '🔐',
    color: 'from-gray-600 to-slate-700',
    features: ['Custom roles', 'Fine-grained permissions', 'Audit logging', 'Secure authentication'],
  },
  {
    id: 'partners',
    title: 'Partner Network',
    description: 'Manage Business Partners and Referral Partners with revenue sharing.',
    icon: '🤝',
    color: 'from-cyan-500 to-blue-600',
    features: ['BP/RP onboarding', 'Revenue share tracking', 'Commission management', 'Partner dashboard'],
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
    enterDemoMode,
    exitDemoMode,
    startTour,
    completeTour,
    skipTour,
    resetDemoProgress,
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
