/**
 * speech-analysis-service.js — Client-side transcript observation scanning
 *
 * Checks Thai and English text for simple patterns (e.g. pronoun reversal,
 * echolalia signals, length) and reports descriptive indicators.
 * Safety: These are indicators/observations only, NOT diagnostic.
 */

export function analyzeTranscript(transcript, lang = 'th') {
  const isThai = lang === 'th' || lang.startsWith('th-');
  const cleanText = transcript.trim();
  
  let words = [];
  let uniqueWords = new Set();
  let echolaliaSignal = false;
  let pronounNote = false;
  
  if (!isThai) {
    // English Analysis
    words = cleanText.toLowerCase().split(/[\s,.\-!?]+/).filter(w => w.length > 0);
    words.forEach(w => uniqueWords.add(w));
    
    // Echolalia: detect 2+ identical 3+ word sequences
    if (words.length >= 6) {
      const phrases = [];
      for (let i = 0; i <= words.length - 3; i++) {
        phrases.push(words.slice(i, i + 3).join(' '));
      }
      const seen = new Set();
      for (const phrase of phrases) {
        if (seen.has(phrase)) {
          echolaliaSignal = true;
          break;
        }
        seen.add(phrase);
      }
    }
    
    // Pronoun confusion: scan for you, he, she, him, her, they, them
    const lowerText = cleanText.toLowerCase();
    if (/\b(you|he|she|him|her)\b/.test(lowerText)) {
      pronounNote = true;
    }
  } else {
    // Thai Analysis
    const thaiStopwords = ['และ', 'หรือ', 'แต่', 'ที่', 'ซึ่ง', 'อัน', 'ของ', 'ใน', 'เพื่อ', 'จะ', 'ได้', 'แล้ว', 'ก็', 'ครับ', 'ค่ะ', 'คะ', 'นะ', 'หนู', 'ผม', 'น้อง', 'แม่', 'พ่อ', 'มี', 'เป็น', 'อยู่', 'ไป', 'มา', 'กิน', 'เล่น', 'เอา', 'อยาก', 'ไม่', 'ใช่', 'คือ'];
    
    // Split by spaces first
    const parts = cleanText.split(/[\s,.\-!?]+/).filter(p => p.length > 0);
    
    let estimatedWords = [];
    parts.forEach(part => {
      let temp = part;
      thaiStopwords.forEach(word => {
        temp = temp.split(word).join(' ');
      });
      const segments = temp.split(/\s+/).filter(s => s.length > 1);
      
      // Re-add stopwords count
      thaiStopwords.forEach(word => {
        const count = part.split(word).length - 1;
        for (let i = 0; i < count; i++) {
          estimatedWords.push(word);
        }
      });
      estimatedWords.push(...segments);
    });
    
    words = estimatedWords;
    words.forEach(w => uniqueWords.add(w));
    
    // Echolalia: check for repeating exact substrings of length 8+ characters
    if (cleanText.length >= 16) {
      for (let i = 0; i <= cleanText.length - 8; i++) {
        const sub = cleanText.substring(i, i + 8);
        if (cleanText.indexOf(sub) !== cleanText.lastIndexOf(sub)) {
          echolaliaSignal = true;
          break;
        }
      }
    }
    
    // Pronoun confusion: check for เขา, คุณ, เธอ
    if (/(เขา|คุณ|เธอ)/.test(cleanText)) {
      pronounNote = true;
    }
  }

  // Utterance calculation: split by punctuation or lines
  const utterances = cleanText.split(/[.,!?\n\s]{2,}/).filter(u => u.trim().length > 0);
  const utteranceCount = utterances.length || 1;
  const avgWordsPerUtterance = words.length / utteranceCount;
  
  return {
    echolaliaSignal,
    pronounNote,
    avgWordsPerUtterance: parseFloat(avgWordsPerUtterance.toFixed(1)),
    uniqueWordCount: uniqueWords.size,
    rawTranscript: cleanText
  };
}
