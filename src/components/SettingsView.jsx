
import { useTranslation } from 'react-i18next';
import '../styles/SettingsView.css';

function SettingsView({
    settings,
    onVoiceChange,
    onThemeChange,
    onLanguageChange,
}) {
    const { t } = useTranslation();

    return (
        <section className="workspace">
            <div className="chat-glass-panel settings-glass-panel">
                <header className="chat-header">
                    <div className="chat-header-info">
                        <h1>{t('settingsTitle')}</h1>
                    </div>
                </header>

                <div className="settings-content">
                    <section className="setting-item">
                        <div className="setting-copy">
                            <h2>{t('voicePlayback')}</h2>
                            <p>{t('voiceDescription')}</p>
                        </div>

                        <button
                            type="button"
                            className={`setting-switch ${settings.voiceEnabled ? 'enabled' : ''
                                }`}
                            role="switch"
                            aria-checked={settings.voiceEnabled}
                            onClick={() => onVoiceChange(!settings.voiceEnabled)}
                        >
                            <span />
                        </button>
                    </section>

                    <section className="setting-item">
                        <div className="setting-copy">
                            <h2>{t('theme')}</h2>
                            <p>{t('themeDescription')}</p>
                        </div>

                        <div className="setting-theme-control">
                            <button
                                type="button"
                                className={`theme-option ${settings.theme === 'dark' ? 'active' : ''
                                    }`}
                                onClick={() => onThemeChange('dark')}
                            >
                                {t('darkTheme')}
                            </button>

                            <button
                                type="button"
                                className="theme-option"
                                disabled
                                title={t('comingSoon')}
                            >
                                {t('lightTheme')}
                            </button>
                        </div>
                    </section>

                    <section className="setting-item">
                        <div className="setting-copy">
                            <h2>{t('language')}</h2>
                            <p>{t('languageDescription')}</p>
                        </div>

                        <div className="setting-theme-control">
                            <button
                                type="button"
                                className={`theme-option ${settings.language === 'ru' ? 'active' : ''
                                    }`}
                                onClick={() => onLanguageChange('ru')}
                            >
                                {t('russian')}
                            </button>

                            <button
                                type="button"
                                className={`theme-option ${settings.language === 'en' ? 'active' : ''
                                    }`}
                                onClick={() => onLanguageChange('en')}
                            >
                                {t('english')}
                            </button>
                        </div>
                    </section>
                </div>
            </div>
        </section>
    );
}

export default SettingsView;