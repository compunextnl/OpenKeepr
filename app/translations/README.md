# Translations

Source language: English (the gettext keys themselves).

Supported languages: `nl, fr, de, es, it`.

## How updates work

You don't need to run anything by hand. On every app startup (when
`AUTO_COMPILE_TRANSLATIONS=true`), OpenKeepr will:

1. Extract source strings from `app/**.py` and `app/templates/**.html` into `messages.pot`
2. Merge new strings into each existing `<lang>/LC_MESSAGES/messages.po`
3. Compile any `.po` whose mtime is newer than its `.mo` (or where `.mo` is missing)

`.po` files **are** tracked in git. `.mo` files are **not** (they're build output).

## Translating

Open any `app/translations/<lang>/LC_MESSAGES/messages.po` in your editor of
choice (Poedit is nice for non-developers). Fill in the empty `msgstr ""`
fields, save, and restart the app. That's it.

## Adding a new language

Add the ISO code to `AVAILABLE_LANGUAGES` in `.env`, restart. The catalog
will be initialised automatically. Then translate.
