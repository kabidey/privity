/**
 * TypewriterQuote Component
 * Displays animated typewriter effect for PE quotes
 */
import { useState, useEffect, useRef, useMemo } from 'react';
import { PE_QUOTES } from './constants';

const TypewriterQuote = ({ theme }) => {
  const [currentQuoteIndex, setCurrentQuoteIndex] = useState(0);
  const [displayedText, setDisplayedText] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [showCursor, setShowCursor] = useState(true);
  const typewriterRef = useRef(null);

  // Memoize quotes to avoid re-renders
  const allQuotes = useMemo(() => PE_QUOTES, []);

  // Cursor blink effect
  useEffect(() => {
    const cursorInterval = setInterval(() => setShowCursor(prev => !prev), 530);
    return () => clearInterval(cursorInterval);
  }, []);

  // Typewriter effect
  useEffect(() => {
    const currentQuote = allQuotes[currentQuoteIndex];
    const typeSpeed = isDeleting ? 30 : 50;
    
    typewriterRef.current = setTimeout(() => {
      if (!isDeleting) {
        if (displayedText.length < currentQuote.length) {
          setDisplayedText(currentQuote.slice(0, displayedText.length + 1));
        } else {
          setTimeout(() => setIsDeleting(true), 3000);
        }
      } else {
        if (displayedText.length > 0) {
          setDisplayedText(displayedText.slice(0, -1));
        } else {
          setIsDeleting(false);
          setCurrentQuoteIndex((prev) => (prev + 1) % allQuotes.length);
        }
      }
    }, typeSpeed);
    
    return () => clearTimeout(typewriterRef.current);
  }, [displayedText, isDeleting, currentQuoteIndex, allQuotes]);

  return (
    <div className="mb-8 text-center max-w-2xl px-4 animate-fade-in" style={{animationDelay: '0.2s'}}>
      <div className="min-h-[80px] flex items-center justify-center">
        <blockquote className="text-lg sm:text-xl md:text-2xl font-light text-white leading-relaxed" data-testid="quote">
          &ldquo;{displayedText}
          <span className={`inline-block w-0.5 h-5 sm:h-6 bg-${theme.primary}-400 ml-1 ${showCursor ? 'opacity-100' : 'opacity-0'}`}></span>&rdquo;
        </blockquote>
      </div>
      <cite className={`text-${theme.primary}-300 text-sm mt-3 block font-bold tracking-wide drop-shadow-sm`}>
        — SMIFS PE
      </cite>
    </div>
  );
};

export default TypewriterQuote;
