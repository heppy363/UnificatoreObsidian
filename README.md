# Unificatore Obsidian

Utility Python che prende un `indice.md` dentro un vault Obsidian, segue i collegamenti alle note correlate e genera un PDF unificato tramite `pandoc`.

## Funzionalita

- Legge un file indice Markdown e segue i link Obsidian `[[nota]]` e `[[cartella/nota|alias]]`.
- Esplora ricorsivamente le note collegate, evitando duplicati e riferimenti circolari.
- Mantiene i file originali invariati e lavora su copie temporanee.
- Converte i link tra note in collegamenti interni cliccabili nel PDF finale.
- Adatta immagini e impaginazione a un layout A4 pensato per documentazione.
- Migliora la resa di tabelle larghe e liste annidate profonde in output PDF.
- Mostra avanzamento CLI, conteggio file processati e percorso finale del PDF.

## Requisiti

- Python 3.11+
- `uv`
- `pandoc`
- un motore PDF compatibile con `pandoc`, ad esempio `xelatex`, `lualatex` o `pdflatex`

Su Windows, per l'output PDF LaTeX e consigliato `MiKTeX`.

## Installazione locale

```powershell
git clone <REPO_URL>
cd UnificatoreObsidian
uv sync
```

## Uso

Esecuzione base:

```powershell
uv run unificatore-obsidian "D:\Vault\Documentazione\indice.md"
```

Output personalizzato:

```powershell
uv run unificatore-obsidian "D:\Vault\Documentazione\indice.md" -o "D:\Export\manuale.pdf"
```

Motore PDF esplicito:

```powershell
uv run unificatore-obsidian "D:\Vault\Documentazione\indice.md" --pdf-engine xelatex
```

## Comportamento

- Il vault viene rilevato cercando la cartella `.obsidian` risalendo dai parent del file indice.
- Se `.obsidian` non esiste, viene usata la cartella che contiene `indice.md`.
- Se non specifichi `--pdf-engine`, il tool prova in automatico `xelatex`, poi `lualatex`, poi `pdflatex`.
- I link verso note incluse nel PDF diventano link interni navigabili, utili soprattutto per l'indice iniziale.
- Per i PDF LaTeX il tool usa di default formato A4, `10pt`, margini da `18mm` e un header che prova a contenere meglio tabelle e immagini dentro la pagina.

## Sviluppo

Eseguire i test:

```powershell
uv run python -m unittest discover -s tests -v
```

Creare il pacchetto:

```powershell
uv build
```

## CI

Il repository include una GitHub Action che:

- esegue i test su Python 3.11, 3.12 e 3.13;
- verifica che il pacchetto sia buildabile con `uv build`.

## Licenza

[MIT](LICENSE)
