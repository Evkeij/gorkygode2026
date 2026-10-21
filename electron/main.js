import { app, BrowserWindow, ipcMain } from 'electron';
import path from 'node:path';
import fs from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';

const createWindow = () => {
    const mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 900,
        minHeight: 600,
        title: 'DescVoice',
        webPreferences: {
            preload: path.join(
                app.getAppPath(),
                'electron',
                'preload.cjs'
            ),
            contextIsolation: true,
            nodeIntegration: false,
        },
    });

    if (app.isPackaged) {
        // В установленном приложении открываем собранный React-интерфейс.
        mainWindow.loadFile(
            path.join(app.getAppPath(), 'dist', 'index.html')
        );
    } else {
        // При разработке используем сервер Vite.
        mainWindow.loadURL('http://localhost:5173');
    }
};

ipcMain.handle('voice:transcribe', async (_event, audioBuffer) => {
    let audioPath;

    try {
        if (!audioBuffer || audioBuffer.byteLength === 0) {
            throw new Error('Не получены аудиоданные.');
        }

        // Временно сохраняем аудио в WAV.
        audioPath = path.join(
            app.getPath('temp'),
            `descvoice-${randomUUID()}.wav`
        );

        await fs.writeFile(audioPath, Buffer.from(audioBuffer));

        // В разработке exe лежит в dist-voice,
        // в установленной версии — в resources.
        const recognizerPath = app.isPackaged
            ? path.join(process.resourcesPath, 'recognize.exe')
            : path.join(
                app.getAppPath(),
                'dist-voice',
                'recognize.exe'
            );

        // Запускаем автономный компонент распознавания.
        const result = await new Promise((resolve, reject) => {
            const child = spawn(recognizerPath, [audioPath], {
                windowsHide: true,
            });

            let stdout = '';
            let stderr = '';

            child.stdout.setEncoding('utf8');
            child.stderr.setEncoding('utf8');

            child.stdout.on('data', (data) => {
                stdout += data;
            });

            child.stderr.on('data', (data) => {
                stderr += data;
            });

            child.on('error', (error) => {
                reject(
                    new Error(
                        `Не удалось запустить компонент распознавания: ${error.message}`
                    )
                );
            });

            child.on('close', (code) => {
                const outputLines = stdout
                    .split(/\r?\n/)
                    .map((line) => line.trim())
                    .filter(Boolean);

                const jsonLine = [...outputLines]
                    .reverse()
                    .find((line) => {
                        try {
                            const parsed = JSON.parse(line);

                            return (
                                typeof parsed === 'object' &&
                                parsed !== null &&
                                ('text' in parsed || 'error' in parsed)
                            );
                        } catch {
                            return false;
                        }
                    });

                if (jsonLine) {
                    const parsed = JSON.parse(jsonLine);

                    if (code === 0 && parsed.text) {
                        resolve(parsed);
                    } else {
                        reject(
                            new Error(
                                parsed.error ||
                                stderr.trim() ||
                                'Не удалось распознать речь.'
                            )
                        );
                    }

                    return;
                }

                reject(
                    new Error(
                        stderr.trim() ||
                        stdout.trim() ||
                        `Компонент распознавания завершился с кодом ${code}.`
                    )
                );
            });
        });

        return result;
    } catch (error) {
        console.error('Voice transcription error:', error);

        return {
            text: '',
            error: error.message || 'Не удалось обработать аудио.',
        };
    } finally {
        if (audioPath) {
            await fs.unlink(audioPath).catch(() => { });
        }
    }
});

app.whenReady().then(() => {
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});