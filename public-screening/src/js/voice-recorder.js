/**
 * voice-recorder.js — Voice recording via Web Speech API
 *
 * Provides speech-to-text recording client-side.
 */

export class VoiceRecorder {
  constructor() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.recognition = SpeechRecognition ? new SpeechRecognition() : null;
    this.isRecording = false;
    this.transcript = '';
    this.startTime = null;
    this.duration = 0;
    this.resolvePromise = null;
    this.rejectPromise = null;
    this.onTranscriptUpdate = null;

    if (this.recognition) {
      this.recognition.continuous = true;
      this.recognition.interimResults = true;

      this.recognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }

        // Live preview update callback
        if (this.onTranscriptUpdate) {
          const currentTotal = (this.transcript + ' ' + finalTranscript + ' ' + interimTranscript).trim();
          this.onTranscriptUpdate(currentTotal);
        }

        if (finalTranscript) {
          this.transcript = (this.transcript + ' ' + finalTranscript).trim();
        }
      };

      this.recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        if (this.rejectPromise) {
          this.rejectPromise(event.error);
        }
      };

      this.recognition.onend = () => {
        this.isRecording = false;
        this.duration = this.startTime ? Math.round((Date.now() - this.startTime) / 1000) : 0;
        if (this.resolvePromise) {
          this.resolvePromise({
            transcript: this.transcript.trim(),
            duration: this.duration
          });
        }
      };
    }
  }

  isSupported() {
    return this.recognition !== null;
  }

  start(lang = 'th-TH') {
    if (!this.isSupported()) {
      return Promise.reject('SpeechRecognition is not supported on this browser.');
    }
    if (this.isRecording) {
      return Promise.resolve();
    }

    this.transcript = '';
    this.startTime = Date.now();
    this.isRecording = true;
    this.recognition.lang = lang;
    
    return new Promise((resolve, reject) => {
      try {
        this.recognition.start();
        resolve();
      } catch (err) {
        this.isRecording = false;
        reject(err);
      }
    });
  }

  stop() {
    if (!this.isSupported() || !this.isRecording) {
      return Promise.resolve({ transcript: '', duration: 0 });
    }

    return new Promise((resolve, reject) => {
      this.resolvePromise = resolve;
      this.rejectPromise = reject;
      this.recognition.stop();
    });
  }
}

/**
 * Helper to get user-friendly error messages based on SpeechRecognition error codes
 */
export function getVoiceErrorMessage(errorType, lang = 'th') {
  const messages = {
    'not-allowed': {
      en: 'Microphone permission blocked. Please check your browser privacy settings.',
      th: 'การเข้าถึงไมโครโฟนถูกปฏิเสธ กรุณาอนุญาตการเข้าถึงไมโครโฟนในการตั้งค่าเบราว์เซอร์'
    },
    'no-speech': {
      en: 'No speech was detected. Please try speaking closer to the microphone.',
      th: 'ไม่ตรวจพบเสียงพูด กรุณาลองพูดใกล้ไมโครโฟนให้มากขึ้น'
    },
    'audio-capture': {
      en: 'Microphone not found or not connected. Please verify your hardware.',
      th: 'ไม่พบหรือไม่ได้เชื่อมต่อไมโครโฟน กรุณาตรวจสอบฮาร์ดแวร์ของคุณ'
    },
    'network': {
      en: 'Network error occurred during speech recognition. An internet connection is required for Web Speech API on some browsers.',
      th: 'เกิดข้อผิดพลาดเครือข่ายระหว่างการรับรู้เสียงพูด (บางเบราว์เซอร์ต้องการการเชื่อมต่ออินเทอร์เน็ต)'
    },
    'default': {
      en: 'An error occurred during voice observation. Please try again.',
      th: 'เกิดข้อผิดพลาดระหว่างการรับข้อมูลเสียง กรุณาลองอีกครั้ง'
    }
  };
  
  const key = messages[errorType] ? errorType : 'default';
  return messages[key][lang] || messages[key]['en'];
}
