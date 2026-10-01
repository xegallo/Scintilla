# Scintilla — sessione Cowork: scomposizione in scene

Istruzioni per una sessione Cowork dedicata, con la cartella `scintilla\libro` collegata. Obiettivo: un file che riassume ogni capitolo in scene e verifica, scena per scena, se arriva ciò che l'autore vuole dire. È la base per la scaletta della riscrittura.

La lunghezza non è un obiettivo di questa fase. La priorità è che si capisca ciò che il libro vuole comunicare.

## Materiali

- Capitoli: `capitoli/01-*.md` … `capitoli/21-*.md` (ramo della versione 2).
- Riferimenti in `note/`: `scheda-progetto-v2.md` (fonte di verità), `abbaglio-contesto.md`, `schede-personaggi.md`.

## Compito

Leggere i 21 capitoli, nell'ordine, e scrivere `note/scene-v1.md` seguendo il modello qui sotto. Non si corregge e non si riscrive: si descrive e si valuta la chiarezza.

## Cos'è una scena

Un tratto continuo di tempo, luogo e fonte. Si apre una scena nuova quando cambia almeno uno di questi elementi: luogo, salto di tempo, livello temporale (t0–t3), fonte del reperto, personaggio al centro.

## Modello per ogni capitolo

```
## Cap. NN — Titolo

Livello: … · Fonte: … · Intenzione del capitolo (dalla scheda): …

| # | Scena | Livello e fonte | Personaggi | Cosa succede | Cosa deve comunicare | Arriva? | Stato |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | titolo breve | t1, occhiali RA | Vince | una o due righe | l'idea, l'emozione o l'indizio che la scena porta | sì / in parte / no | piena / riassunta / abbozzata |

**Cosa ostacola la comprensione.** Per ogni scena con "in parte" o "no": cosa impedisce al lettore di capire (contraddizione, informazione mancante, ordine degli eventi, prosa che copre il senso, punto di vista confuso). Citare il passaggio.

**Ambiguità volute e non volute.** La scheda prevede confusioni volute (Ka-Vin e il tecnico, la Signora e Mira). Distinguere queste da quelle casuali, che vanno segnalate.

**Scene mancanti.** Solo quelle richieste da decisioni già prese nella scheda (per esempio il viaggio di Vince tra i capp. 15 e 19). Nessuna invenzione di trama.

**Registro.** Righe del registro semine e raccolte che riguardano il capitolo, citate per nome.
```

Significato delle colonne:

- **Cosa deve comunicare**: ricavato dalla scheda ("Cosa comunica") e dal testo. Se la scheda e il testo non coincidono, dirlo: è una domanda per l'autore.
- **Arriva?**: se un lettore attento, alla prima lettura, coglie ciò che la scena deve comunicare. Per le scene con ambiguità volute, la domanda è se l'ambiguità funziona come previsto.
- **Stato**: piena (mostrata, con azione e dialogo), riassunta (raccontata in poche righe), abbozzata (appena accennata, più appunto che scena).

## Riepilogo finale

In fondo al file:

1. Una tabella con capitolo, numero di scene, scene che arrivano, in parte, no.
2. Le tre o quattro cause più frequenti per cui una scena non arriva, con i capitoli in cui compaiono.
3. Le domande per l'autore, numerate, dove l'intenzione non è ricavabile né dalla scheda né dal testo.

## Regole

- Non modificare `capitoli/` né `word/`. Scrivere solo `note/scene-v1.md`.
- Nessuna proposta di riscrittura: questa fase serve a capire, non a correggere.
- Alla fine: `git add note/scene-v1.md`, commit "note: scomposizione in scene" e push, dopo conferma dell'autore.
