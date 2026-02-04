import React from 'react';
import Joyride, { STATUS, ACTIONS, EVENTS } from 'react-joyride';
import { useDemo } from '../../contexts/DemoContext';

const tourStyles = {
  options: {
    primaryColor: '#10b981',
    textColor: '#374151',
    backgroundColor: '#ffffff',
    arrowColor: '#ffffff',
    overlayColor: 'rgba(0, 0, 0, 0.5)',
    zIndex: 10000,
  },
  buttonNext: {
    backgroundColor: '#10b981',
    borderRadius: '8px',
    padding: '8px 16px',
  },
  buttonBack: {
    color: '#6b7280',
    marginRight: 10,
  },
  buttonSkip: {
    color: '#9ca3af',
  },
  tooltip: {
    borderRadius: '12px',
    padding: '20px',
  },
  tooltipContainer: {
    textAlign: 'left',
  },
  tooltipTitle: {
    fontSize: '18px',
    fontWeight: '600',
    marginBottom: '8px',
  },
  tooltipContent: {
    fontSize: '14px',
    lineHeight: '1.6',
  },
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

  const handleJoyrideCallback = (data) => {
    const { action, index, status, type } = data;

    if ([EVENTS.STEP_AFTER, EVENTS.TARGET_NOT_FOUND].includes(type)) {
      setTourStepIndex(index + (action === ACTIONS.PREV ? -1 : 1));
    }

    if ([STATUS.FINISHED].includes(status)) {
      completeTour(currentTour);
    }

    if ([STATUS.SKIPPED].includes(status) || action === ACTIONS.CLOSE) {
      skipTour();
    }
  };

  return (
    <Joyride
      steps={tourSteps}
      stepIndex={tourStepIndex}
      run={true}
      continuous
      showProgress
      showSkipButton
      scrollToFirstStep
      spotlightClicks
      disableOverlayClose
      callback={handleJoyrideCallback}
      styles={tourStyles}
      locale={{
        back: 'Back',
        close: 'Close',
        last: 'Finish',
        next: 'Next',
        skip: 'Skip Tour',
      }}
      floaterProps={{
        disableAnimation: false,
      }}
    />
  );
}
