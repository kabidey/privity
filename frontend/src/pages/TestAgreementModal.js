import UserAgreementModal from '../components/UserAgreementModal';

const TestAgreementModal = () => {
  const handleAccept = () => {
    console.log('Agreement accepted');
  };

  const handleDecline = () => {
    console.log('Agreement declined');
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-2xl font-bold mb-4 text-gray-800 dark:text-gray-200">Agreement Modal Test</h1>
        <p className="text-gray-600 dark:text-gray-400">The modal should be visible below:</p>
      </div>
      <UserAgreementModal 
        isOpen={true} 
        onAccept={handleAccept} 
        onDecline={handleDecline} 
      />
    </div>
  );
};

export default TestAgreementModal;
