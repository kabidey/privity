import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Pause, RotateCcw, X, ChevronLeft, ChevronRight } from 'lucide-react';

// Workflow animation data
const WORKFLOW_ANIMATIONS = {
  booking: {
    title: 'Booking Creation Workflow',
    description: 'See how to create a new booking in PRIVITY',
    duration: 12000,
    steps: [
      {
        id: 1,
        title: 'Select Client',
        description: 'Search and select an existing client or create a new one',
        icon: '👤',
        duration: 2000,
        visual: {
          type: 'form',
          fields: ['Client Search', 'Client Name', 'PAN Number'],
          highlight: 'Client Search',
        },
      },
      {
        id: 2,
        title: 'Choose Stock',
        description: 'Browse available stocks and select the one for booking',
        icon: '📈',
        duration: 2000,
        visual: {
          type: 'list',
          items: ['RELIANCE - ₹2,450', 'TCS - ₹3,890', 'HDFC - ₹1,650'],
          highlight: 'RELIANCE - ₹2,450',
        },
      },
      {
        id: 3,
        title: 'Enter Quantity',
        description: 'Specify the number of shares to book',
        icon: '🔢',
        duration: 2000,
        visual: {
          type: 'input',
          label: 'Quantity',
          value: '100',
          calculated: 'Total: ₹2,45,000',
        },
      },
      {
        id: 4,
        title: 'Set Prices',
        description: 'Enter buy price and optional sell price',
        icon: '💰',
        duration: 2000,
        visual: {
          type: 'prices',
          buyPrice: '₹2,450.00',
          sellPrice: '₹2,550.00',
          profit: '+₹10,000 (4.08%)',
        },
      },
      {
        id: 5,
        title: 'Review & Submit',
        description: 'Review booking details and submit for approval',
        icon: '✅',
        duration: 2000,
        visual: {
          type: 'summary',
          items: [
            'Client: Rajesh Kumar',
            'Stock: RELIANCE',
            'Qty: 100 shares',
            'Total: ₹2,45,000',
          ],
        },
      },
      {
        id: 6,
        title: 'Booking Created!',
        description: 'Booking is now pending approval',
        icon: '🎉',
        duration: 2000,
        visual: {
          type: 'success',
          message: 'Booking #BK-00001 created successfully!',
          status: 'Pending Approval',
        },
      },
    ],
  },
  client: {
    title: 'Client Onboarding Workflow',
    description: 'Learn how to add and verify a new client',
    duration: 10000,
    steps: [
      {
        id: 1,
        title: 'Basic Information',
        description: 'Enter client name, PAN, and contact details',
        icon: '📝',
        duration: 2000,
        visual: {
          type: 'form',
          fields: ['Full Name', 'PAN Number', 'Email', 'Mobile'],
          highlight: 'Full Name',
        },
      },
      {
        id: 2,
        title: 'Upload Documents',
        description: 'Upload KYC documents for verification',
        icon: '📄',
        duration: 2000,
        visual: {
          type: 'upload',
          documents: ['PAN Card', 'Aadhar Card', 'Address Proof'],
        },
      },
      {
        id: 3,
        title: 'Bank Details',
        description: 'Add bank account information',
        icon: '🏦',
        duration: 2000,
        visual: {
          type: 'form',
          fields: ['Bank Name', 'Account Number', 'IFSC Code'],
          highlight: 'Account Number',
        },
      },
      {
        id: 4,
        title: 'Submit for Approval',
        description: 'Client profile sent for KYC verification',
        icon: '📤',
        duration: 2000,
        visual: {
          type: 'progress',
          status: 'Submitting...',
          progress: 100,
        },
      },
      {
        id: 5,
        title: 'Client Approved!',
        description: 'Client is now ready for bookings',
        icon: '✅',
        duration: 2000,
        visual: {
          type: 'success',
          message: 'Client verified and approved!',
          status: 'Active',
        },
      },
    ],
  },
  approval: {
    title: 'Approval Workflow',
    description: 'Understanding the multi-level approval process',
    duration: 8000,
    steps: [
      {
        id: 1,
        title: 'Booking Submitted',
        description: 'Employee creates a booking request',
        icon: '📋',
        duration: 2000,
        visual: {
          type: 'status',
          from: 'Employee',
          status: 'Submitted',
          color: 'blue',
        },
      },
      {
        id: 2,
        title: 'Manager Review',
        description: 'Manager reviews and approves/rejects',
        icon: '👔',
        duration: 2000,
        visual: {
          type: 'status',
          from: 'Manager',
          status: 'Under Review',
          color: 'yellow',
        },
      },
      {
        id: 3,
        title: 'PE Desk Verification',
        description: 'PE Desk verifies inventory and pricing',
        icon: '🔍',
        duration: 2000,
        visual: {
          type: 'status',
          from: 'PE Desk',
          status: 'Verifying',
          color: 'orange',
        },
      },
      {
        id: 4,
        title: 'Approved & Executed',
        description: 'Booking is approved and executed',
        icon: '✅',
        duration: 2000,
        visual: {
          type: 'status',
          from: 'System',
          status: 'Completed',
          color: 'green',
        },
      },
    ],
  },
  reports: {
    title: 'Reports & Analytics',
    description: 'Generate and export business reports',
    duration: 8000,
    steps: [
      {
        id: 1,
        title: 'Select Report Type',
        description: 'Choose from various report categories',
        icon: '📊',
        duration: 2000,
        visual: {
          type: 'list',
          items: ['Revenue Report', 'Booking Summary', 'Client Analytics', 'P&L Statement'],
          highlight: 'Revenue Report',
        },
      },
      {
        id: 2,
        title: 'Apply Filters',
        description: 'Filter by date range, client, stock',
        icon: '🔍',
        duration: 2000,
        visual: {
          type: 'filters',
          filters: ['Date: Last 30 days', 'Client: All', 'Stock: All'],
        },
      },
      {
        id: 3,
        title: 'View Results',
        description: 'Interactive charts and data tables',
        icon: '📈',
        duration: 2000,
        visual: {
          type: 'chart',
          data: [30, 45, 60, 80, 95, 75, 90],
        },
      },
      {
        id: 4,
        title: 'Export Report',
        description: 'Download as Excel or PDF',
        icon: '📥',
        duration: 2000,
        visual: {
          type: 'export',
          formats: ['Excel (.xlsx)', 'PDF (.pdf)'],
        },
      },
    ],
  },
};

// Visual components for each step type
const StepVisual = ({ visual, isActive }) => {
  if (!visual) return null;

  switch (visual.type) {
    case 'form':
      return (
        <div className="space-y-3">
          {visual.fields.map((field, i) => (
            <motion.div
              key={field}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1 }}
              className={`p-3 rounded-lg border ${
                visual.highlight === field
                  ? 'border-emerald-500 bg-emerald-50'
                  : 'border-gray-200 bg-gray-50'
              }`}
            >
              <span className="text-sm text-gray-600">{field}</span>
            </motion.div>
          ))}
        </div>
      );

    case 'list':
      return (
        <div className="space-y-2">
          {visual.items.map((item, i) => (
            <motion.div
              key={item}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.15 }}
              className={`p-3 rounded-lg ${
                visual.highlight === item
                  ? 'bg-emerald-500 text-white'
                  : 'bg-gray-100 text-gray-700'
              }`}
            >
              {item}
            </motion.div>
          ))}
        </div>
      );

    case 'input':
      return (
        <div className="space-y-3">
          <div className="text-sm text-gray-500">{visual.label}</div>
          <motion.div
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
            className="p-4 bg-white border-2 border-emerald-500 rounded-lg text-2xl font-bold text-center"
          >
            {visual.value}
          </motion.div>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="text-center text-emerald-600 font-medium"
          >
            {visual.calculated}
          </motion.div>
        </div>
      );

    case 'prices':
      return (
        <div className="space-y-3">
          <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
            <span className="text-gray-600">Buy Price</span>
            <span className="font-bold text-blue-600">{visual.buyPrice}</span>
          </div>
          <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
            <span className="text-gray-600">Sell Price</span>
            <span className="font-bold text-green-600">{visual.sellPrice}</span>
          </div>
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="p-3 bg-emerald-100 rounded-lg text-center"
          >
            <span className="text-emerald-700 font-bold">{visual.profit}</span>
          </motion.div>
        </div>
      );

    case 'summary':
      return (
        <div className="bg-gray-50 rounded-lg p-4 space-y-2">
          {visual.items.map((item, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1 }}
              className="flex items-center gap-2 text-sm"
            >
              <span className="w-2 h-2 bg-emerald-500 rounded-full" />
              <span>{item}</span>
            </motion.div>
          ))}
        </div>
      );

    case 'success':
      return (
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="text-center py-4"
        >
          <motion.div
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 0.5, repeat: 2 }}
            className="text-5xl mb-3"
          >
            🎉
          </motion.div>
          <p className="font-semibold text-gray-800">{visual.message}</p>
          <span className="inline-block mt-2 px-3 py-1 bg-emerald-100 text-emerald-700 rounded-full text-sm">
            {visual.status}
          </span>
        </motion.div>
      );

    case 'status':
      const colors = {
        blue: 'bg-blue-100 text-blue-700 border-blue-300',
        yellow: 'bg-yellow-100 text-yellow-700 border-yellow-300',
        orange: 'bg-orange-100 text-orange-700 border-orange-300',
        green: 'bg-green-100 text-green-700 border-green-300',
      };
      return (
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className={`p-4 rounded-lg border-2 ${colors[visual.color]}`}
        >
          <div className="text-xs uppercase tracking-wide opacity-75">{visual.from}</div>
          <div className="text-lg font-bold mt-1">{visual.status}</div>
        </motion.div>
      );

    case 'chart':
      return (
        <div className="h-32 flex items-end justify-around gap-2 p-4 bg-gray-50 rounded-lg">
          {visual.data.map((value, i) => (
            <motion.div
              key={i}
              initial={{ height: 0 }}
              animate={{ height: `${value}%` }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
              className="w-8 bg-gradient-to-t from-emerald-500 to-emerald-300 rounded-t"
            />
          ))}
        </div>
      );

    case 'export':
      return (
        <div className="space-y-3">
          {visual.formats.map((format, i) => (
            <motion.button
              key={format}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.2 }}
              whileHover={{ scale: 1.02 }}
              className="w-full p-3 bg-emerald-500 text-white rounded-lg font-medium"
            >
              Download {format}
            </motion.button>
          ))}
        </div>
      );

    default:
      return null;
  }
};

export default function WorkflowAnimation({ workflowId, onClose }) {
  const workflow = WORKFLOW_ANIMATIONS[workflowId];
  const [currentStep, setCurrentStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!isPlaying || !workflow) return;

    const stepDuration = workflow.steps[currentStep]?.duration || 2000;
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          // Move to next step
          if (currentStep < workflow.steps.length - 1) {
            setCurrentStep(currentStep + 1);
            return 0;
          } else {
            setIsPlaying(false);
            return 100;
          }
        }
        return prev + (100 / (stepDuration / 50));
      });
    }, 50);

    return () => clearInterval(interval);
  }, [isPlaying, currentStep, workflow]);

  if (!workflow) return null;

  const step = workflow.steps[currentStep];

  const handleRestart = () => {
    setCurrentStep(0);
    setProgress(0);
    setIsPlaying(true);
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
      setProgress(0);
    }
  };

  const handleNext = () => {
    if (currentStep < workflow.steps.length - 1) {
      setCurrentStep(currentStep + 1);
      setProgress(0);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
    >
      <motion.div
        initial={{ scale: 0.9, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full overflow-hidden"
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-emerald-600 to-teal-600 text-white p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold">{workflow.title}</h2>
              <p className="text-emerald-100 mt-1">{workflow.description}</p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/20 rounded-full transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Progress indicators */}
          <div className="flex gap-2 mt-4">
            {workflow.steps.map((s, i) => (
              <div
                key={s.id}
                className={`h-1 flex-1 rounded-full ${
                  i < currentStep
                    ? 'bg-white'
                    : i === currentStep
                    ? 'bg-white/50'
                    : 'bg-white/20'
                }`}
              >
                {i === currentStep && (
                  <motion.div
                    className="h-full bg-white rounded-full"
                    style={{ width: `${progress}%` }}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentStep}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="grid grid-cols-2 gap-6"
            >
              {/* Step info */}
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-4xl">{step.icon}</span>
                  <div>
                    <div className="text-sm text-gray-500">
                      Step {currentStep + 1} of {workflow.steps.length}
                    </div>
                    <h3 className="text-xl font-bold text-gray-800">{step.title}</h3>
                  </div>
                </div>
                <p className="text-gray-600">{step.description}</p>
              </div>

              {/* Visual */}
              <div className="bg-gray-50 rounded-xl p-4">
                <StepVisual visual={step.visual} isActive={isPlaying} />
              </div>
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Controls */}
        <div className="border-t bg-gray-50 p-4">
          <div className="flex items-center justify-between">
            <button
              onClick={handleRestart}
              className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-800"
            >
              <RotateCcw className="w-4 h-4" />
              Restart
            </button>

            <div className="flex items-center gap-2">
              <button
                onClick={handlePrev}
                disabled={currentStep === 0}
                className="p-2 hover:bg-gray-200 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>

              <button
                onClick={() => setIsPlaying(!isPlaying)}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 flex items-center gap-2"
              >
                {isPlaying ? (
                  <>
                    <Pause className="w-4 h-4" /> Pause
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" /> Play
                  </>
                )}
              </button>

              <button
                onClick={handleNext}
                disabled={currentStep === workflow.steps.length - 1}
                className="p-2 hover:bg-gray-200 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>

            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
            >
              Close
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

export { WORKFLOW_ANIMATIONS };
