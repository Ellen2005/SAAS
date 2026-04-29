/* eslint react-refresh/only-export-components: off */
import React, { createContext, useContext, useState, useEffect } from 'react'

const STORAGE_KEY = 'saas.language'

export const translations = {
  en: {
    // Nav
    nav_admin: 'Admin',
    nav_dashboard: 'Dashboard',
    nav_reports: 'Reports',
    nav_validation: 'Validation',
    nav_settings: 'Settings',
    nav_logout: 'Log Out',

    // Landing
    landing_title: 'Smart Automated Analytics System',
    landing_subtitle: 'Nightly AI-driven intelligence for department heads. Connect your data, get your briefings, and act before the coffee is cold.',
    landing_enter: 'Enter Platform',
    landing_feature1_title: 'AI-Driven Summaries',
    landing_feature1_desc: "Don't look at charts for hours. Our system writes a concise executive narrative of your previous 24 hours automatically.",
    landing_feature2_title: 'Anomaly Detection',
    landing_feature2_desc: 'Sudden dips or spikes? Our ML engine flags statistical outliers before they become major operational bottlenecks.',
    landing_feature3_title: 'Unified Data Sync',
    landing_feature3_desc: 'Connect PostgreSQL, MySQL, MongoDB or SQL Server. Local or hosted, we fetch and process your data on your schedule.',

    // Login
    login_title: 'Welcome to SAAS',
    login_subtitle: 'Enter your credentials to access the analytics dashboard.',
    signup_title: 'Create your Account',
    signup_subtitle: 'Sign up to start your automated analytics.',
    login_email: 'Email Address',
    login_password: 'Password',
    login_confirm_password: 'Confirm Password',
    login_name: 'Name',
    login_btn: 'Sign In',
    signup_btn: 'Sign Up',
    login_forgot: 'Forgot password?',
    login_no_account: "Don't have an account?",
    login_has_account: 'Already have an account?',
    login_processing: 'Processing...',
    login_reset_send: 'Send reset email',
    login_reset_sent: 'If the email exists, you will receive a reset link shortly.',

    // Language picker
    lang_choose: 'Choose your language',
    lang_en: 'English',
    lang_fr: 'Français',
    lang_continue: 'Continue',

    // Dashboard
    dashboard_title: 'Executive Summary',
    dashboard_last_report: 'Last report:',
    dashboard_no_report: 'No report generated yet.',
    dashboard_generate: 'Generate Report',
    dashboard_generating: 'Generating...',
    dashboard_report_history: 'Report History',
    dashboard_no_data_title: 'No report yet',
    dashboard_no_data_desc: 'Click Generate Report to run the full analytics pipeline.',
    dashboard_ai_narrative: 'AI Narrative',
    dashboard_forecast: '7-Day KPI Forecast',
    dashboard_forecast_desc: 'Predicted values for the next 7 days based on historical trends.',
    dashboard_anomalies: 'Critical Anomalies Detected',
    dashboard_sync_step1: 'Step 1/6: Deep Extraction...',
    dashboard_sync_step2: 'Step 2/6: Applying Semantic Mappings...',
    dashboard_sync_step3: 'Step 3/6: Running Quality Checks...',
    dashboard_sync_step4: 'Step 4/6: ML Pattern Matching...',
    dashboard_sync_step5: 'Step 5/6: Storing Results...',
    dashboard_sync_step6: 'Step 6/6: AI Strategic Writing...',
    dashboard_sync_email: 'Finalizing Briefings...',
    dashboard_sync_failed: 'Validation failed. Refreshing results...',

    // NLQ
    nlq_title: 'Ask Your Data',
    nlq_placeholder: 'e.g. Show me employees who have not completed their contributions this month',
    nlq_btn: 'Run Query',
    nlq_running: 'Running...',
    nlq_results: 'Query Results',
    nlq_generated_sql: 'Generated Query',
    nlq_no_results: 'No results returned.',
    nlq_error: 'Query Error',
    nlq_rows: 'rows',

    // Custom Report
    custom_report_title: 'Custom Report',
    custom_report_instruction: 'What should this report cover?',
    custom_report_instruction_placeholder: 'e.g. Give me a summary of all anomalies in the Sales department last week',
    custom_report_scope: 'Data Scope',
    custom_report_scope_mine: 'My Department',
    custom_report_scope_all: 'All Departments',
    custom_report_scope_specific: 'Specific Departments',
    custom_report_format: 'Report Format',
    custom_report_format_narrative: 'Narrative',
    custom_report_format_table: 'Table',
    custom_report_format_bullets: 'Bullet Points',
    custom_report_format_brief: 'Executive Brief',
    custom_report_format_detailed: 'Detailed',
    custom_report_date_from: 'From Date',
    custom_report_date_to: 'To Date',
    custom_report_generate: 'Generate Report',
    custom_report_generating: 'Generating...',
    custom_report_result: 'Generated Report',
    custom_report_save: 'Save to History',
    custom_report_saved: 'Saved!',

    // Reports History
    reports_title: 'Report History',
    reports_subtitle: 'All AI-generated reports. Click to read, edit the narrative, or resend to email recipients.',
    reports_refresh: 'Refresh',
    reports_no_reports: 'No reports yet',
    reports_no_reports_desc: 'Go to the Dashboard and click Generate Report to create your first report.',
    reports_edit: 'Edit',
    reports_send: 'Send',
    reports_sent: 'Sent!',
    reports_save: 'Save',
    reports_cancel: 'Cancel',
    reports_full_narrative: 'Full Report Narrative',

    // Settings
    settings_title: 'Department Settings',
    settings_connection: 'Source Connectivity',
    settings_connection_method: 'Connection Method',
    settings_direct: 'Direct Connection',
    settings_cloudflare: 'Cloudflare Tunnel',
    settings_ssh: 'SSH Tunnel',
    settings_docker: 'Docker behind VPN',
    settings_uri: 'Direct URI',
    settings_db_type: 'Database Type',
    settings_host: 'Host',
    settings_port: 'Port',
    settings_db_name: 'Database Name',
    settings_user: 'User',
    settings_password: 'Password',
    settings_test: 'Test Connection',
    settings_save_conn: 'Save Connection',
    settings_testing: 'Testing...',
    settings_conn_ok: 'Connection verified.',
    settings_conn_saved: 'Configuration saved.',
    settings_conn_error: 'Connection failed. Review the values and try again.',
    settings_semantic: 'Semantic Mapping',
    settings_template: 'Template:',
    settings_mappings_ok: 'Required mappings are complete.',
    settings_mappings_missing: 'Missing required mappings:',
    settings_local_col: 'Local Column',
    settings_map: 'Map',
    settings_update: 'Update',
    settings_ai: 'AI Narrative and Delivery',
    settings_ai_tone: 'AI Tone',
    settings_tone_insight: 'Insight-driven',
    settings_tone_formal: 'Formal',
    settings_sync_freq: 'Sync Frequency',
    settings_freq_daily: 'Daily',
    settings_freq_weekly: 'Weekly',
    settings_freq_monthly: 'Monthly',
    settings_freq_yearly: 'Yearly',
    settings_sync_time: 'Sync Time',
    settings_yearly_date: 'Yearly Date',
    settings_analysis_focus: 'Analysis Focus',
    settings_recipients: 'Email Recipients',
    settings_save_prefs: 'Save Preferences',
    settings_trigger_sync: 'Trigger Sync Now',
    settings_account: 'Account Management',
    settings_appearance: 'Appearance',
    settings_light: 'Light',
    settings_dark: 'Dark',
    settings_change_password: 'Change Password',
    settings_new_password: 'New Password',
    settings_confirm_password: 'Confirm Password',
    settings_update_password: 'Update Password',
    settings_delete_account: 'Delete Account',
    settings_delete_desc: 'Deletes your Supabase user and all governed data tied to your account.',
    settings_language: 'Language',

    // Validation
    validation_title: 'Validation History',
    validation_subtitle: 'Schema, null, and anomaly checks from your governed department syncs.',

    // Admin
    admin_overview: 'Overview',
    admin_departments: 'Departments',
    admin_semantic: 'Semantic Layer',
    admin_quality: 'Data Quality',
    admin_users: 'Users',
    admin_templates: 'Templates',

    // Onboarding
    onboarding_title: 'Welcome to SAAS!',
    onboarding_desc: 'Your account has been created. An admin will assign you to a department. You can already explore the dashboard.',
    onboarding_language: 'Select your preferred language:',
  },

  fr: {
    // Nav
    nav_admin: 'Admin',
    nav_dashboard: 'Tableau de bord',
    nav_reports: 'Rapports',
    nav_validation: 'Validation',
    nav_settings: 'Paramètres',
    nav_logout: 'Déconnexion',

    // Landing
    landing_title: 'Système Analytique Automatisé Intelligent',
    landing_subtitle: "Intelligence IA nocturne pour les responsables de département. Connectez vos données, recevez vos briefings et agissez avant que le café refroidisse.",
    landing_enter: 'Accéder à la plateforme',
    landing_feature1_title: 'Résumés pilotés par IA',
    landing_feature1_desc: "Ne passez pas des heures sur des graphiques. Notre système rédige automatiquement un résumé exécutif de vos dernières 24 heures.",
    landing_feature2_title: 'Détection d\'anomalies',
    landing_feature2_desc: 'Baisses ou pics soudains ? Notre moteur ML signale les valeurs aberrantes avant qu\'elles ne deviennent des problèmes opérationnels majeurs.',
    landing_feature3_title: 'Synchronisation unifiée',
    landing_feature3_desc: 'Connectez PostgreSQL, MySQL, MongoDB ou SQL Server. Local ou hébergé, nous récupérons et traitons vos données selon votre calendrier.',

    // Login
    login_title: 'Bienvenue sur SAAS',
    login_subtitle: 'Entrez vos identifiants pour accéder au tableau de bord analytique.',
    signup_title: 'Créer votre compte',
    signup_subtitle: 'Inscrivez-vous pour démarrer vos analyses automatisées.',
    login_email: 'Adresse e-mail',
    login_password: 'Mot de passe',
    login_confirm_password: 'Confirmer le mot de passe',
    login_name: 'Nom',
    login_btn: 'Se connecter',
    signup_btn: "S'inscrire",
    login_forgot: 'Mot de passe oublié ?',
    login_no_account: 'Pas encore de compte ?',
    login_has_account: 'Déjà un compte ?',
    login_processing: 'Traitement...',
    login_reset_send: 'Envoyer le lien de réinitialisation',
    login_reset_sent: 'Si l\'e-mail existe, vous recevrez un lien de réinitialisation.',

    // Language picker
    lang_choose: 'Choisissez votre langue',
    lang_en: 'English',
    lang_fr: 'Français',
    lang_continue: 'Continuer',

    // Dashboard
    dashboard_title: 'Résumé exécutif',
    dashboard_last_report: 'Dernier rapport :',
    dashboard_no_report: 'Aucun rapport généré.',
    dashboard_generate: 'Générer un rapport',
    dashboard_generating: 'Génération...',
    dashboard_report_history: 'Historique des rapports',
    dashboard_no_data_title: 'Aucun rapport',
    dashboard_no_data_desc: 'Cliquez sur Générer un rapport pour lancer le pipeline analytique complet.',
    dashboard_ai_narrative: 'Narration IA',
    dashboard_forecast: 'Prévision KPI sur 7 jours',
    dashboard_forecast_desc: 'Valeurs prédites pour les 7 prochains jours basées sur les tendances historiques.',
    dashboard_anomalies: 'Anomalies critiques détectées',
    dashboard_sync_step1: 'Étape 1/6 : Extraction...',
    dashboard_sync_step2: 'Étape 2/6 : Mappages sémantiques...',
    dashboard_sync_step3: 'Étape 3/6 : Contrôles qualité...',
    dashboard_sync_step4: 'Étape 4/6 : Analyse ML...',
    dashboard_sync_step5: 'Étape 5/6 : Stockage des résultats...',
    dashboard_sync_step6: 'Étape 6/6 : Rédaction IA...',
    dashboard_sync_email: 'Finalisation des briefings...',
    dashboard_sync_failed: 'Validation échouée. Actualisation...',

    // NLQ
    nlq_title: 'Interroger vos données',
    nlq_placeholder: 'ex. Montrez-moi les employés qui n\'ont pas complété leurs contributions ce mois-ci',
    nlq_btn: 'Exécuter',
    nlq_running: 'Exécution...',
    nlq_results: 'Résultats',
    nlq_generated_sql: 'Requête générée',
    nlq_no_results: 'Aucun résultat retourné.',
    nlq_error: 'Erreur de requête',
    nlq_rows: 'lignes',

    // Custom Report
    custom_report_title: 'Rapport personnalisé',
    custom_report_instruction: 'Que doit couvrir ce rapport ?',
    custom_report_instruction_placeholder: 'ex. Donnez-moi un résumé de toutes les anomalies du département Ventes la semaine dernière',
    custom_report_scope: 'Périmètre des données',
    custom_report_scope_mine: 'Mon département',
    custom_report_scope_all: 'Tous les départements',
    custom_report_scope_specific: 'Départements spécifiques',
    custom_report_format: 'Format du rapport',
    custom_report_format_narrative: 'Narratif',
    custom_report_format_table: 'Tableau',
    custom_report_format_bullets: 'Points clés',
    custom_report_format_brief: 'Résumé exécutif',
    custom_report_format_detailed: 'Détaillé',
    custom_report_date_from: 'Date de début',
    custom_report_date_to: 'Date de fin',
    custom_report_generate: 'Générer le rapport',
    custom_report_generating: 'Génération...',
    custom_report_result: 'Rapport généré',
    custom_report_save: 'Sauvegarder',
    custom_report_saved: 'Sauvegardé !',

    // Reports History
    reports_title: 'Historique des rapports',
    reports_subtitle: 'Tous les rapports générés par IA. Cliquez pour lire, modifier ou renvoyer.',
    reports_refresh: 'Actualiser',
    reports_no_reports: 'Aucun rapport',
    reports_no_reports_desc: 'Allez sur le tableau de bord et cliquez sur Générer un rapport.',
    reports_edit: 'Modifier',
    reports_send: 'Envoyer',
    reports_sent: 'Envoyé !',
    reports_save: 'Sauvegarder',
    reports_cancel: 'Annuler',
    reports_full_narrative: 'Rapport complet',

    // Settings
    settings_title: 'Paramètres du département',
    settings_connection: 'Connectivité source',
    settings_connection_method: 'Méthode de connexion',
    settings_direct: 'Connexion directe',
    settings_cloudflare: 'Tunnel Cloudflare',
    settings_ssh: 'Tunnel SSH',
    settings_docker: 'Docker derrière VPN',
    settings_uri: 'URI directe',
    settings_db_type: 'Type de base de données',
    settings_host: 'Hôte',
    settings_port: 'Port',
    settings_db_name: 'Nom de la base',
    settings_user: 'Utilisateur',
    settings_password: 'Mot de passe',
    settings_test: 'Tester la connexion',
    settings_save_conn: 'Sauvegarder la connexion',
    settings_testing: 'Test en cours...',
    settings_conn_ok: 'Connexion vérifiée.',
    settings_conn_saved: 'Configuration sauvegardée.',
    settings_conn_error: 'Connexion échouée. Vérifiez les valeurs.',
    settings_semantic: 'Mappage sémantique',
    settings_template: 'Modèle :',
    settings_mappings_ok: 'Les mappages requis sont complets.',
    settings_mappings_missing: 'Mappages requis manquants :',
    settings_local_col: 'Colonne locale',
    settings_map: 'Mapper',
    settings_update: 'Mettre à jour',
    settings_ai: 'Narration IA et livraison',
    settings_ai_tone: 'Ton IA',
    settings_tone_insight: 'Axé sur les insights',
    settings_tone_formal: 'Formel',
    settings_sync_freq: 'Fréquence de synchronisation',
    settings_freq_daily: 'Quotidien',
    settings_freq_weekly: 'Hebdomadaire',
    settings_freq_monthly: 'Mensuel',
    settings_freq_yearly: 'Annuel',
    settings_sync_time: 'Heure de synchronisation',
    settings_yearly_date: 'Date annuelle',
    settings_analysis_focus: 'Focus d\'analyse',
    settings_recipients: 'Destinataires e-mail',
    settings_save_prefs: 'Sauvegarder les préférences',
    settings_trigger_sync: 'Déclencher la synchronisation',
    settings_account: 'Gestion du compte',
    settings_appearance: 'Apparence',
    settings_light: 'Clair',
    settings_dark: 'Sombre',
    settings_change_password: 'Changer le mot de passe',
    settings_new_password: 'Nouveau mot de passe',
    settings_confirm_password: 'Confirmer le mot de passe',
    settings_update_password: 'Mettre à jour le mot de passe',
    settings_delete_account: 'Supprimer le compte',
    settings_delete_desc: 'Supprime votre utilisateur Supabase et toutes les données associées.',
    settings_language: 'Langue',

    // Validation
    validation_title: 'Historique de validation',
    validation_subtitle: 'Vérifications de schéma, nullité et anomalies de vos synchronisations.',

    // Admin
    admin_overview: 'Vue d\'ensemble',
    admin_departments: 'Départements',
    admin_semantic: 'Couche sémantique',
    admin_quality: 'Qualité des données',
    admin_users: 'Utilisateurs',
    admin_templates: 'Modèles',

    // Onboarding
    onboarding_title: 'Bienvenue sur SAAS !',
    onboarding_desc: 'Votre compte a été créé. Un administrateur vous assignera à un département. Vous pouvez déjà explorer le tableau de bord.',
    onboarding_language: 'Sélectionnez votre langue préférée :',
  },
}

const LangContext = createContext(null)

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(() => {
    try { return localStorage.getItem(STORAGE_KEY) || 'en' } catch { return 'en' }
  })

  const setLang = (l) => {
    setLangState(l)
    try { localStorage.setItem(STORAGE_KEY, l) } catch {}
  }

  const t = (key) => translations[lang]?.[key] ?? translations['en']?.[key] ?? key

  return <LangContext.Provider value={{ lang, setLang, t }}>{children}</LangContext.Provider>
}

export function useLang() {
  const ctx = useContext(LangContext)
  if (!ctx) throw new Error('useLang must be used within LangProvider')
  return ctx
}
