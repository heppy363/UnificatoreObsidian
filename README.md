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
- un motore PDF compatibile con `pandoc`, ad esempio `tectonic`, `xelatex`, `lualatex` o `pdflatex`

Su Windows, per l'output PDF LaTeX e consigliato `tectonic` per setup portabili oppure `MiKTeX` se preferisci una installazione di sistema.

## Installazione locale

```powershell
git clone <REPO_URL>
cd UnificatoreObsidian
uv sync
```

Per preparare anche la build Windows standalone:

```powershell
uv sync --extra portable
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

Diagnostica binari rilevati:

```powershell
uv run unificatore-obsidian --diagnose
```

## Comportamento

- Il vault viene rilevato cercando la cartella `.obsidian` risalendo dai parent del file indice.
- Se `.obsidian` non esiste, viene usata la cartella che contiene `indice.md`.
- Se non specifichi `--pdf-engine`, il tool prova in automatico `tectonic`, poi `xelatex`, `lualatex` e `pdflatex`.
- I link verso note incluse nel PDF diventano link interni navigabili, utili soprattutto per l'indice iniziale.
- Per i PDF LaTeX il tool usa di default formato A4, `10pt`, margini da `18mm` e un header che prova a contenere meglio tabelle e immagini dentro la pagina.
- I binari vengono cercati prima tramite opzioni CLI e variabili ambiente, poi nelle cartelle locali `external/`, `tools/` e `.portable-tools/`, infine nel `PATH` di sistema.

## Setup portabile

Per evitare dipendenze globali puoi tenere i binari insieme al progetto. Esempio:

```text
UnificatoreObsidian/
  external/
    pandoc/
      pandoc.exe
    tectonic/
      tectonic.exe
```

Con questa struttura la CLI li rileva automaticamente, senza dover modificare il `PATH`.

In alternativa puoi indicare i percorsi esplicitamente:

```powershell
uv run unificatore-obsidian "D:\Vault\Documentazione\indice.md" `
  --pandoc-path ".\external\pandoc\pandoc.exe" `
  --pdf-engine tectonic `
  --pdf-engine-path ".\external\tectonic\tectonic.exe"
```

Oppure usare variabili ambiente:

```powershell
$env:UNIFICATORE_OBSIDIAN_PANDOC="D:\tools\pandoc\pandoc.exe"
$env:UNIFICATORE_OBSIDIAN_PDF_ENGINE="D:\tools\tectonic\tectonic.exe"
```

## Build CLI standalone per Windows

La build portabile resta una utility da riga di comando: produce un `.exe` console, non una GUI.

Build base:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-portable.ps1
```

Build con bundle locale di `pandoc` e `tectonic`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-portable.ps1 `
  -PandocSource "C:\tools\pandoc\pandoc.exe" `
  -PdfEngineSource "C:\tools\tectonic\tectonic.exe" `
  -PdfEngineName "tectonic"
```

Output prodotto:

- `dist\portable-cli\unificatore-obsidian.exe`
- `dist\portable-cli\external\...`
- `dist\unificatore-obsidian-portable-win64.zip`

Una volta copiato su un altro PC puoi usare direttamente:

```powershell
.\unificatore-obsidian.exe "D:\Vault\Documentazione\indice.md"
```

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
