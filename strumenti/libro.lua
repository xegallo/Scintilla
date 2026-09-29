--[[ Filtro pandoc per il libro.

Corpo del testo
  - una riga vuota separa i blocchi; un "a capo" semplice separa le righe
  - la prima riga di un blocco ha il rientro (stile "Corpo")
  - le righe successive, e il primo blocco del capitolo, no ("Corpo senza rientro")

Inserti (callout in stile Obsidian)
  > [!documento] TITOLO      -> "Documento titolo" + righe "Documento"/"Documento continua"
  > [!nota]                  -> un solo paragrafo "Nota", righe unite da a capo

Apertura capitolo
  ::: {.apertura etichetta="..." sottotitolo="..."}   (generato da esporta.py)
]]

local function styled(style, inlines)
  return pandoc.Div({ pandoc.Para(inlines) }, { ["custom-style"] = style })
end

-- divide gli inline di un paragrafo sulle interruzioni di riga
local function split_lines(inlines)
  local lines, cur = {}, {}
  for _, el in ipairs(inlines) do
    if el.t == "SoftBreak" or el.t == "LineBreak" then
      table.insert(lines, cur); cur = {}
    else
      table.insert(cur, el)
    end
  end
  table.insert(lines, cur)
  local out = {}
  for _, l in ipairs(lines) do
    while #l > 0 and l[1].t == "Space" do table.remove(l, 1) end
    while #l > 0 and l[#l].t == "Space" do table.remove(l) end
    if #l > 0 then table.insert(out, l) end
  end
  return out
end

-- trasforma un blockquote-callout nei paragrafi stilizzati
local function callout(bq)
  local blocks = bq.content
  local first = blocks[1]
  if not first or (first.t ~= "Para" and first.t ~= "Plain") then return nil end
  local marker = first.content[1]
  if not marker or marker.t ~= "Str" then return nil end
  local tipo = marker.text:match("^%[!(%w+)%]$")
  if not tipo then return nil end
  tipo = tipo:lower()

  -- separa la riga del titolo dal resto del primo paragrafo
  local lines = split_lines(first.content)
  local head = lines[1]; table.remove(head, 1)
  while #head > 0 and head[1].t == "Space" do table.remove(head, 1) end
  table.remove(lines, 1)

  local paras = {}
  if #lines > 0 then table.insert(paras, lines) end
  for i = 2, #blocks do
    local b = blocks[i]
    if b.t == "Para" or b.t == "Plain" then
      table.insert(paras, split_lines(b.content))
    end
  end

  local out = {}
  if tipo == "nota" then
    if #head > 0 then table.insert(paras, 1, { head }) end
    for _, p in ipairs(paras) do
      local joined = {}
      for j, l in ipairs(p) do
        if j > 1 then table.insert(joined, pandoc.LineBreak()) end
        for _, el in ipairs(l) do table.insert(joined, el) end
      end
      table.insert(out, styled("Nota", joined))
    end
  else
    local base = tipo:sub(1, 1):upper() .. tipo:sub(2)   -- es. "Documento"
    if #head > 0 then table.insert(out, styled(base .. " titolo", head)) end
    for _, p in ipairs(paras) do
      for j, l in ipairs(p) do
        table.insert(out, styled(j == 1 and base or (base .. " continua"), l))
      end
    end
  end
  return out
end

local SEZIONE = '<w:p><w:pPr><w:sectPr>{{SEZIONE}}</w:sectPr></w:pPr></w:p>'

function Pandoc(doc)
  local out = {}
  local first_block = true   -- primo blocco di corpo dopo l'apertura
  local n_cap = 0
  for _, b in ipairs(doc.blocks) do
    if b.t == "Div" and b.classes:includes("apertura") then
      n_cap = n_cap + 1
      if n_cap > 1 then
        -- fine del capitolo precedente: interruzione di sezione (nuova pagina)
        table.insert(out, pandoc.RawBlock("openxml", SEZIONE))
      end
      local a = b.attributes
      if a.etichetta and a.etichetta ~= "" then
        table.insert(out, styled("Etichetta capitolo", { pandoc.Str(pandoc.text.upper(a.etichetta)) }))
      end
      for _, x in ipairs(b.content) do table.insert(out, x) end
      if a.sottotitolo and a.sottotitolo ~= "" then
        table.insert(out, styled("Sottotitolo capitolo", pandoc.read(a.sottotitolo).blocks[1].content))
      end
      first_block = true
    elseif b.t == "Para" or b.t == "Plain" then
      for j, l in ipairs(split_lines(b.content)) do
        local st = (j == 1 and not first_block) and "Corpo" or "Corpo senza rientro"
        table.insert(out, styled(st, l))
      end
      first_block = false
    elseif b.t == "BlockQuote" then
      local c = callout(b)
      for _, x in ipairs(c or { b }) do table.insert(out, x) end
    else
      table.insert(out, b)
    end
  end
  doc.blocks = out
  return doc
end
