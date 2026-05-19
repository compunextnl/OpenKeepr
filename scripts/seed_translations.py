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
    "Support development": {"nl": "Ondersteun de ontwikkeling", "fr": "Soutenir le développement", "de": "Entwicklung unterstützen", "es": "Apoyar el desarrollo", "it": "Sostieni lo sviluppo"},
    "Buy me a coffee": {"nl": "Trakteer me op een koffie", "fr": "Offrez-moi un café", "de": "Spendier mir einen Kaffee", "es": "Invítame a un café", "it": "Offrimi un caffè"},
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
    "Share secrets safely": {"nl": "Geheimen veilig delen", "fr": "Partagez vos secrets en toute sécurité", "de": "Geheimnisse sicher teilen", "es": "Comparte secretos de forma segura", "it": "Condividi segreti in sicurezza"},
    "Share a secret. Once. Safely.": {"nl": "Deel een geheim. Eén keer. Veilig.", "fr": "Partagez un secret. Une fois. En toute sécurité.", "de": "Teile ein Geheimnis. Einmal. Sicher.", "es": "Comparte un secreto. Una vez. De forma segura.", "it": "Condividi un segreto. Una volta. In sicurezza."},
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
    "Your secret message…": {"nl": "Je geheime bericht…", "fr": "Votre message secret…", "de": "Deine geheime Nachricht…", "es": "Tu mensaje secreto…", "it": "Il tuo messaggio segreto…"},
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
    "Create a new message": {"nl": "Maak een nieuw bericht", "fr": "Créer un nouveau message", "de": "Neue Nachricht erstellen", "es": "Crear un nuevo mensaje", "it": "Crea un nuovo messaggio"},
}


def apply(po_path: Path, lang: str) -> int:
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
        if msg.string:  # already translated — don't overwrite
            continue
        msg.string = translations[lang]
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
