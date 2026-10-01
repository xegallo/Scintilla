# Scintilla — protocollo di revisione capitolo per capitolo

> **Nota (1/10/2026).** Con la decisione di riscrivere il libro, questo protocollo vale per la revisione delle nuove stesure, blocco per blocco. Il confronto del punto 4 si fa anche con la scaletta del capitolo. Le correzioni che toccano più capitoli si risolvono per filo, in una sessione dedicata. Da aggiornare dopo la scomposizione in scene.

Protocollo per le sessioni in Claude Cowork, con la cartella `scintilla\libro` collegata. Vale per tutta la versione 2.

## Materiali di riferimento

Tutti in `libro/note/`, versionati in Git:

- `scheda-progetto-v2.md` — regole, livelli temporali, fonti, schede capitolo, registro semine e raccolte, decisioni. È la fonte di verità.
- `abbaglio-contesto.md` — canone di Abbaglio e vincoli per Scintilla. Abbaglio è la legge.
- `schede-personaggi.md` — schede dei personaggi.

Se una proposta richiede una decisione che la scheda non contiene, Claude non la inventa: fa la domanda.

## I tre passaggi

Ogni sessione dichiara all'inizio in quale passaggio si lavora. Le proposte riguardano solo quel passaggio; tutto il resto finisce nella lista "Da rimandare" del capitolo.

1. **Coerenza.** Errori del registro, canone (Matthews, Mi-Ran, date, Lum-Dat, titolo di Ka-Vin), intestazioni delle fonti, cronologia. Modifiche minime, la voce dell'autore non si tocca.
2. **Schiaffo.** Regola dei sensi, pensieri come deduzioni di Ka-Vin, regola del tempo verbale, indizi e chiave. Richiede prima una sessione dedicata alla progettazione della chiave.
3. **Stile.** Uniformità di registro, apostrofi tipografici, refusi, corsivi spuri.

## Procedura per un capitolo

### 1. Apertura

1. Verificare di essere sul ramo della versione 2: `python strumenti/sincronizza.py versione elenco`. Se serve: `versione passa 2`.
2. Ricordare all'autore di chiudere il `.docx` del capitolo.
3. Aprire il capitolo con la skill capitolo-apri: `python strumenti/sincronizza.py apri <nome-completo>`. Usare sempre il nome completo (per esempio `12-l-arca-blindata`): con il solo numero lo script confonde 12, 120 e 1200.
4. Leggere il capitolo intero e la sua scheda in `scheda-progetto-v2.md`, più le righe del registro che lo riguardano.

### 2. Divisione in blocchi

Dividere il capitolo in 5 o 6 blocchi, per tema o per lunghezza simile. Presentare la divisione così:

> **Blocco A** — righe/paragrafi da … a … — una riga di riassunto.

L'autore può chiedere di spostare i confini prima di cominciare.

### 3. Proposte, un blocco alla volta

Per ogni blocco, un elenco numerato. Ogni proposta ha questa forma:

> **[cap].[blocco].[n]** «testo originale esatto» → «testo proposto»
> *Motivo:* riferimento preciso (regola, riga del registro, vincolo del canone, decisione).

Regole:

- Il testo originale va citato alla lettera, così la modifica si può applicare senza ambiguità.
- Se un blocco non ha bisogno di modifiche nel passaggio in corso, scrivere solo: **Nessuna modifica necessaria.**
- Una proposta, una modifica. Niente proposte che ne contengono altre.
- Aspettare la risposta prima di passare al blocco successivo.

L'autore risponde per numero:

- `sì` — approvata così com'è;
- `no` — rifiutata;
- `modifica: …` — approvata con il testo indicato dall'autore;
- `rimanda` — spostata alla lista "Da rimandare".

Claude tiene aggiornato l'elenco delle decisioni del capitolo e lo mostra alla fine.

### 4. Rilettura e confronto

Prima di toccare il `.docx`:

1. Applicare le modifiche approvate a una copia temporanea: `/tmp/<nome>-rev.md`, partendo da `capitoli/<nome>.md`.
2. Mostrare il confronto parola per parola:
   `git diff --no-index --word-diff capitoli/<nome>.md /tmp/<nome>-rev.md`
3. Presentarlo in forma leggibile, blocco per blocco. L'autore conferma oppure chiede ritocchi, che rientrano nel punto 3.

### 5. Applicazione

Solo dopo il via libera:

1. Applicare le stesse modifiche a `word/<nome>.docx`, conservando gli stili del modello.
2. Verificare: `python strumenti/importa_docx.py word/<nome>.docx /tmp/<nome>-verifica.md`, poi confrontare con `/tmp/<nome>-rev.md`. I due file devono coincidere; se no, fermarsi e dirlo.
3. Non modificare mai `capitoli/` a mano: il Markdown lo genera lo strumento.

### 6. Sincronizzazione con Git

1. Salvare con la skill capitolo-salva:
   `python strumenti/sincronizza.py salva <nome> -m "capNN, passaggio P: <cosa cambia nel racconto>"`
2. Aggiornare `note/scheda-progetto-v2.md`: problemi risolti, stato delle righe del registro, nuove decisioni. Mostrare le modifiche all'autore prima di scriverle.
3. Salvare le note: `git add note/ && git commit -m "scheda: capNN, passaggio P" && git push`.
4. Se si lavora anche sull'altro PC, ricordare che lì serve `versione passa 2`.

### 7. Chiusura

Riepilogo breve: modifiche applicate, rifiutate, rimandate, e il capitolo successivo.

## Regole generali

- Mai `--force`, `reset --hard` o cancellazioni di rami.
- Su Windows `python`, non `python3`.
- Nessuna modifica fuori dal passaggio dichiarato, salvo refusi evidenti, che si propongono comunque e non si applicano senza approvazione.
- Ogni tanto la scheda aggiornata va riportata anche nella knowledge del progetto su claude.ai, sostituendo il file vecchio.
