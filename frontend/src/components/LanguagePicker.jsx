import React from 'react'
import { useLang } from '../lib/i18n'

export default function LanguagePicker({ onClose }) {
  const { lang, setLang, t } = useLang()

  const choose = (l) => {
    setLang(l)
    if (onClose) onClose()
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
      display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 9999,
    }}>
      <div className="glass-panel" style={{ maxWidth: '360px', width: '92%', textAlign: 'center', padding: '40px 32px' }}>
        <div style={{ fontSize: '2rem', marginBottom: '16px' }}>🌐</div>
        <h2 style={{ marginBottom: '8px' }}>{t('lang_choose')}</h2>
        <p style={{ marginBottom: '28px', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          {t('onboarding_language')}
        </p>
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
          <button
            className="btn btn-outline"
            onClick={() => choose('en')}
            style={{
              flex: 1, padding: '14px',
              borderColor: lang === 'en' ? 'var(--primary-color)' : undefined,
              color: lang === 'en' ? 'var(--primary-color)' : undefined,
              fontWeight: lang === 'en' ? 700 : 500,
            }}
          >
            🇬🇧 {t('lang_en')}
          </button>
          <button
            className="btn btn-outline"
            onClick={() => choose('fr')}
            style={{
              flex: 1, padding: '14px',
              borderColor: lang === 'fr' ? 'var(--primary-color)' : undefined,
              color: lang === 'fr' ? 'var(--primary-color)' : undefined,
              fontWeight: lang === 'fr' ? 700 : 500,
            }}
          >
            🇫🇷 {t('lang_fr')}
          </button>
        </div>
        {onClose && (
          <button className="btn btn-primary" onClick={onClose} style={{ marginTop: '20px', width: '100%' }}>
            {t('lang_continue')}
          </button>
        )}
      </div>
    </div>
  )
}
