import { useEffect, useRef, useState } from 'react';
import Icon from './ui/Icon';

function MessageComposer({ onSend, disabled = false, isSpeaking = false, onStopSpeaking }) {
    const [text, setText] = useState('');
    const textareaRef = useRef(null);

    const resizeTextarea = () => {
        const textarea = textareaRef.current;
        if (!textarea) return;
        textarea.style.height = '40px';
        const maxHeight = Math.min(window.innerHeight * 0.4, 300);
        textarea.style.height = `${Math.min(textarea.scrollHeight, maxHeight)}px`;
    };

    useEffect(() => {
        const textarea = textareaRef.current;
        if (!textarea) return;
        textarea.style.height = '40px';
        const maxHeight = Math.min(window.innerHeight * 0.4, 300);
        textarea.style.height = `${Math.min(textarea.scrollHeight, maxHeight)}px`;
    }, [text]);

    const [isListening, setIsListening] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [voiceError, setVoiceError] = useState('');
    const audioContextRef = useRef(null);
    const streamRef = useRef(null);
    const sourceRef = useRef(null);
    const processorRef = useRef(null);
    const audioChunksRef = useRef([]);

    const handleSubmit = (event) => {
        event.preventDefault();
        const message = text.trim();
        if (!message || disabled || isProcessing || isSpeaking) return;
        onSend(message);
        setText('');
        setVoiceError('');
    };

    const handleKeyDown = (event) => {
        if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
            event.preventDefault();
            const message = text.trim();
            if (message && !disabled && !isProcessing && !isSpeaking) {
                onSend(message);
                setText('');
            }
        }
    };

    const cleanupRecording = async () => {
        processorRef.current?.disconnect();
        sourceRef.current?.disconnect();
        streamRef.current?.getTracks().forEach((track) => track.stop());
        const audioContext = audioContextRef.current;
        processorRef.current = null;
        sourceRef.current = null;
        streamRef.current = null;
        audioContextRef.current = null;

        if (audioContext && audioContext.state !== 'closed') {
            await audioContext.close();
        }
    };

    const createWavBlob = (chunks, sampleRate) => {
        const sampleCount = chunks.reduce((total, chunk) => total + chunk.length, 0);
        if (sampleCount === 0) throw new Error('empty-audio');

        const samples = new Float32Array(sampleCount);
        let offset = 0;
        for (const chunk of chunks) {
            samples.set(chunk, offset);
            offset += chunk.length;
        }

        const bytesPerSample = 2;
        const dataSize = samples.length * bytesPerSample;
        const buffer = new ArrayBuffer(44 + dataSize);
        const view = new DataView(buffer);

        const writeString = (position, value) => {
            for (let i = 0; i < value.length; i += 1) {
                view.setUint8(position + i, value.charCodeAt(i));
            }
        };

        writeString(0, 'RIFF');
        view.setUint32(4, 36 + dataSize, true);
        writeString(8, 'WAVE');
        writeString(12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, 1, true);
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * bytesPerSample, true);
        view.setUint16(32, bytesPerSample, true);
        view.setUint16(34, 16, true);
        writeString(36, 'data');
        view.setUint32(40, dataSize, true);

        for (let i = 0; i < samples.length; i += 1) {
            const sample = Math.max(-1, Math.min(1, samples[i]));
            const value = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
            view.setInt16(44 + i * 2, value, true);
        }

        return new Blob([buffer], { type: 'audio/wav' });
    };

    const startRecording = async () => {
        if (!navigator.mediaDevices?.getUserMedia) {
            setVoiceError('Запись микрофона недоступна.');
            return;
        }

        try {
            setVoiceError('');
            audioChunksRef.current = [];

            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            streamRef.current = stream;

            const audioContext = new AudioContext();
            audioContextRef.current = audioContext;
            await audioContext.resume();

            const source = audioContext.createMediaStreamSource(stream);
            const processor = audioContext.createScriptProcessor(4096, 1, 1);

            sourceRef.current = source;
            processorRef.current = processor;

            processor.onaudioprocess = (event) => {
                audioChunksRef.current.push(
                    new Float32Array(event.inputBuffer.getChannelData(0))
                );
            };

            source.connect(processor);
            processor.connect(audioContext.destination);

            setIsListening(true);
        } catch (error) {
            await cleanupRecording();
            setVoiceError(
                error?.name === 'NotAllowedError'
                    ? 'Разреши доступ к микрофону.'
                    : 'Не удалось запустить запись. Проверь микрофон.'
            );
        }
    };

    const stopRecording = async () => {
        setIsListening(false);
        setIsProcessing(true);
        setVoiceError('');

        try {
            const audioContext = audioContextRef.current;
            if (!audioContext) throw new Error('recording-unavailable');

            const sampleRate = audioContext.sampleRate;
            const chunks = audioChunksRef.current;

            await cleanupRecording();
            audioChunksRef.current = [];

            const wavBlob = createWavBlob(chunks, sampleRate);
            const audioBuffer = await wavBlob.arrayBuffer();

            if (!window.voiceAPI?.transcribe) {
                throw new Error('voice-api-unavailable');
            }

            const result = await window.voiceAPI.transcribe(audioBuffer);
            if (result?.error) throw new Error(result.error);

            const recognizedText = typeof result === 'string' ? result : result?.text;
            if (!recognizedText?.trim()) throw new Error('empty-transcription');

            onSend(recognizedText.trim());

        } catch (error) {
            console.error('Voice input error:', error);
            if (error.message === 'voice-api-unavailable') {
                setVoiceError('Модуль голосового ввода ещё не подключён.');
            } else if (error.message === 'empty-audio') {
                setVoiceError('Запись пуста. Попробуй ещё раз.');
            } else if (error.message === 'empty-transcription') {
                setVoiceError('Не удалось распознать речь. Попробуй ещё раз.');
            } else {
                setVoiceError('Не удалось обработать аудио. Проверь подключение.');
            }
        } finally {
            await cleanupRecording();
            audioChunksRef.current = [];
            setIsProcessing(false);
        }
    };

    const handleVoiceInput = () => {

        if (isSpeaking) {
            onStopSpeaking();
            return;
        }
        if (isProcessing || disabled) return;
        if (isListening) {
            void stopRecording();
        } else {
            void startRecording();
        }
    };

    return (
        <form className="chat-composer" onSubmit={handleSubmit}>
            <textarea
                ref={textareaRef}
                className="chat-composer-input"
                value={text}
                onChange={(event) => setText(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Напиши сообщение..."
                aria-label="Текст сообщения"
                rows={1}
            />

            <div className="chat-composer-actions">
                <button
                    className={`chat-mic-button${isListening ? ' listening' : ''}`}
                    type="button"
                    onClick={handleVoiceInput}
                    disabled={disabled || isProcessing}
                    title={isSpeaking ? 'Остановить речь' : isListening ? 'Остановить запись' : 'Голосовой ввод'}
                >
                    {isSpeaking ? (
                        <div className="chat-stop-icon" />
                    ) : (
                        <Icon name="mic" size={20} />
                    )}
                </button>

                <button
                    className="chat-mic-button"
                    type="submit"
                    disabled={!text.trim() || disabled || isProcessing || isSpeaking}
                    title="Отправить"
                >
                    <Icon name="send" size={20} />
                </button>
            </div>

            {isProcessing && (
                <p className="chat-voice-error" role="status">
                    Распознавание речи...
                </p>
            )}

            {voiceError && (
                <p className="chat-voice-error" role="status">
                    {voiceError}
                </p>
            )}
        </form>
    );
}

export default MessageComposer;