# assets/

Bundled templates and static resources.

| Path | Loaded by | Status |
|---|---|---|
| `carousel-templates/` | `scripts/render_carousel.py` | Active — the 8 shipped carousel templates |
| `gallery-template/gallery.html`, `gallery.css`, `gallery.js` | — | **Reference templates — not currently loaded by any script.** `scripts/build_gallery.py` emits its own self-contained `gallery.html` into the month's `review/` directory. Kept as the design reference for the review gallery markup. |
| `document-template/calendar-doc-structure.json` | — | **Reference template — not currently loaded by any script.** Kept as the structural reference for the delivery DOCX. |
| `default-fonts/`, `preview-templates/` | — | Empty — no fonts or preview templates are bundled. |
