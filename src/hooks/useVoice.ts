import { useState, useCallback, useRef } from 'react';

export function useVoice(onResult: (text: string) => void) {
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [interimTranscript, setInterimTranscript] = useState('');
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  const startListening = useCallback((lang = 'en-IN') => {
    const SpeechRecognition =
      window.SpeechRecognition || (window as unknown as { webkitSpeechRecognition: typeof SpeechRecognition }).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setError('Speech recognition not supported in this browser.');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = lang;
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onstart = () => {
      setIsListening(true);
      setInterimTranscript('');
    };
    recognition.onend = () => {
      setIsListening(false);
      setInterimTranscript('');
    };
    recognition.onerror = (e) => {
      setIsListening(false);
      setInterimTranscript('');
      setError(e.error === 'not-allowed' ? 'Microphone access denied.' : `Error: ${e.error}`);
    };
    recognition.onresult = (e) => {
      let final = '';
      let interim = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) {
          final += e.results[i][0].transcript;
        } else {
          interim += e.results[i][0].transcript;
        }
      }
      if (final) onResult(final);
      setInterimTranscript(interim);
    };

    recognitionRef.current = recognition;
    recognition.start();
  }, [onResult]);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    setIsListening(false);
    setInterimTranscript('');
  }, []);

  return { isListening, error, startListening, stopListening, interimTranscript };
}
