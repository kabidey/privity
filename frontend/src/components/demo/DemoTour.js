import React, { useState, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ChevronLeft, ChevronRight, SkipForward } from 'lucide-react';
import { useDemo } from '../../contexts/DemoContext';

const Spotlight = ({ target, onNext, onPrev, onSkip, step, totalSteps, content }) => {
  const [position, setPosition] = useState({ top: 0, left: 0, width: 0, height: 0 });
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0, left: 0 });

  useEffect(() => {
    const element = document.querySelector(target);
    if (element) {
      const rect = element.getBoundingClientRect();
      setPosition({
        top: rect.top + window.scrollY - 8,
        left: rect.left + window.scrollX - 8,
        width: rect.width + 16,
        height: rect.height + 16,
      });

      // Calculate tooltip position
      const tooltipWidth = 320;
      const tooltipHeight = 200;
      let tooltipTop = rect.bottom + window.scrollY + 16;
      let tooltipLeft = rect.left + window.scrollX;

      // Ensure tooltip stays in viewport
      if (tooltipLeft + tooltipWidth > window.innerWidth) {
        tooltipLeft = window.innerWidth - tooltipWidth - 16;
      }
      if (tooltipTop + tooltipHeight > window.innerHeight + window.scrollY) {
        tooltipTop = rect.top + window.scrollY - tooltipHeight - 16;
      }

      setTooltipPosition({ top: tooltipTop, left: Math.max(16, tooltipLeft) });

      // Scroll element into view
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [target]);

  return createPortal(
    <>
      {/* Overlay */}
      <div className="fixed inset-0 z-[9998] pointer-events-none">
        <svg className="w-full h-full" style={{ position: 'absolute', top: 0, left: 0 }}>
          <defs>
            <mask id="spotlight-mask">
              <rect x="0" y="0" width="100%" height="100%" fill="white" />
              <rect
                x={position.left}
                y={position.top}
                width={position.width}
                height={position.height}
                rx="8"
                fill="black"
              />
            </mask>
          </defs>
          <rect
            x="0"
            y="0"
            width="100%"
            height="100%"
            fill="rgba(0, 0, 0, 0.7)"
            mask="url(#spotlight-mask)"
          />
        </svg>
      </div>

      {/* Spotlight ring */}
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="fixed z-[9999] border-2 border-emerald-400 rounded-lg pointer-events-none"
        style={{
          top: position.top,
          left: position.left,
          width: position.width,
          height: position.height,
          boxShadow: '0 0 0 4px rgba(16, 185, 129, 0.3)',
        }}
      />

      {/* Tooltip */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        className="fixed z-[10000] bg-white rounded-xl shadow-2xl p-5 w-80"
        style={{ top: tooltipPosition.top, left: tooltipPosition.left }}
      >
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm text-gray-500 font-medium">
            Step {step} of {totalSteps}
          </span>
          <button
            onClick={onSkip}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-gray-700 mb-4">{content}</p>

        <div className="flex items-center justify-between">
          <button
            onClick={onSkip}
            className="text-gray-500 hover:text-gray-700 text-sm flex items-center gap-1"
          >
            <SkipForward className="w-4 h-4" />
            Skip Tour
          </button>
          <div className="flex items-center gap-2">
            {step > 1 && (
              <button
                onClick={onPrev}
                className="px-3 py-1.5 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 flex items-center gap-1 text-sm"
              >
                <ChevronLeft className="w-4 h-4" />
                Back
              </button>
            )}
            <button
              onClick={onNext}
              className="px-4 py-1.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 flex items-center gap-1 text-sm"
            >
              {step === totalSteps ? 'Finish' : 'Next'}
              {step < totalSteps && <ChevronRight className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Progress dots */}
        <div className="flex items-center justify-center gap-1.5 mt-4">
          {Array.from({ length: totalSteps }).map((_, i) => (
            <div
              key={i}
              className={`w-2 h-2 rounded-full transition-colors ${
                i + 1 === step ? 'bg-emerald-500' : 'bg-gray-300'
              }`}
            />
          ))}
        </div>
      </motion.div>
    </>,
    document.body
  );
};

export default function DemoTour() {
  const { 
    isDemoMode, 
    currentTour, 
    tourSteps, 
    tourStepIndex, 
    setTourStepIndex,
    completeTour,
    skipTour 
  } = useDemo();

  if (!isDemoMode || !currentTour || tourSteps.length === 0) {
    return null;
  }

  const currentStep = tourSteps[tourStepIndex];

  const handleNext = () => {
    if (tourStepIndex < tourSteps.length - 1) {
      setTourStepIndex(tourStepIndex + 1);
    } else {
      completeTour(currentTour);
    }
  };

  const handlePrev = () => {
    if (tourStepIndex > 0) {
      setTourStepIndex(tourStepIndex - 1);
    }
  };

  return (
    <AnimatePresence>
      <Spotlight
        key={tourStepIndex}
        target={currentStep.target}
        content={currentStep.content}
        step={tourStepIndex + 1}
        totalSteps={tourSteps.length}
        onNext={handleNext}
        onPrev={handlePrev}
        onSkip={skipTour}
      />
    </AnimatePresence>
  );
}
