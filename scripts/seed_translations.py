#!/usr/bin/env python3
"""Seed canonical translations into all PO files.

This script is idempotent: it only writes a translation when the matching
msgstr is currently empty, so it never overwrites work a human translator has
already done. Add or refine entries in TRANSLATIONS below and re-run.

Usage:
    python scripts/seed_translations.py
"""

from __future__ import annotations

from pathlib import Path

import babel.messages.pofile as pofile

ROOT = Path(__file__).resolve().parent.parent
PO_DIR = ROOT / "app" / "translations"

# Master dict — { msgid : { lang : translation } }.
# Only include strings worth localising; the rest can stay English (fine for
# a side-project at v1.0).
TRANSLATIONS: dict[str, dict[str, str]] = {
    # --- Navbar & footer ---
    "Create": {"nl": "Aanmaken", "fr": "Créer", "de": "Erstellen", "es": "Crear", "it": "Crea"},
    "Start": {"nl": "Start", "fr": "Démarrer", "de": "Start", "es": "Empezar", "it": "Inizia"},
    "Off": {"nl": "Uit", "fr": "Désactivé", "de": "Aus", "es": "Desactivado", "it": "Disattivato"},
    "Two-factor authentication is not enabled": {
        "nl": "Tweestapsverificatie is niet ingeschakeld",
        "fr": "L'authentification à deux facteurs n'est pas activée",
        "de": "Zwei-Faktor-Authentifizierung ist nicht aktiviert",
        "es": "La autenticación en dos factores no está activada",
        "it": "L'autenticazione a due fattori non è attiva",
    },
    "Two-factor authentication": {
        "nl": "Tweestapsverificatie",
        "fr": "Authentification à deux facteurs",
        "de": "Zwei-Faktor-Authentifizierung",
        "es": "Autenticación en dos factores",
        "it": "Autenticazione a due fattori",
    },
    "Change password": {"nl": "Wachtwoord wijzigen", "fr": "Changer le mot de passe", "de": "Passwort ändern", "es": "Cambiar contraseña", "it": "Cambia password"},
    "About": {"nl": "Over", "fr": "À propos", "de": "Über", "es": "Acerca de", "it": "Informazioni"},
    "API": {"nl": "API", "fr": "API", "de": "API", "es": "API", "it": "API"},
    "Language": {"nl": "Taal", "fr": "Langue", "de": "Sprache", "es": "Idioma", "it": "Lingua"},
    "Toggle theme": {"nl": "Thema wisselen", "fr": "Changer de thème", "de": "Thema wechseln", "es": "Cambiar tema", "it": "Cambia tema"},
    "Account": {"nl": "Account", "fr": "Compte", "de": "Konto", "es": "Cuenta", "it": "Account"},
    "Admin": {"nl": "Beheer", "fr": "Admin", "de": "Admin", "es": "Admin", "it": "Admin"},
    "Sign in": {"nl": "Inloggen", "fr": "Se connecter", "de": "Anmelden", "es": "Iniciar sesión", "it": "Accedi"},
    "Sign up": {"nl": "Registreren", "fr": "S'inscrire", "de": "Registrieren", "es": "Registrarse", "it": "Registrati"},
    "Sign out": {"nl": "Uitloggen", "fr": "Se déconnecter", "de": "Abmelden", "es": "Cerrar sesión", "it": "Esci"},
    "Send feedback": {"nl": "Feedback sturen", "fr": "Envoyer un retour", "de": "Feedback senden", "es": "Enviar comentarios", "it": "Invia feedback"},
    # "Buy me a coffee" and "Support development" are intentionally NOT
    # translated — "Buy me a coffee" is the registered product name and
    # should appear verbatim across languages.
    "Privacy": {"nl": "Privacy", "fr": "Confidentialité", "de": "Datenschutz", "es": "Privacidad", "it": "Privacy"},
    "Cookies": {"nl": "Cookies", "fr": "Cookies", "de": "Cookies", "es": "Cookies", "it": "Cookie"},
    "Security": {"nl": "Beveiliging", "fr": "Sécurité", "de": "Sicherheit", "es": "Seguridad", "it": "Sicurezza"},
    "Learn more": {"nl": "Meer informatie", "fr": "En savoir plus", "de": "Mehr erfahren", "es": "Más información", "it": "Scopri di più"},
    "OK": {"nl": "OK", "fr": "OK", "de": "OK", "es": "OK", "it": "OK"},
    "We use only essential cookies (session, CSRF, language). No tracking.": {
        "nl": "We gebruiken alleen essentiële cookies (sessie, CSRF, taal). Geen tracking.",
        "fr": "Nous n'utilisons que des cookies essentiels (session, CSRF, langue). Aucun suivi.",
        "de": "Wir verwenden nur essenzielle Cookies (Session, CSRF, Sprache). Kein Tracking.",
        "es": "Usamos solo cookies esenciales (sesión, CSRF, idioma). Sin seguimiento.",
        "it": "Usiamo solo cookie essenziali (sessione, CSRF, lingua). Nessun tracciamento.",
    },

    # --- Homepage / composer ---
    "Share secrets safely": {"nl": "Veilig delen", "fr": "Partage sécurisé", "de": "Sicher teilen", "es": "Compartir de forma segura", "it": "Condivisione sicura"},
    "Secure message sharing": {"nl": "Veilig berichten delen", "fr": "Partage de messages sécurisé", "de": "Sicheres Teilen von Nachrichten", "es": "Compartir mensajes de forma segura", "it": "Condivisione sicura di messaggi"},
    "Share a secret. Once. Safely.": {"nl": "Veilig delen.", "fr": "Partage sécurisé.", "de": "Sicher teilen.", "es": "Compartir de forma segura.", "it": "Condivisione sicura."},
    "Share securely.": {"nl": "Veilig delen.", "fr": "Partage sécurisé.", "de": "Sicher teilen.", "es": "Compartir de forma segura.", "it": "Condivisione sicura."},
    "%(name)s is an open-source, self-hostable tool for sharing secrets one-time and securely. Messages are encrypted in your browser before they leave your device — the server cannot read them, and neither can the operator.": {
        "nl": "%(name)s is een open-source, zelf te hosten tool om gevoelige informatie eenmalig en veilig te delen. Berichten worden in je browser versleuteld voordat ze je apparaat verlaten — de server kan ze niet lezen, de beheerder ook niet.",
        "fr": "%(name)s est un outil open-source et auto-hébergeable pour partager des informations sensibles une seule fois et en toute sécurité. Les messages sont chiffrés dans votre navigateur avant de quitter votre appareil — le serveur ne peut pas les lire, et l'opérateur non plus.",
        "de": "%(name)s ist ein quelloffenes, selbst hostbares Tool, um sensible Informationen einmalig und sicher zu teilen. Nachrichten werden in deinem Browser verschlüsselt, bevor sie dein Gerät verlassen — der Server kann sie nicht lesen, und der Betreiber auch nicht.",
        "es": "%(name)s es una herramienta de código abierto y autoalojable para compartir información sensible una sola vez y de forma segura. Los mensajes se cifran en tu navegador antes de salir de tu dispositivo — el servidor no puede leerlos, ni tampoco el operador.",
        "it": "%(name)s è uno strumento open-source e self-hostable per condividere informazioni sensibili una sola volta e in modo sicuro. I messaggi vengono crittografati nel tuo browser prima di lasciare il tuo dispositivo — il server non può leggerli, e nemmeno l'operatore.",
    },
    "Send sensitive information, encrypted.": {
        "nl": "Verstuur gevoelige informatie versleuteld.",
        "fr": "Envoyez des informations sensibles, chiffrées.",
        "de": "Sende sensible Informationen, verschlüsselt.",
        "es": "Envía información sensible, cifrada.",
        "it": "Invia informazioni sensibili, crittografate.",
    },
    "Zero-knowledge encryption": {"nl": "Zero-knowledge encryptie", "fr": "Chiffrement à divulgation nulle", "de": "Zero-Knowledge-Verschlüsselung", "es": "Cifrado de conocimiento cero", "it": "Crittografia zero-knowledge"},
    "End-to-end encrypted": {"nl": "End-to-end versleuteld", "fr": "Chiffré de bout en bout", "de": "Ende-zu-Ende verschlüsselt", "es": "Cifrado de extremo a extremo", "it": "Crittografato end-to-end"},
    "End-to-end encrypted · Zero-knowledge": {"nl": "End-to-end versleuteld · Zero-knowledge", "fr": "Chiffrement de bout en bout · Zero-knowledge", "de": "Ende-zu-Ende verschlüsselt · Zero-Knowledge", "es": "Cifrado de extremo a extremo · Zero-knowledge", "it": "Crittografato end-to-end · Zero-knowledge"},
    "End-to-end encrypted in your browser. Only readable with the unique link and verification code.": {
        "nl": "End-to-end versleuteld in je browser. Alleen leesbaar met de unieke link en verificatiecode.",
        "fr": "Chiffré de bout en bout dans votre navigateur. Lisible uniquement avec le lien unique et le code de vérification.",
        "de": "Ende-zu-Ende verschlüsselt in deinem Browser. Nur mit dem einzigartigen Link und Verifizierungscode lesbar.",
        "es": "Cifrado de extremo a extremo en tu navegador. Solo legible con el enlace único y el código de verificación.",
        "it": "Crittografato end-to-end nel tuo browser. Leggibile solo con il link univoco e il codice di verifica.",
    },
    "Type or paste here — a password, a recovery phrase, or anything sensitive.": {
        "nl": "Typ of plak hier — een wachtwoord, recovery phrase of andere gevoelige informatie.",
        "fr": "Tapez ou collez ici — un mot de passe, une phrase de récupération ou toute information sensible.",
        "de": "Tippe oder füge hier ein — ein Passwort, eine Recovery-Phrase oder andere sensible Informationen.",
        "es": "Escribe o pega aquí — una contraseña, una frase de recuperación o información sensible.",
        "it": "Digita o incolla qui — una password, una recovery phrase o qualsiasi informazione sensibile.",
    },
    "characters": {"nl": "karakters", "fr": "caractères", "de": "Zeichen", "es": "caracteres", "it": "caratteri"},
    "%(used)s / %(total)s characters": {
        "nl": "%(used)s / %(total)s karakters",
        "fr": "%(used)s / %(total)s caractères",
        "de": "%(used)s / %(total)s Zeichen",
        "es": "%(used)s / %(total)s caracteres",
        "it": "%(used)s / %(total)s caratteri",
    },
    "Markdown is supported — formatting is auto-detected.": {
        "nl": "Markdown wordt ondersteund — opmaak wordt automatisch herkend.",
        "fr": "Le Markdown est pris en charge — la mise en forme est détectée automatiquement.",
        "de": "Markdown wird unterstützt — Formatierung wird automatisch erkannt.",
        "es": "Markdown es compatible — el formato se detecta automáticamente.",
        "it": "Markdown è supportato — la formattazione viene rilevata automaticamente.",
    },
    "Encrypted in your browser before sending": {
        "nl": "Versleuteld in je browser voordat het verzonden wordt",
        "fr": "Chiffré dans votre navigateur avant l'envoi",
        "de": "Im Browser verschlüsselt, bevor es gesendet wird",
        "es": "Cifrado en tu navegador antes de enviarlo",
        "it": "Crittografato nel tuo browser prima dell'invio",
    },
    "Leave empty to generate a 6-digit verification code. Otherwise a code is sent to the recipient (more secure).": {
        "nl": "Laat leeg om een willekeurige verificatiecode te genereren. Vul een e-mailadres in om de ontvanger de code per e-mail te laten ontvangen.",
        "fr": "Laissez vide pour générer un code de vérification aléatoire. Saisissez une adresse e-mail pour que le destinataire reçoive le code par e-mail.",
        "de": "Leer lassen, um einen zufälligen Verifizierungscode zu erzeugen. Gib eine E-Mail-Adresse ein, damit der Empfänger den Code per E-Mail erhält.",
        "es": "Déjalo vacío para generar un código de verificación aleatorio. Introduce una dirección de correo para que el destinatario reciba el código por e-mail.",
        "it": "Lascia vuoto per generare un codice di verifica casuale. Inserisci un indirizzo e-mail per far ricevere al destinatario il codice via e-mail.",
    },
    "Leave empty to generate a random verification code. Enter an e-mail address to have the code sent to the recipient by e-mail.": {
        "nl": "Laat leeg om een willekeurige verificatiecode te genereren. Vul een e-mailadres in om de ontvanger de code per e-mail te laten ontvangen.",
        "fr": "Laissez vide pour générer un code de vérification aléatoire. Saisissez une adresse e-mail pour que le destinataire reçoive le code par e-mail.",
        "de": "Leer lassen, um einen zufälligen Verifizierungscode zu erzeugen. Gib eine E-Mail-Adresse ein, damit der Empfänger den Code per E-Mail erhält.",
        "es": "Déjalo vacío para generar un código de verificación aleatorio. Introduce una dirección de correo para que el destinatario reciba el código por e-mail.",
        "it": "Lascia vuoto per generare un codice di verifica casuale. Inserisci un indirizzo e-mail per far ricevere al destinatario il codice via e-mail.",
    },
    "Up to %(n)d files · max %(s)s MB each · %(t)s MB total": {
        "nl": "Maximaal %(n)d bestanden · max %(s)s MB per bestand · %(t)s MB totaal",
        "fr": "Jusqu'à %(n)d fichiers · max %(s)s Mo par fichier · %(t)s Mo au total",
        "de": "Bis zu %(n)d Dateien · max. %(s)s MB pro Datei · %(t)s MB insgesamt",
        "es": "Hasta %(n)d archivos · máx. %(s)s MB por archivo · %(t)s MB en total",
        "it": "Fino a %(n)d file · max %(s)s MB per file · %(t)s MB totali",
    },
    "Attachments": {"nl": "Bijlagen", "fr": "Pièces jointes", "de": "Anhänge", "es": "Adjuntos", "it": "Allegati"},
    "We only show this once — copy it now and share it with your recipient.": {
        "nl": "We tonen dit slechts één keer — kopieer het nu en deel het met je ontvanger.",
        "fr": "Nous ne l'affichons qu'une fois — copiez-le maintenant et partagez-le avec votre destinataire.",
        "de": "Wir zeigen das nur einmal — kopiere es jetzt und teile es mit dem Empfänger.",
        "es": "Solo lo mostramos una vez — cópialo ahora y compártelo con el destinatario.",
        "it": "Lo mostriamo solo una volta — copialo ora e condividilo con il destinatario.",
    },
    "Share the link via e-mail and the verification code via a separate channel — chat, SMS or in person. That's the safest split.": {
        "nl": "Deel de link via e-mail en de verificatiecode via een apart kanaal — chat, SMS of in persoon. Dat is de veiligste verdeling.",
        "fr": "Partagez le lien par e-mail et le code de vérification par un canal séparé — chat, SMS ou en personne. C'est la répartition la plus sûre.",
        "de": "Teile den Link per E-Mail und den Verifizierungscode über einen separaten Kanal — Chat, SMS oder persönlich. Das ist die sicherste Aufteilung.",
        "es": "Comparte el enlace por correo y el código de verificación por un canal aparte — chat, SMS o en persona. Es la forma más segura.",
        "it": "Condividi il link via e-mail e il codice di verifica tramite un canale separato — chat, SMS o di persona. È la divisione più sicura.",
    },
    "Share the link via one channel and the verification code via another — chat, SMS or in person. That's the safest split.": {
        "nl": "Deel de link via één kanaal en de verificatiecode via een ander — chat, SMS of in persoon. Dat is de veiligste verdeling.",
        "fr": "Partagez le lien par un canal et le code de vérification par un autre — chat, SMS ou en personne. C'est la répartition la plus sûre.",
        "de": "Teile den Link über einen Kanal und den Verifizierungscode über einen anderen — Chat, SMS oder persönlich. Das ist die sicherste Aufteilung.",
        "es": "Comparte el enlace por un canal y el código de verificación por otro — chat, SMS o en persona. Es la forma más segura.",
        "it": "Condividi il link tramite un canale e il codice di verifica tramite un altro — chat, SMS o di persona. È la divisione più sicura.",
    },
    "The verification code has been sent to the recipient by e-mail. Share only the link with them.": {
        "nl": "De verificatiecode wordt per e-mail naar de ontvanger gestuurd. Deel alleen de link met ze.",
        "fr": "Le code de vérification sera envoyé au destinataire par e-mail. Ne partagez que le lien avec lui.",
        "de": "Der Verifizierungscode wird per E-Mail an den Empfänger gesendet. Teile nur den Link mit ihm.",
        "es": "El código de verificación se enviará al destinatario por correo. Comparte solo el enlace con él.",
        "it": "Il codice di verifica verrà inviato al destinatario via e-mail. Condividi solo il link con lui.",
    },
    "The verification code will be sent to the recipient by e-mail. Share only the link with them.": {
        "nl": "De verificatiecode wordt per e-mail naar de ontvanger gestuurd. Deel alleen de link met ze.",
        "fr": "Le code de vérification sera envoyé au destinataire par e-mail. Ne partagez que le lien avec lui.",
        "de": "Der Verifizierungscode wird per E-Mail an den Empfänger gesendet. Teile nur den Link mit ihm.",
        "es": "El código de verificación se enviará al destinatario por correo. Comparte solo el enlace con él.",
        "it": "Il codice di verifica verrà inviato al destinatario via e-mail. Condividi solo il link con lui.",
    },
    "End-to-end encrypted in your browser. Nobody — not even us — can read the message without your link and verification code.": {
        "nl": "End-to-end versleuteld in je browser. Niemand — ook wij niet — kan het bericht lezen zonder jouw link en verificatiecode.",
        "fr": "Chiffré de bout en bout dans votre navigateur. Personne — pas même nous — ne peut lire le message sans votre lien et votre code de vérification.",
        "de": "Ende-zu-Ende verschlüsselt in deinem Browser. Niemand — auch wir nicht — kann die Nachricht ohne deinen Link und Verifizierungscode lesen.",
        "es": "Cifrado de extremo a extremo en tu navegador. Nadie — ni siquiera nosotros — puede leer el mensaje sin tu enlace y código de verificación.",
        "it": "Crittografia end-to-end nel tuo browser. Nessuno — nemmeno noi — può leggere il messaggio senza il tuo link e codice di verifica.",
    },
    "Editor": {"nl": "Editor", "fr": "Éditeur", "de": "Editor", "es": "Editor", "it": "Editor"},
    "Preview": {"nl": "Voorbeeld", "fr": "Aperçu", "de": "Vorschau", "es": "Vista previa", "it": "Anteprima"},
    "Message": {"nl": "Bericht", "fr": "Message", "de": "Nachricht", "es": "Mensaje", "it": "Messaggio"},
    "Your secret message…": {"nl": "Je bericht…", "fr": "Votre message…", "de": "Deine Nachricht…", "es": "Tu mensaje…", "it": "Il tuo messaggio…"},
    "Render as Markdown when opened": {"nl": "Renderen als Markdown bij openen", "fr": "Afficher en Markdown à l'ouverture", "de": "Beim Öffnen als Markdown rendern", "es": "Mostrar como Markdown al abrir", "it": "Mostra come Markdown all'apertura"},
    "Expires after": {"nl": "Verloopt na", "fr": "Expire après", "de": "Läuft ab nach", "es": "Caduca después de", "it": "Scade dopo"},
    "hour": {"nl": "uur", "fr": "heure", "de": "Stunde", "es": "hora", "it": "ora"},
    "hours": {"nl": "uur", "fr": "heures", "de": "Stunden", "es": "horas", "it": "ore"},
    "days": {"nl": "dagen", "fr": "jours", "de": "Tage", "es": "días", "it": "giorni"},
    "max": {"nl": "max", "fr": "max", "de": "max", "es": "máx", "it": "max"},
    "Max opens": {"nl": "Max aantal keer openen", "fr": "Ouvertures max", "de": "Max. Öffnungen", "es": "Aperturas máx.", "it": "Aperture max"},
    "view (burn after reading)": {"nl": "keer (verbranden na lezen)", "fr": "vue (détruire après lecture)", "de": "Ansicht (nach Lesen löschen)", "es": "vista (destruir tras leer)", "it": "visualizzazione (distruggi dopo lettura)"},
    "views": {"nl": "keer", "fr": "vues", "de": "Ansichten", "es": "vistas", "it": "visualizzazioni"},
    "Unlimited (until expiry)": {"nl": "Onbeperkt (tot verloop)", "fr": "Illimité (jusqu'à expiration)", "de": "Unbegrenzt (bis Ablauf)", "es": "Sin límite (hasta caducidad)", "it": "Illimitato (fino alla scadenza)"},
    "Allowed recipients (e-mail, optional)": {"nl": "Toegestane ontvangers (e-mail, optioneel)", "fr": "Destinataires autorisés (e-mail, optionnel)", "de": "Erlaubte Empfänger (E-Mail, optional)", "es": "Destinatarios permitidos (correo, opcional)", "it": "Destinatari consentiti (e-mail, opzionale)"},
    "Leave empty to generate a 6-digit verification code instead. Otherwise a code will be sent to the recipient(s) (more secure!)": {
        "nl": "Laat leeg om in plaats daarvan een 6-cijferige verificatiecode te genereren. Anders wordt een code naar de ontvanger(s) gestuurd (veiliger!)",
        "fr": "Laissez vide pour générer un code de vérification à 6 chiffres. Sinon, un code sera envoyé au(x) destinataire(s) (plus sûr !)",
        "de": "Leer lassen, um stattdessen einen 6-stelligen Verifizierungscode zu generieren. Andernfalls wird ein Code an die Empfänger gesendet (sicherer!)",
        "es": "Déjelo vacío para generar un código de verificación de 6 dígitos. De lo contrario, se enviará un código a los destinatarios (¡más seguro!)",
        "it": "Lascia vuoto per generare un codice di verifica a 6 cifre. Altrimenti, un codice verrà inviato ai destinatari (più sicuro!)",
    },
    "Encrypted in your browser before sending.": {"nl": "Versleuteld in je browser voordat het verzonden wordt.", "fr": "Chiffré dans votre navigateur avant l'envoi.", "de": "Vor dem Senden in deinem Browser verschlüsselt.", "es": "Cifrado en tu navegador antes de enviarlo.", "it": "Crittografato nel tuo browser prima dell'invio."},
    "Create secure message": {"nl": "Maak veilig bericht", "fr": "Créer un message sécurisé", "de": "Sichere Nachricht erstellen", "es": "Crear mensaje seguro", "it": "Crea messaggio sicuro"},
    "Your secure message is ready": {"nl": "Je veilige bericht is klaar", "fr": "Votre message sécurisé est prêt", "de": "Deine sichere Nachricht ist bereit", "es": "Tu mensaje seguro está listo", "it": "Il tuo messaggio sicuro è pronto"},
    "Link": {"nl": "Link", "fr": "Lien", "de": "Link", "es": "Enlace", "it": "Link"},
    "Expires": {"nl": "Verloopt", "fr": "Expire", "de": "Läuft ab", "es": "Caduca", "it": "Scade"},
    "Verification code": {"nl": "Verificatiecode", "fr": "Code de vérification", "de": "Verifizierungscode", "es": "Código de verificación", "it": "Codice di verifica"},
    "Share this code via a separate channel from the link.": {"nl": "Deel deze code via een ander kanaal dan de link.", "fr": "Partagez ce code par un canal différent du lien.", "de": "Teile diesen Code über einen anderen Kanal als den Link.", "es": "Comparte este código por un canal distinto al del enlace.", "it": "Condividi questo codice tramite un canale diverso dal link."},
    "We only show this once. After closing this dialog, the link cannot be recovered from our database.": {
        "nl": "We tonen dit maar één keer. Na het sluiten van dit venster kan de link niet meer worden opgehaald uit onze database.",
        "fr": "Nous l'affichons une seule fois. Après la fermeture, le lien ne peut plus être récupéré de notre base de données.",
        "de": "Wir zeigen dies nur einmal. Nach dem Schließen kann der Link nicht mehr aus unserer Datenbank wiederhergestellt werden.",
        "es": "Lo mostramos solo una vez. Tras cerrar el cuadro, el enlace no se puede recuperar de la base de datos.",
        "it": "Lo mostriamo solo una volta. Dopo la chiusura, il link non può più essere recuperato dal database.",
    },
    "Copy all to clipboard": {"nl": "Kopieer alles naar klembord", "fr": "Tout copier", "de": "Alles in Zwischenablage kopieren", "es": "Copiar todo al portapapeles", "it": "Copia tutto negli appunti"},
    "Done": {"nl": "Klaar", "fr": "Terminé", "de": "Fertig", "es": "Listo", "it": "Fatto"},

    # --- Auth forms (most visible) ---
    "Email": {"nl": "E-mail", "fr": "Adresse e-mail", "de": "E-Mail", "es": "Correo electrónico", "it": "E-mail"},
    "Password": {"nl": "Wachtwoord", "fr": "Mot de passe", "de": "Passwort", "es": "Contraseña", "it": "Password"},
    "Remember me": {"nl": "Onthoud mij", "fr": "Se souvenir de moi", "de": "Angemeldet bleiben", "es": "Recordarme", "it": "Ricordami"},
    "Confirm password": {"nl": "Bevestig wachtwoord", "fr": "Confirmer le mot de passe", "de": "Passwort bestätigen", "es": "Confirmar contraseña", "it": "Conferma password"},
    "Create account": {"nl": "Account aanmaken", "fr": "Créer un compte", "de": "Konto erstellen", "es": "Crear cuenta", "it": "Crea account"},
    "Verify": {"nl": "Verifiëren", "fr": "Vérifier", "de": "Verifizieren", "es": "Verificar", "it": "Verifica"},
    "6-digit code": {"nl": "6-cijferige code", "fr": "Code à 6 chiffres", "de": "6-stelliger Code", "es": "Código de 6 dígitos", "it": "Codice a 6 cifre"},
    "Invalid e-mail or password.": {"nl": "Ongeldig e-mailadres of wachtwoord.", "fr": "E-mail ou mot de passe incorrect.", "de": "Ungültige E-Mail oder Passwort.", "es": "Correo o contraseña incorrectos.", "it": "E-mail o password non valide."},

    # --- Viewer ---
    "Secure message": {"nl": "Veilig bericht", "fr": "Message sécurisé", "de": "Sichere Nachricht", "es": "Mensaje seguro", "it": "Messaggio sicuro"},
    "Send code": {"nl": "Stuur code", "fr": "Envoyer le code", "de": "Code senden", "es": "Enviar código", "it": "Invia codice"},
    "Unlock": {"nl": "Ontgrendelen", "fr": "Déverrouiller", "de": "Entsperren", "es": "Desbloquear", "it": "Sblocca"},
    "Your e-mail": {"nl": "Je e-mailadres", "fr": "Votre e-mail", "de": "Deine E-Mail", "es": "Tu correo", "it": "La tua e-mail"},
    "Click below to decrypt this message in your browser.": {"nl": "Klik hieronder om dit bericht in je browser te ontsleutelen.", "fr": "Cliquez ci-dessous pour déchiffrer ce message dans votre navigateur.", "de": "Klicke unten, um diese Nachricht im Browser zu entschlüsseln.", "es": "Haz clic abajo para descifrar este mensaje en tu navegador.", "it": "Clicca qui sotto per decifrare questo messaggio nel browser."},
    "Reveal message": {"nl": "Toon bericht", "fr": "Afficher le message", "de": "Nachricht anzeigen", "es": "Mostrar mensaje", "it": "Mostra messaggio"},
    "Decrypted message": {"nl": "Ontsleuteld bericht", "fr": "Message déchiffré", "de": "Entschlüsselte Nachricht", "es": "Mensaje descifrado", "it": "Messaggio decifrato"},
    "Copy": {"nl": "Kopiëren", "fr": "Copier", "de": "Kopieren", "es": "Copiar", "it": "Copia"},
    "Burn now": {"nl": "Direct verbranden", "fr": "Détruire maintenant", "de": "Jetzt löschen", "es": "Destruir ahora", "it": "Distruggi ora"},
    "Destroy this message when I leave the page": {"nl": "Verwijder dit bericht zodra ik de pagina verlaat", "fr": "Détruire ce message quand je quitte la page", "de": "Diese Nachricht beim Verlassen der Seite löschen", "es": "Destruir este mensaje al salir de la página", "it": "Distruggi questo messaggio quando lascio la pagina"},
    "This message is no longer available.": {"nl": "Dit bericht is niet meer beschikbaar.", "fr": "Ce message n'est plus disponible.", "de": "Diese Nachricht ist nicht mehr verfügbar.", "es": "Este mensaje ya no está disponible.", "it": "Questo messaggio non è più disponibile."},
    "It may have expired, reached its open limit, or been burned by the recipient.": {
        "nl": "Het kan zijn dat het bericht is verlopen, het maximum aantal keer geopend is, of door de ontvanger is verbrand.",
        "fr": "Il peut avoir expiré, avoir atteint sa limite d'ouvertures ou avoir été détruit par le destinataire.",
        "de": "Sie ist möglicherweise abgelaufen, hat ihre Öffnungs­grenze erreicht oder wurde vom Empfänger gelöscht.",
        "es": "Puede haber caducado, haber alcanzado el límite de aperturas o haber sido destruido por el destinatario.",
        "it": "Potrebbe essere scaduto, aver raggiunto il limite di aperture o essere stato distrutto dal destinatario.",
    },
    "Message not available": {"nl": "Bericht niet beschikbaar", "fr": "Message indisponible", "de": "Nachricht nicht verfügbar", "es": "Mensaje no disponible", "it": "Messaggio non disponibile"},
    "Create a new message": {"nl": "Maak een nieuw bericht", "fr": "Créer un nouveau message", "de": "Neue Nachricht erstellen", "es": "Crear un nuevo mensaje", "it": "Crea un nuovo messaggio"},

    # --- Attachments (composer) ---
    "Attachments (optional)": {"nl": "Bijlagen (optioneel)", "fr": "Pièces jointes (optionnel)", "de": "Anhänge (optional)", "es": "Archivos adjuntos (opcional)", "it": "Allegati (opzionale)"},
    "Drop files here or click to choose": {"nl": "Sleep bestanden hierheen of klik om te kiezen", "fr": "Déposez des fichiers ici ou cliquez pour choisir", "de": "Dateien hierher ziehen oder klicken zum Auswählen", "es": "Suelta los archivos aquí o haz clic para elegir", "it": "Trascina i file qui o clicca per scegliere"},
    "Allowed file types:": {"nl": "Toegestane bestandstypen:", "fr": "Types de fichiers autorisés :", "de": "Erlaubte Dateitypen:", "es": "Tipos de archivo permitidos:", "it": "Tipi di file consentiti:"},
    "Any file type is allowed by this instance.": {"nl": "Op deze installatie zijn alle bestandstypen toegestaan.", "fr": "Cette instance autorise tous les types de fichiers.", "de": "Diese Instanz erlaubt jeden Dateityp.", "es": "Esta instancia permite cualquier tipo de archivo.", "it": "Questa istanza consente qualsiasi tipo di file."},
    "We cannot scan attachments for malware — only share files from senders you trust.": {
        "nl": "We kunnen bijlagen niet scannen op malware — deel alleen bestanden van afzenders die je vertrouwt.",
        "fr": "Nous ne pouvons pas analyser les pièces jointes — ne partagez que des fichiers provenant d'expéditeurs de confiance.",
        "de": "Wir können Anhänge nicht auf Schadsoftware scannen — teile nur Dateien von Absendern, denen du vertraust.",
        "es": "No podemos analizar los archivos adjuntos — comparte únicamente archivos de remitentes en los que confíes.",
        "it": "Non possiamo analizzare gli allegati per malware — condividi solo file di mittenti di cui ti fidi.",
    },
    "Message and any attachments are encrypted in your browser before sending.": {
        "nl": "Bericht en eventuele bijlagen worden in je browser versleuteld voordat ze verzonden worden.",
        "fr": "Le message et les pièces jointes sont chiffrés dans votre navigateur avant l'envoi.",
        "de": "Nachricht und Anhänge werden vor dem Senden in deinem Browser verschlüsselt.",
        "es": "El mensaje y los archivos adjuntos se cifran en tu navegador antes de enviarlos.",
        "it": "Il messaggio e gli eventuali allegati vengono crittografati nel tuo browser prima dell'invio.",
    },

    # --- Message viewer ---
    "View message": {"nl": "Bericht bekijken", "fr": "Voir le message", "de": "Nachricht ansehen", "es": "Ver mensaje", "it": "Visualizza messaggio"},
    "This message is restricted to specific recipients. Enter your e-mail address to receive a verification code.": {
        "nl": "Dit bericht is alleen toegankelijk voor specifieke ontvangers. Vul je e-mailadres in om een verificatiecode te ontvangen.",
        "fr": "Ce message est réservé à des destinataires spécifiques. Saisissez votre adresse e-mail pour recevoir un code de vérification.",
        "de": "Diese Nachricht ist auf bestimmte Empfänger beschränkt. Gib deine E-Mail-Adresse ein, um einen Verifizierungscode zu erhalten.",
        "es": "Este mensaje está restringido a destinatarios específicos. Introduce tu correo electrónico para recibir un código de verificación.",
        "it": "Questo messaggio è riservato a destinatari specifici. Inserisci il tuo indirizzo e-mail per ricevere un codice di verifica.",
    },
    "This link is missing the decryption key. Make sure you copied the full URL, including the part after the #.": {
        "nl": "De ontsleutelingssleutel ontbreekt in deze link. Controleer of je de volledige URL hebt gekopieerd, inclusief het deel achter de #.",
        "fr": "La clé de déchiffrement manque dans ce lien. Assurez-vous d'avoir copié l'URL complète, y compris la partie après le #.",
        "de": "Der Entschlüsselungsschlüssel fehlt in diesem Link. Stelle sicher, dass du die vollständige URL kopiert hast, einschließlich des Teils nach dem #.",
        "es": "A este enlace le falta la clave de descifrado. Asegúrate de copiar la URL completa, incluida la parte después del #.",
        "it": "Manca la chiave di decifratura in questo link. Assicurati di aver copiato l'URL completo, inclusa la parte dopo il #.",
    },

    # --- Attachments (viewer) ---
    "Attachments": {"nl": "Bijlagen", "fr": "Pièces jointes", "de": "Anhänge", "es": "Archivos adjuntos", "it": "Allegati"},
    "Download all (zip)": {"nl": "Alles downloaden (zip)", "fr": "Tout télécharger (zip)", "de": "Alle herunterladen (zip)", "es": "Descargar todo (zip)", "it": "Scarica tutto (zip)"},
    "We cannot scan attachments for malware. Only download files from senders you trust.": {
        "nl": "We kunnen bijlagen niet scannen op malware. Download alleen bestanden van afzenders die je vertrouwt.",
        "fr": "Nous ne pouvons pas analyser les pièces jointes. Ne téléchargez que des fichiers d'expéditeurs de confiance.",
        "de": "Wir können Anhänge nicht auf Schadsoftware scannen. Lade nur Dateien von Absendern herunter, denen du vertraust.",
        "es": "No podemos analizar los archivos adjuntos. Descarga únicamente archivos de remitentes en los que confíes.",
        "it": "Non possiamo analizzare gli allegati per malware. Scarica solo file di mittenti di cui ti fidi.",
    },

    # --- Admin storage panel ---
    "Storage": {"nl": "Opslag", "fr": "Stockage", "de": "Speicher", "es": "Almacenamiento", "it": "Spazio"},
    "Database": {"nl": "Database", "fr": "Base de données", "de": "Datenbank", "es": "Base de datos", "it": "Database"},
    "Total on disk": {"nl": "Totaal op schijf", "fr": "Total sur disque", "de": "Gesamt auf Festplatte", "es": "Total en disco", "it": "Totale su disco"},
    "files": {"nl": "bestanden", "fr": "fichiers", "de": "Dateien", "es": "archivos", "it": "file"},

    # --- Audit log card view ---
    "Detail": {"nl": "Details", "fr": "Détails", "de": "Details", "es": "Detalles", "it": "Dettagli"},
    "No events match this filter.": {"nl": "Geen gebeurtenissen voor dit filter.", "fr": "Aucun événement ne correspond à ce filtre.", "de": "Keine Ereignisse für diesen Filter.", "es": "Ningún evento coincide con este filtro.", "it": "Nessun evento corrisponde a questo filtro."},

    # --- Client-side strings (rendered into window.__OKP_I18N in base.html) ---
    "Theme: auto": {"nl": "Thema: automatisch", "fr": "Thème : auto", "de": "Thema: automatisch", "es": "Tema: automático", "it": "Tema: automatico"},
    "Theme: light": {"nl": "Thema: licht", "fr": "Thème : clair", "de": "Thema: hell", "es": "Tema: claro", "it": "Tema: chiaro"},
    "Theme: dark": {"nl": "Thema: donker", "fr": "Thème : sombre", "de": "Thema: dunkel", "es": "Tema: oscuro", "it": "Tema: scuro"},
    "Type not allowed": {"nl": "Bestandstype niet toegestaan", "fr": "Type non autorisé", "de": "Typ nicht erlaubt", "es": "Tipo no permitido", "it": "Tipo non consentito"},
    "Exceeds total limit": {"nl": "Overschrijdt totaallimiet", "fr": "Dépasse la limite totale", "de": "Überschreitet das Gesamtlimit", "es": "Supera el límite total", "it": "Supera il limite totale"},
    "Invalid:": {"nl": "Ongeldig:", "fr": "Invalide :", "de": "Ungültig:", "es": "No válido:", "it": "Non valido:"},
    "Please enter a message.": {"nl": "Voer een bericht in.", "fr": "Veuillez saisir un message.", "de": "Bitte gib eine Nachricht ein.", "es": "Introduce un mensaje.", "it": "Inserisci un messaggio."},
    "Please fix the invalid e-mail addresses:": {
        "nl": "Corrigeer de ongeldige e-mailadressen:",
        "fr": "Corrigez les adresses e-mail invalides :",
        "de": "Bitte korrigiere die ungültigen E-Mail-Adressen:",
        "es": "Corrige las direcciones de correo no válidas:",
        "it": "Correggi gli indirizzi e-mail non validi:",
    },
    "Server rejected these e-mail addresses:": {
        "nl": "De server heeft deze e-mailadressen afgewezen:",
        "fr": "Le serveur a rejeté ces adresses e-mail :",
        "de": "Der Server hat diese E-Mail-Adressen abgelehnt:",
        "es": "El servidor rechazó estas direcciones de correo:",
        "it": "Il server ha rifiutato questi indirizzi e-mail:",
    },
    "Failed to create message:": {
        "nl": "Aanmaken van bericht mislukt:",
        "fr": "Échec de la création du message :",
        "de": "Nachricht konnte nicht erstellt werden:",
        "es": "No se pudo crear el mensaje:",
        "it": "Impossibile creare il messaggio:",
    },
    "%(n)s attachment(s) will be skipped due to validation errors. Continue?": {
        "nl": "%(n)s bijlage(n) worden overgeslagen wegens validatiefouten. Doorgaan?",
        "fr": "%(n)s pièce(s) jointe(s) seront ignorée(s) en raison d'erreurs de validation. Continuer ?",
        "de": "%(n)s Anhang/Anhänge werden wegen Validierungsfehlern übersprungen. Fortfahren?",
        "es": "Se omitirán %(n)s archivo(s) adjunto(s) por errores de validación. ¿Continuar?",
        "it": "%(n)s allegato/i verrà/verranno saltato/i a causa di errori di validazione. Continuare?",
    },
    "Link:": {"nl": "Link:", "fr": "Lien :", "de": "Link:", "es": "Enlace:", "it": "Link:"},
    "Expires:": {"nl": "Verloopt:", "fr": "Expire :", "de": "Läuft ab:", "es": "Expira:", "it": "Scade:"},
    "Verification code:": {"nl": "Verificatiecode:", "fr": "Code de vérification :", "de": "Verifizierungscode:", "es": "Código de verificación:", "it": "Codice di verifica:"},
    "File name or MIME type is too long.": {
        "nl": "Bestandsnaam of MIME-type is te lang.",
        "fr": "Le nom de fichier ou le type MIME est trop long.",
        "de": "Dateiname oder MIME-Typ ist zu lang.",
        "es": "El nombre del archivo o el tipo MIME es demasiado largo.",
        "it": "Il nome del file o il tipo MIME è troppo lungo.",
    },
    "Unrecognised attachment format.": {
        "nl": "Onbekend bijlageformaat.",
        "fr": "Format de pièce jointe non reconnu.",
        "de": "Unbekanntes Anhangsformat.",
        "es": "Formato de archivo adjunto no reconocido.",
        "it": "Formato di allegato non riconosciuto.",
    },
    "plain text": {"nl": "platte tekst", "fr": "texte brut", "de": "Klartext", "es": "texto sin formato", "it": "testo semplice"},
    "Enter the 6-digit verification code the sender shared with you.": {
        "nl": "Voer de 6-cijferige verificatiecode in die de afzender met je heeft gedeeld.",
        "fr": "Saisissez le code de vérification à 6 chiffres que l'expéditeur vous a communiqué.",
        "de": "Gib den 6-stelligen Verifizierungscode ein, den der Absender mit dir geteilt hat.",
        "es": "Introduce el código de verificación de 6 dígitos que te ha compartido el remitente.",
        "it": "Inserisci il codice di verifica a 6 cifre che il mittente ha condiviso con te.",
    },
    "A 6-digit code has been sent if your e-mail is allowed.": {
        "nl": "Als je e-mailadres is toegestaan, is er een 6-cijferige code verzonden.",
        "fr": "Si votre adresse e-mail est autorisée, un code à 6 chiffres a été envoyé.",
        "de": "Wenn deine E-Mail-Adresse zugelassen ist, wurde ein 6-stelliger Code gesendet.",
        "es": "Si tu correo electrónico está permitido, se ha enviado un código de 6 dígitos.",
        "it": "Se il tuo indirizzo e-mail è autorizzato, è stato inviato un codice a 6 cifre.",
    },
    "Could not request a code.": {
        "nl": "Kan geen code opvragen.",
        "fr": "Impossible de demander un code.",
        "de": "Code konnte nicht angefordert werden.",
        "es": "No se pudo solicitar un código.",
        "it": "Impossibile richiedere un codice.",
    },
    "Decrypt & download": {
        "nl": "Ontsleutelen & downloaden",
        "fr": "Déchiffrer et télécharger",
        "de": "Entschlüsseln & herunterladen",
        "es": "Descifrar y descargar",
        "it": "Decifra e scarica",
    },
    "Saved": {"nl": "Opgeslagen", "fr": "Enregistré", "de": "Gespeichert", "es": "Guardado", "it": "Salvato"},
    "Failed": {"nl": "Mislukt", "fr": "Échec", "de": "Fehlgeschlagen", "es": "Error", "it": "Non riuscito"},
    "Preparing…": {"nl": "Voorbereiden…", "fr": "Préparation…", "de": "Wird vorbereitet…", "es": "Preparando…", "it": "In preparazione…"},
    "Copied": {"nl": "Gekopieerd", "fr": "Copié", "de": "Kopiert", "es": "Copiado", "it": "Copiato"},
    "Copy": {"nl": "Kopiëren", "fr": "Copier", "de": "Kopieren", "es": "Copiar", "it": "Copia"},
    "Invalid e-mail or verification code.": {
        "nl": "Ongeldig e-mailadres of verificatiecode.",
        "fr": "Adresse e-mail ou code de vérification invalide.",
        "de": "Ungültige E-Mail-Adresse oder Verifizierungscode.",
        "es": "Correo o código de verificación no válidos.",
        "it": "E-mail o codice di verifica non validi.",
    },
    "Could not retrieve the message.": {
        "nl": "Kan het bericht niet ophalen.",
        "fr": "Impossible de récupérer le message.",
        "de": "Nachricht konnte nicht abgerufen werden.",
        "es": "No se pudo recuperar el mensaje.",
        "it": "Impossibile recuperare il messaggio.",
    },

    # --- Legal pages additions (v1.3) ---
    "Keeps you signed in and protects forms (CSRF)": {
        "nl": "Houdt je ingelogd en beschermt formulieren (CSRF)",
        "fr": "Vous garde connecté et protège les formulaires (CSRF)",
        "de": "Hält dich angemeldet und schützt Formulare (CSRF)",
        "es": "Te mantiene conectado y protege los formularios (CSRF)",
        "it": "Ti mantiene connesso e protegge i moduli (CSRF)",
    },
    "Remembers that you dismissed the cookie notice": {
        "nl": "Onthoudt dat je de cookie-melding hebt weggeklikt",
        "fr": "Mémorise que vous avez fermé l'avis cookies",
        "de": "Merkt sich, dass du den Cookie-Hinweis geschlossen hast",
        "es": "Recuerda que has descartado el aviso de cookies",
        "it": "Ricorda che hai chiuso l'avviso sui cookie",
    },
    "All CSS, JavaScript and fonts are served from this server. No third-party tracking, analytics or CDN requests happen at runtime.": {
        "nl": "Alle CSS, JavaScript en lettertypen worden vanaf deze server geserveerd. Er vinden tijdens gebruik geen verzoeken naar tracking, analytics of CDN's plaats.",
        "fr": "Tout le CSS, JavaScript et les polices sont servis depuis ce serveur. Aucune requête de suivi, d'analyse ou de CDN n'a lieu à l'exécution.",
        "de": "Alle CSS-, JavaScript- und Schriftdateien werden von diesem Server bereitgestellt. Zur Laufzeit erfolgen keine Anfragen an Tracker, Analyse-Tools oder CDNs.",
        "es": "Todo el CSS, JavaScript y las fuentes se sirven desde este servidor. No se hacen peticiones de seguimiento, analítica ni CDN en ejecución.",
        "it": "Tutti i file CSS, JavaScript e i font sono serviti da questo server. A runtime non vengono effettuate richieste a tracker, analytics o CDN.",
    },
    "Attachments are encrypted with the same key as the message body, using a fresh AES-GCM nonce per file. The server only ever sees opaque ciphertext blobs — the original filename, MIME-type and contents are part of the encrypted payload and are invisible to the operator.": {
        "nl": "Bijlagen worden versleuteld met dezelfde sleutel als het bericht, met een verse AES-GCM nonce per bestand. De server ziet alleen ondoorzichtige ciphertext — de oorspronkelijke bestandsnaam, MIME-type en inhoud zitten in de versleutelde payload en zijn onzichtbaar voor de beheerder.",
        "fr": "Les pièces jointes sont chiffrées avec la même clé que le corps du message, avec un nonce AES-GCM frais par fichier. Le serveur ne voit que des blocs chiffrés opaques — le nom de fichier, le type MIME et le contenu d'origine font partie de la charge utile chiffrée et sont invisibles pour l'opérateur.",
        "de": "Anhänge werden mit demselben Schlüssel wie der Nachrichtentext verschlüsselt und nutzen pro Datei einen frischen AES-GCM-Nonce. Der Server sieht nur undurchsichtige Ciphertext-Blobs — der ursprüngliche Dateiname, MIME-Typ und Inhalt sind Teil der verschlüsselten Nutzlast und für den Betreiber unsichtbar.",
        "es": "Los archivos adjuntos se cifran con la misma clave que el mensaje, usando un nonce AES-GCM fresco por archivo. El servidor solo ve blobs cifrados opacos — el nombre original, el tipo MIME y el contenido forman parte del payload cifrado y son invisibles para el operador.",
        "it": "Gli allegati vengono crittografati con la stessa chiave del messaggio, usando un nonce AES-GCM fresco per ogni file. Il server vede solo blob di ciphertext opachi — nome del file, tipo MIME e contenuto originali fanno parte del payload crittografato e sono invisibili all'operatore.",
    },
    "Recipient e-mail addresses are stored only as keyed HMAC-SHA256 hashes": {
        "nl": "E-mailadressen van ontvangers worden alleen opgeslagen als keyed HMAC-SHA256-hashes",
        "fr": "Les adresses e-mail des destinataires ne sont stockées que sous forme de hachages HMAC-SHA256 à clé",
        "de": "E-Mail-Adressen der Empfänger werden nur als Keyed-HMAC-SHA256-Hashes gespeichert",
        "es": "Las direcciones de correo de los destinatarios solo se almacenan como hashes HMAC-SHA256 con clave",
        "it": "Gli indirizzi e-mail dei destinatari vengono memorizzati solo come hash HMAC-SHA256 con chiave",
    },
    "Server-side metadata (TOTP secrets, backup codes) is encrypted at rest with a dedicated key": {
        "nl": "Server-side metadata (TOTP-secrets, backup-codes) wordt versleuteld opgeslagen met een aparte sleutel",
        "fr": "Les métadonnées côté serveur (secrets TOTP, codes de secours) sont chiffrées au repos avec une clé dédiée",
        "de": "Server-seitige Metadaten (TOTP-Secrets, Backup-Codes) werden mit einem dedizierten Schlüssel ruhend verschlüsselt",
        "es": "Los metadatos del servidor (secretos TOTP, códigos de respaldo) se cifran en reposo con una clave dedicada",
        "it": "I metadati lato server (secret TOTP, codici di backup) vengono crittografati a riposo con una chiave dedicata",
    },
    "Transport and browser hardening": {
        "nl": "Transport- en browserbeveiliging",
        "fr": "Renforcement du transport et du navigateur",
        "de": "Transport- und Browser-Härtung",
        "es": "Endurecimiento de transporte y navegador",
        "it": "Hardening trasporto e browser",
    },
    "Strict Content-Security-Policy with per-request nonces — third-party or injected scripts cannot execute": {
        "nl": "Strikte Content-Security-Policy met nonces per request — externe of geïnjecteerde scripts kunnen niet draaien",
        "fr": "Content-Security-Policy stricte avec nonces par requête — les scripts tiers ou injectés ne peuvent pas s'exécuter",
        "de": "Strikte Content-Security-Policy mit Nonces pro Request — Dritt- oder injizierte Skripte können nicht ausgeführt werden",
        "es": "Content-Security-Policy estricta con nonces por solicitud — los scripts de terceros o inyectados no pueden ejecutarse",
        "it": "Content-Security-Policy rigorosa con nonce per richiesta — script di terze parti o iniettati non possono essere eseguiti",
    },
    "CSRF protection on every state-changing request": {
        "nl": "CSRF-bescherming op elke statuswijzigende request",
        "fr": "Protection CSRF sur chaque requête modifiant l'état",
        "de": "CSRF-Schutz bei jeder zustandsändernden Anfrage",
        "es": "Protección CSRF en todas las solicitudes que modifican el estado",
        "it": "Protezione CSRF su ogni richiesta che modifica lo stato",
    },
    "HTTP-only / SameSite session cookies": {
        "nl": "HTTP-only / SameSite session cookies",
        "fr": "Cookies de session HTTP-only / SameSite",
        "de": "HTTP-only / SameSite Session-Cookies",
        "es": "Cookies de sesión HTTP-only / SameSite",
        "it": "Cookie di sessione HTTP-only / SameSite",
    },
    "All CSS, JavaScript and fonts are vendored and served from this server — no CDN, no third-party requests at runtime": {
        "nl": "Alle CSS, JavaScript en lettertypen zijn vendored en worden vanaf deze server geserveerd — geen CDN, geen externe verzoeken tijdens gebruik",
        "fr": "Tous les fichiers CSS, JavaScript et polices sont vendorisés et servis depuis ce serveur — pas de CDN, pas de requêtes tierces à l'exécution",
        "de": "Alle CSS-, JavaScript- und Schriftdateien werden vendored und von diesem Server bereitgestellt — kein CDN, keine Drittanbieter-Anfragen zur Laufzeit",
        "es": "Todo el CSS, JavaScript y las fuentes están vendorizados y servidos desde este servidor — sin CDN, sin peticiones de terceros en ejecución",
        "it": "Tutti i file CSS, JavaScript e i font sono vendored e serviti da questo server — niente CDN, nessuna richiesta a terze parti a runtime",
    },
    "HSTS is set when the application is configured for HTTPS": {
        "nl": "HSTS wordt ingesteld wanneer de applicatie voor HTTPS is geconfigureerd",
        "fr": "HSTS est défini lorsque l'application est configurée pour HTTPS",
        "de": "HSTS wird gesetzt, wenn die Anwendung für HTTPS konfiguriert ist",
        "es": "HSTS se establece cuando la aplicación está configurada para HTTPS",
        "it": "HSTS viene impostato quando l'applicazione è configurata per HTTPS",
    },

    # --- Cleanup button + status hint ---
    "Run cleanup now": {"nl": "Opruimen nu", "fr": "Nettoyer maintenant", "de": "Jetzt aufräumen", "es": "Limpiar ahora", "it": "Pulisci ora"},
    "Stats reflect what is currently on disk. Burned or expired messages are purged automatically every 2 minutes.": {
        "nl": "De statistieken tonen wat er nu op schijf staat. Verbrande of verlopen berichten worden elke 2 minuten automatisch opgeruimd.",
        "fr": "Les statistiques reflètent ce qui est actuellement sur le disque. Les messages détruits ou expirés sont purgés automatiquement toutes les 2 minutes.",
        "de": "Die Statistiken zeigen, was aktuell auf der Festplatte liegt. Gelöschte oder abgelaufene Nachrichten werden alle 2 Minuten automatisch entfernt.",
        "es": "Las estadísticas reflejan lo que hay actualmente en disco. Los mensajes destruidos o caducados se eliminan automáticamente cada 2 minutos.",
        "it": "Le statistiche riflettono ciò che è attualmente su disco. I messaggi distrutti o scaduti vengono rimossi automaticamente ogni 2 minuti.",
    },
}


def apply(po_path: Path, lang: str) -> int:
    """Sync the .po file with the canonical TRANSLATIONS dict.

    The seed in this file is the source of truth. We:

      - Fill empty msgstrs (new strings just extracted by pybabel).
      - Replace ``fuzzy`` auto-matches that pybabel guessed from similar
        msgids and clear the flag.
      - Overwrite any msgstr that *differs* from the canonical seed — this
        lets us evolve translations (e.g. tone tweaks, terminology fixes)
        by editing this file and restarting the app; no need to invent a
        new msgid each time.

    Entries that already match the canonical seed are left untouched, so
    the seeder is idempotent and only writes when there's something to
    change.
    """
    if not po_path.exists():
        return 0
    with po_path.open("rb") as f:
        catalog = pofile.read_po(f, locale=lang)

    changed = 0
    for msgid, translations in TRANSLATIONS.items():
        if lang not in translations:
            continue
        msg = catalog.get(msgid)
        if msg is None:
            continue  # source string not extracted yet
        canonical = translations[lang]
        is_fuzzy = "fuzzy" in (msg.flags or set())
        if msg.string == canonical and not is_fuzzy:
            continue  # already at the canonical value
        msg.string = canonical
        if is_fuzzy:
            msg.flags.discard("fuzzy")
        changed += 1

    if changed:
        with po_path.open("wb") as f:
            pofile.write_po(f, catalog, width=76)
    return changed


def main() -> None:
    total = 0
    for lang_dir in PO_DIR.iterdir():
        if not lang_dir.is_dir():
            continue
        po = lang_dir / "LC_MESSAGES" / "messages.po"
        if not po.exists():
            continue
        n = apply(po, lang_dir.name)
        total += n
        print(f"{lang_dir.name}: filled {n} translations")
    print(f"---\nseeded {total} translation(s)")


if __name__ == "__main__":
    main()
