# Stato Progetto

Data: 2026-06-13

## Obiettivo

Creare una utility Python che prenda un `indice.md` dentro un vault Obsidian e generi un PDF unificato con tutte le note collegate, senza modificare i file originali.

## Avanzamento

- [x] Analisi iniziale del workspace
- [x] Definizione struttura progetto con `uv`
- [x] Implementazione parser link Obsidian
- [x] Implementazione raccolta note e generazione PDF
- [x] Test locali
- [x] Rifinitura documentazione
- [x] Preparazione repository per pubblicazione su GitHub

## Note

- `uv` e disponibile nel sistema.
- La CLI e stata verificata localmente con `--help`.
- I test automatici passano: 15/15.
- Il packaging e stato verificato con `uv build` e produce correttamente sdist e wheel.
- Il builder ora seleziona automaticamente un motore PDF LaTeX disponibile, preferendo `xelatex`.
- Aggiunto un header LaTeX temporaneo con supporto a liste annidate profonde per evitare l'errore `Too deeply nested`.
- La CLI ora mostra una barra di avanzamento e un riepilogo finale con numero di file processati e percorso del PDF.
- Aggiunto preset di layout PDF A4 con margini, interlinea, ridimensionamento immagini e gestione piu robusta delle tabelle larghe.
- I collegamenti tra note raccolte vengono convertiti in link interni nel PDF e l'esplorazione ricorsiva evita duplicati anche in presenza di riferimenti circolari.
- Aggiunti file standard da repository pubblico: `LICENSE`, `.editorconfig`, `.gitattributes` e workflow CI GitHub Actions.
- La generazione PDF reale non e stata rilanciata qui solo per una differenza di `PATH` nell'ambiente degli strumenti rispetto alla shell utente.
