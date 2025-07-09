/**
 * Example JavaScript code for using XTTS Network Streaming
 * This can be adapted for use in Chrome extensions or web applications
 */

class XTTSNetworkStreamer {
    constructor(serverUrl = 'http://localhost:8020') {
        this.serverUrl = serverUrl;
        this.audioContext = null;
        this.currentSource = null;
        this.audioQueue = [];
        this.isPlaying = false;
    }

    /**
     * Initialize Web Audio API
     */
    async initAudio() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        
        // Resume context if suspended (required by Chrome autoplay policy)
        if (this.audioContext.state === 'suspended') {
            await this.audioContext.resume();
        }
    }

    /**
     * Stream text-to-speech audio using the new network streaming endpoint
     * @param {string} text - Text to convert to speech
     * @param {string} speaker_wav - Speaker voice file name
     * @param {string} language - Language code (e.g., 'en', 'es', 'fr')
     */
    async streamTTS(text, speaker_wav = 'female.wav', language = 'en') {
        try {
            await this.initAudio();

            // Use the new POST endpoint for network streaming
            const response = await fetch(`${this.serverUrl}/tts_to_audio_stream/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text,
                    speaker_wav: speaker_wav,
                    language: language
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            // Process the streaming response
            const reader = response.body.getReader();
            let audioBuffer = new ArrayBuffer(0);

            while (true) {
                const { done, value } = await reader.read();
                
                if (done) {
                    console.log('Streaming completed');
                    break;
                }

                // Append new audio data to buffer
                audioBuffer = this.appendBuffer(audioBuffer, value.buffer);
                
                // Try to play audio chunks as they arrive
                await this.playAudioBuffer(audioBuffer);
            }

        } catch (error) {
            console.error('Error in TTS streaming:', error);
            throw error;
        }
    }

    /**
     * Alternative method using GET endpoint with query parameters
     */
    async streamTTSGet(text, speaker_wav = 'female.wav', language = 'en') {
        try {
            await this.initAudio();

            const params = new URLSearchParams({
                text: text,
                speaker_wav: speaker_wav,
                language: language
            });

            const response = await fetch(`${this.serverUrl}/tts_stream_realtime?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            // Create audio element for simpler playback
            const audio = new Audio();
            audio.src = URL.createObjectURL(await response.blob());
            
            return new Promise((resolve, reject) => {
                audio.onended = resolve;
                audio.onerror = reject;
                audio.play();
            });

        } catch (error) {
            console.error('Error in GET TTS streaming:', error);
            throw error;
        }
    }

    /**
     * Utility method to append array buffers
     */
    appendBuffer(buffer1, buffer2) {
        const combined = new ArrayBuffer(buffer1.byteLength + buffer2.byteLength);
        const view = new Uint8Array(combined);
        view.set(new Uint8Array(buffer1), 0);
        view.set(new Uint8Array(buffer2), buffer1.byteLength);
        return combined;
    }

    /**
     * Play audio buffer using Web Audio API
     */
    async playAudioBuffer(arrayBuffer) {
        try {
            // Only try to decode if we have enough data (basic WAV header + some audio)
            if (arrayBuffer.byteLength < 1024) return;

            const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer.slice());
            
            if (this.currentSource) {
                this.currentSource.stop();
            }

            const source = this.audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.audioContext.destination);
            source.start();
            
            this.currentSource = source;
            this.isPlaying = true;

            source.onended = () => {
                this.isPlaying = false;
                this.currentSource = null;
            };

        } catch (error) {
            // Ignore decoding errors for incomplete buffers
            if (!error.message.includes('decode')) {
                console.warn('Audio playback error:', error);
            }
        }
    }

    /**
     * Stop current audio playback
     */
    stop() {
        if (this.currentSource) {
            this.currentSource.stop();
            this.currentSource = null;
            this.isPlaying = false;
        }
    }
}

// Example usage for Chrome Extension
class ChromeExtensionTTS {
    constructor() {
        this.streamer = new XTTSNetworkStreamer('http://your-server-ip:8020');
    }

    /**
     * Read selected text aloud
     */
    async readSelectedText() {
        // Get selected text from page
        const selectedText = window.getSelection().toString().trim();
        
        if (!selectedText) {
            alert('Please select some text to read aloud');
            return;
        }

        try {
            console.log('Reading text:', selectedText);
            
            // Use network streaming - audio will play on client machine
            await this.streamer.streamTTS(selectedText, 'female.wav', 'en');
            
            console.log('Audio playback completed');
            
        } catch (error) {
            console.error('Failed to read text:', error);
            alert('Error: Unable to read text. Make sure the XTTS server is running.');
        }
    }

    /**
     * Alternative method with simpler audio handling
     */
    async readTextSimple(text) {
        try {
            // This method is simpler but may have higher latency
            await this.streamer.streamTTSGet(text, 'female.wav', 'en');
        } catch (error) {
            console.error('Simple TTS failed:', error);
            throw error;
        }
    }
}

// Usage example:
// const tts = new ChromeExtensionTTS();
// tts.readSelectedText();

// For testing in browser console:
// const streamer = new XTTSNetworkStreamer('http://localhost:8020');
// streamer.streamTTS('Hello, this is a test of network streaming!'); 