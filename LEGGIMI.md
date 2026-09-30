# Libro – come funziona

Scrivi in Word. Git conserva la cronologia dei capitoli in formato testo (Markdown),
che serve anche per sincronizzare i due PC.

## Cartelle
- `word/` – **i capitoli su cui lavori** (`00-prologo.docx`, `01-…`). Non vanno in Git.
- `capitoli/` – la versione Markdown di ogni capitolo, salvata in Git. Non si modifica a mano.
- `strumenti/` – modello di stile, script. Non si toccano.
- `esporta/` – il libro completo (`libro.docx`), rigenerabile in ogni momento.

## Flusso di lavoro
**Sincronizzazione automatica.** Installala una volta sola:
- Ubuntu: `sh strumenti/installa-autosync.sh`
- Windows: `powershell -ExecutionPolicy Bypass -File strumenti\installa-autosync.ps1`
Da quel momento:
- apri un capitolo da `word/`, scrivi, salva in formato Word e chiudi;
- entro circa un minuto il capitolo viene salvato in Git e inviato a GitHub;
- ogni 5 minuti arrivano da soli i capitoli modificati sull'altro PC;
- i file aperti non vengono mai toccati;
- le notifiche sul desktop segnalano salvataggi, aggiornamenti e problemi
  (su Windows servono le notifiche BurntToast: `Install-Module BurntToast -Scope CurrentUser`;
  senza, resta il registro).
Registro: `word/.stato/autosync.log`.

**A mano** (o chiedendo a Claude "apri / salva il capitolo 3"):
`python3 strumenti/sincronizza.py apri 03` e `python3 strumenti/sincronizza.py salva 03 -m "…"`.

**Libro completo**: "assembla il libro" oppure `python3 strumenti/sincronizza.py libro`
→ `esporta/libro.docx`. Usa i capitoli salvati in Git.

`python3 strumenti/sincronizza.py elenco` mostra lo stato di tutti i capitoli.

## Versioni del libro (rami)
Il ramo principale (`main`) contiene sempre la versione completa; ogni nuova stesura
si lavora in un ramo a parte.
```
python3 strumenti/sincronizza.py versione elenco       versioni e quella in uso
python3 strumenti/sincronizza.py versione nuova 12     crea la versione 12
python3 strumenti/sincronizza.py versione passa 12     ci si sposta sopra (anche sull'altro PC)
python3 strumenti/sincronizza.py versione passa main   torna alla versione completa
python3 strumenti/sincronizza.py versione unisci 12    porta la 12 dentro main
```
Il cambio di versione si rifiuta se ci sono capitoli modificati e non salvati o file
aperti, e rigenera i `.docx` di `word/` con il contenuto della versione scelta.
**I due PC devono stare sulla stessa versione**: la sincronizzazione automatica lavora
solo sul ramo in uso. Dopo `versione nuova`, sull'altro PC serve `versione passa`.

## Come riconosce le parti del testo
Dagli stili Word del modello (o dalla formattazione dei vecchi capitoli):
- Etichetta capitolo / Heading 1 / Sottotitolo capitolo → apertura del capitolo
- Corpo (con rientro) → inizio di un blocco; Corpo senza rientro → riga che lo continua
- Nota → nota di trascrizione
- Documento titolo / Documento / Documento continua → inserto documentale

Tutto ciò che non rientra in questi stili (colori, commenti, revisioni, immagini,
tabelle) **non viene conservato**. Grassetto e corsivo invece sì.

## Nuovo capitolo
Salva il file in `word/` con nome `NN-titolo.docx` (es. `03-la-cripta.docx`), poi "salva il capitolo 3".

## Conflitti
Se lo stesso paragrafo è stato cambiato su entrambi i PC, quel capitolo non viene salvato:
le due versioni finiscono in `word/.stato/conflitti/<capitolo>.md` tra `<<<<<<<` e `>>>>>>>`
e compare una notifica. Chiedi a Claude di risolverlo; a mano: si sceglie quale versione
tenere in quel file, poi `python3 strumenti/sincronizza.py risolto <capitolo>`.

## Requisiti (su entrambi i PC)
Git, Python 3 (`pip install python-docx`), [pandoc](https://pandoc.org/installing.html).
