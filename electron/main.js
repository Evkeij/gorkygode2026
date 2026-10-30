import { app, BrowserWindow, ipcMain, Notification, Tray, Menu, nativeImage } from 'electron';
import path from 'node:path';
import fs from 'node:fs';
import fsPromises from 'node:fs/promises';
import { spawn, exec } from 'node:child_process';
import { randomUUID } from 'node:crypto';

app.setAppUserModelId('ru.descvoice.app');

const getAppIconPath = () => {
    return app.isPackaged
        ? path.join(process.resourcesPath, 'icon.ico')
        : path.join(app.getAppPath(), 'public', 'icon.ico');
};

const iconPath = getAppIconPath();
const appIcon = nativeImage.createFromPath(iconPath);

const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
    app.quit();
} else {
    app.on('second-instance', () => {
        const windows = BrowserWindow.getAllWindows();
        if (windows.length > 0) {
            const mainWindow = windows[0];
            if (mainWindow.isMinimized()) mainWindow.restore();
            mainWindow.show();
            mainWindow.focus();
        }
    });
}

let pyProcess = null;
let isBackendStarted = false;
let tray = null;

const NOTIFIED_FILE = path.join(app.getPath('userData'), 'notified-events.json');
let notifiedEvents = new Set();

const isHidden = process.argv.includes('--hidden');

async function loadNotified() {
    try {
        const data = await fsPromises.readFile(NOTIFIED_FILE, 'utf8');
        const arr = JSON.parse(data);
        if (Array.isArray(arr)) {
            notifiedEvents = new Set(arr);
        }
    } catch {
        notifiedEvents = new Set();
    }
}

async function saveNotified() {
    try {
        await fsPromises.writeFile(NOTIFIED_FILE, JSON.stringify([...notifiedEvents]), 'utf8');
    } catch (e) {
        console.error('Не удалось сохранить notified-events:', e.message);
    }
}

const startPythonBackend = () => {
    if (isBackendStarted) return;
    isBackendStarted = true;

    const exePath = app.isPackaged
        ? path.join(process.resourcesPath, 'backend.exe')
        : path.join(app.getAppPath(), 'backend.exe');

    const logPath = path.join(app.getPath('userData'), 'backend-log.txt');
    console.log('--- Запуск бэкенда ---', exePath);
    console.log('Логи пишутся в:', logPath);

    try {
        const logStream = fs.createWriteStream(logPath, { flags: 'a' });
        logStream.write(`\n\n--- ЗАПУСК ${new Date().toISOString()} ---\n`);

        pyProcess = spawn(exePath, [], {
            windowsHide: true,
            stdio: ['ignore', 'pipe', 'pipe'],
        });

        if (pyProcess.stdout) pyProcess.stdout.pipe(logStream);
        if (pyProcess.stderr) pyProcess.stderr.pipe(logStream);

        pyProcess.on('error', (err) => {
            console.error('Ошибка запуска бэкенда:', err);
            logStream.write(`\n--- ОШИБКА ЗАПУСКА: ${err.message} ---\n`);
            isBackendStarted = false;
            pyProcess = null;
        });

        pyProcess.on('exit', (code) => {
            console.log('backend exited with code', code);
            logStream.write(`\n--- БЭКЕНД ЗАВЕРШИЛСЯ С КОДОМ ${code} ---\n`);
            logStream.end();
            isBackendStarted = false;
            pyProcess = null;
        });
    } catch (e) {
        console.error('Ошибка при создании процесса:', e);
        isBackendStarted = false;
    }
};

const stopPythonBackend = () => {
    if (pyProcess) {
        try {
            pyProcess.kill();
        } catch { }
        pyProcess = null;
    }
    isBackendStarted = false;
    exec('taskkill /F /IM backend.exe /T', { windowsHide: true }, () => { });
};

const checkNotifications = async () => {
    try {
        const res = await fetch('http://127.0.0.1:8000/events');
        if (!res.ok) return;

        const data = await res.json();
        if (!data.records) return;

        const now = new Date();
        let changed = false;

        for (const event of data.records) {
            if (event.is_completed || !event.date) continue;

            let eventDate;
            try {
                eventDate = new Date(event.date);
            } catch {
                continue;
            }

            const diffMs = eventDate - now;
            const diffMinutes = diffMs / (1000 * 60);
            const diffHours = diffMinutes / 60;
            const timeStr = eventDate.toLocaleString('ru-RU', {
                hour: '2-digit',
                minute: '2-digit',
            });

            const notifIcon = getAppIconPath();

            const key12h = `${event.id}-12h`;
            if (diffHours > 11.5 && diffHours <= 12.5 && !notifiedEvents.has(key12h)) {
                new Notification({ title: 'Напоминание', body: `${event.title} — в ${timeStr}`, icon: notifIcon }).show();
                notifiedEvents.add(key12h);
                changed = true;
            }

            const key2h = `${event.id}-2h`;
            if (diffHours > 1.5 && diffHours <= 2.5 && !notifiedEvents.has(key2h)) {
                new Notification({ title: 'Скоро событие', body: `${event.title} — в ${timeStr}`, icon: notifIcon }).show();
                notifiedEvents.add(key2h);
                changed = true;
            }

            const key15m = `${event.id}-15m`;
            if (diffMinutes > 12 && diffMinutes <= 18 && !notifiedEvents.has(key15m)) {
                new Notification({ title: 'Событие через 15 минут!', body: `${event.title} — в ${timeStr}`, icon: notifIcon }).show();
                notifiedEvents.add(key15m);
                changed = true;
            }
            const keynow = `${event.id}-now`;
            if (diffMinutes < 0 && diffMinutes > -5 && !notifiedEvents.has(keynow)) {
                new Notification({ title: 'Событие прямо сейчас!', body: `${event.title} — в ${timeStr}`, icon: notifIcon }).show();
                notifiedEvents.add(keynow);
                changed = true;
            }
        }

        if (changed) {
            await saveNotified();
        }
    } catch (error) {
    }
};

const createWindow = () => {
    const mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 900,
        minHeight: 600,
        title: 'DescVoice',
        icon: appIcon,
        show: false,
        webPreferences: {
            preload: path.join(app.getAppPath(), 'electron', 'preload.cjs'),
            contextIsolation: true,
            nodeIntegration: false,
            webSecurity: false,
        },
    });

    if (app.isPackaged) {
        mainWindow.loadFile(path.join(app.getAppPath(), 'dist', 'index.html'));
    } else {
        mainWindow.loadURL('http://localhost:5173');
    }

    mainWindow.once('ready-to-show', () => {
        if (!isHidden) {
            mainWindow.show();
        }
    });

    mainWindow.on('close', (event) => {
        if (!app.isQuitting) {
            event.preventDefault();
            mainWindow.hide();
        }
    });

    return mainWindow;
};

ipcMain.handle('voice:transcribe', async (_event, audioBuffer) => {
    let audioPath;
    try {
        if (!audioBuffer || audioBuffer.byteLength === 0) {
            throw new Error('Не получены аудиоданные.');
        }
        audioPath = path.join(app.getPath('temp'), `descvoice-${randomUUID()}.wav`);
        await fsPromises.writeFile(audioPath, Buffer.from(audioBuffer));

        const recognizerPath = app.isPackaged
            ? path.join(process.resourcesPath, 'recognize.exe')
            : path.join(app.getAppPath(), 'recognize.exe');


        const result = await new Promise((resolve, reject) => {
            const child = spawn(recognizerPath, [audioPath], {
                windowsHide: true,
                stdio: ['ignore', 'pipe', 'pipe'],
            });

            let stdout = '';
            let stderr = '';
            let settled = false;

            const timeout = setTimeout(() => {
                if (settled) return;

                settled = true;
                child.kill();

                reject(new Error('Превышено время ожидания распознавания речи.'));
            }, 20000);

            child.stdout.setEncoding('utf8');
            child.stderr.setEncoding('utf8');

            child.stdout.on('data', (data) => {
                stdout += data;
            });

            child.stderr.on('data', (data) => {
                stderr += data;
            });

            child.on('error', (error) => {
                if (settled) return;

                settled = true;
                clearTimeout(timeout);
                reject(new Error(`Ошибка запуска распознавания: ${error.message}`));
            });

            child.on('close', (code) => {
                if (settled) return;

                settled = true;
                clearTimeout(timeout);

                const jsonLine = stdout
                    .split(/\r?\n/)
                    .map((line) => line.trim())
                    .filter(Boolean)
                    .reverse()
                    .find((line) => {
                        try {
                            const parsed = JSON.parse(line);
                            return parsed && ('text' in parsed || 'error' in parsed);
                        } catch {
                            return false;
                        }
                    });

                if (jsonLine) {
                    const parsed = JSON.parse(jsonLine);

                    if (code === 0 && parsed.text) {
                        resolve(parsed);
                    } else {
                        reject(new Error(parsed.error || stderr.trim() || 'Не распознано'));
                    }

                    return;
                }

                reject(new Error(stderr.trim() || stdout.trim() || `Код ${code}`));
            });
        });


        return result;
    } catch (error) {
        return { text: '', error: error.message };
    } finally {
        if (audioPath) {
            await fsPromises.unlink(audioPath).catch(() => { });
        }
    }
});

ipcMain.handle('voice:speak', async (_event, text) => {
    try {
        const speakPath = app.isPackaged
            ? path.join(process.resourcesPath, 'speak.exe')
            : path.join(app.getAppPath(), 'speak.exe');

        console.log('--- Запуск speak.exe ---', speakPath);

        return new Promise((resolve) => {
            const child = spawn(speakPath, [text], { windowsHide: true });
            let stdout = '';
            let stderr = '';

            child.stdout.on('data', (data) => { stdout += data; });
            child.stderr.on('data', (data) => { stderr += data; });

            child.on('error', (error) => {
                console.error('Ошибка spawn speak.exe:', error);
                resolve({ success: false, error: error.message });
            });

            child.on('close', async (code) => {
                console.log('speak.exe завершился с кодом:', code);
                console.log('stdout:', stdout);
                if (stderr) console.log('stderr:', stderr);

                if (code === 0) {
                    const mp3Path = path.join(app.getPath('temp'), 'reply.mp3');
                    try {
                        const audioBuffer = await fsPromises.readFile(mp3Path);
                        resolve({ success: true, audio: audioBuffer });
                    } catch (err) {
                        resolve({ success: false, error: `Файл не найден: ${mp3Path}` });
                    }
                } else {
                    resolve({ success: false, error: `Ошибка speak.exe: ${stderr || stdout}` });
                }
            });
        });
    } catch (error) {
        return { success: false, error: error.message };
    }
});

app.whenReady().then(async () => {
    app.setLoginItemSettings({
        openAtLogin: true,
        args: ['--hidden'],
    });

    await loadNotified();

    if (gotTheLock) {
        startPythonBackend();
    }

    const mainWindow = createWindow();

    try {
        tray = new Tray(iconPath);
        const contextMenu = Menu.buildFromTemplate([
            {
                label: 'Открыть DescVoice',
                click: () => mainWindow.show(),
            },
            { type: 'separator' },
            {
                label: 'Выход',
                click: () => {
                    app.isQuitting = true;
                    app.quit();
                },
            },
        ]);
        tray.setToolTip('DescVoice');
        tray.setContextMenu(contextMenu);
        tray.on('click', () => mainWindow.show());
    } catch (e) {
        console.warn('Ошибка трея:', e.message);
    }

    setTimeout(() => {
        checkNotifications();
        setInterval(checkNotifications, 45000);
    }, 12000);

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
});

app.on('before-quit', () => {
    stopPythonBackend();
});