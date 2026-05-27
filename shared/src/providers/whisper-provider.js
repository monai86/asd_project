import { ASRProvider } from "./asr-provider.js";

export class WhisperProvider extends ASRProvider {
  async transcribeAudio(file, language = "en", speakerCount = null) {
    throw new Error("Whisper integration not yet implemented. Real audio pipeline is not run.");
  }
}
