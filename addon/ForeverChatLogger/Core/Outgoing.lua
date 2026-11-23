local ADDON_NAME, addonTable = ...
addonTable = addonTable or WoWTranslatorNS -- clientes < 3.0 no pasan argumentos

-- ==========================================
-- MOTOR INVERSO (redactar en inglés)
-- ==========================================
-- Al revés que Core/Translator.lua: SUSTITUYE el término del idioma destino por
-- su original inglés en vez de anotarlo, porque el resultado va a la caja de
-- chat para que lo envíe el jugador.
--
-- El índice se construye la primera vez que se usa /wt en: son otras ~5.800
-- entradas de memoria y la mayoría de jugadores no redactará nunca en inglés.

local MasterDict = addonTable.MasterDict
local MultiWordPatterns = addonTable.MultiWordPatterns

local ipairs, pairs = ipairs, pairs
local string_find, string_gmatch, string_gsub, string_lower, string_match =
    string.find, string.gmatch, string.gsub, string.lower, string.match
local table_sort = table.sort

-- Aquí el texto de entrada está en el idioma destino, así que viene lleno de
-- acentos. "[%a%d']+" no vale: %a solo casa letras ASCII y partiría "Potrzebuję"
-- en "Potrzebuj" + "", dejando la palabra sin encontrar. Los bytes altos son
-- siempre continuación de un carácter UTF-8, así que entran en la clase.
local WORD = "[%w'\128-\255]+"

local function StripAccents(str)
    if not str then return "" end
    str = string_gsub(str, "á", "a")
    str = string_gsub(str, "é", "e")
    str = string_gsub(str, "í", "i")
    str = string_gsub(str, "ó", "o")
    str = string_gsub(str, "ú", "u")
    str = string_gsub(str, "ü", "u")
    str = string_gsub(str, "Á", "a")
    str = string_gsub(str, "É", "e")
    str = string_gsub(str, "Í", "i")
    str = string_gsub(str, "Ó", "o")
    str = string_gsub(str, "Ú", "u")
    str = string_gsub(str, "Ü", "u")
    return str
end
addonTable.StripAccents = StripAccents

-- Frases y expresiones coloquiales de alto uso en el chat de WoW (Español -> Inglés gamer)
local COLLOQUIAL_OUTGOING = {
    -- Saludos y despedidas
    ["hola a todos"] = "hi all",
    ["hola grupo"] = "hi team",
    ["hola raid"] = "hi raid",
    ["hola"] = "hi",
    ["buenas"] = "hello",
    ["saludos"] = "greetings",
    ["adios"] = "bye",
    ["nos vemos"] = "cya",
    ["buen trabajo"] = "gj",
    ["bien jugado"] = "gg",
    ["buena partida"] = "gg",
    ["gracias a todos"] = "ty all",
    ["muchas gracias"] = "tyvm",
    ["gracias"] = "ty",
    ["de nada"] = "yw",
    ["no te preocupes"] = "np",
    ["no pasa nada"] = "np",
    ["sin problema"] = "np",
    ["tranquilo"] = "np",
    ["tranquilos"] = "np",
    ["mala mia"] = "mb",
    ["mi culpa"] = "my bad",
    ["fue mi culpa"] = "my bad",
    ["perdon a todos"] = "sry all",
    ["perdon"] = "sry",
    ["disculpen"] = "sry",
    ["lo siento"] = "sry",

    -- Estado y peticiones comunes
    ["esperen por favor"] = "wait please",
    ["esperen un segundo"] = "wait sec",
    ["esperen un momento"] = "hold on",
    ["esperen"] = "wait",
    ["espera"] = "wait",
    ["esperame"] = "wait for me",
    ["sin mana"] = "oom",
    ["no tengo mana"] = "oom",
    ["bebiendo mana"] = "drinking mana",
    ["bebiendo"] = "drinking",
    ["comiendo"] = "eating",
    ["listos"] = "rdy",
    ["listo"] = "rdy",
    ["preparados"] = "rdy",
    ["todos listos"] = "all rdy",
    ["quien falta"] = "who is missing",
    ["ya vuelvo"] = "brb",
    ["vuelvo enseguida"] = "brb",
    ["ausente"] = "afk",
    ["en camino"] = "omw",
    ["voy de camino"] = "omw",
    ["voy"] = "omw",

    -- Combate y mecánicas
    ["no puleen todavia"] = "dont pull yet",
    ["no puleen"] = "dont pull",
    ["no jalen todavia"] = "dont pull yet",
    ["no jalen"] = "dont pull",
    ["puleen"] = "pull",
    ["jalen"] = "pull",
    ["cuidado con el aggro"] = "watch aggro",
    ["cuidado"] = "watch out",
    ["atentos"] = "watch out",
    ["sin aggro"] = "no aggro",
    ["foco al jefe"] = "focus boss",
    ["foco a los adds"] = "focus adds",
    ["foco al caster"] = "focus caster",
    ["ataquen al"] = "focus",
    ["corten el casteo"] = "kick cast",
    ["corten"] = "kick",
    ["interrumpan"] = "interrupt",
    ["limpien"] = "clean",
    ["dispeleen"] = "dispel",
    ["purguen"] = "purge",
    ["corran"] = "run",
    ["salgan del fuego"] = "out of fire",
    ["salgan"] = "get out",
    ["muerte total"] = "wipe",
    ["wipeamos"] = "wipe",
    ["nos morimos"] = "wipe",
    ["resucitenme"] = "rez me pls",
    ["resuciten"] = "rez pls",
    ["dame rez"] = "rez pls",
    ["necesito res"] = "need rez",
    ["dame bufo"] = "buff pls",
    ["dame buffs"] = "buffs pls",
    ["bufos por favor"] = "buffs pls",

    -- LFG, loot y hermandad
    ["busco grupo para"] = "lfg",
    ["busco grupo"] = "lfg",
    ["busco party"] = "lfg",
    ["busco mas"] = "lfm",
    ["buscamos gente"] = "lfm",
    ["invitame"] = "inv pls",
    ["invita"] = "inv",
    ["dame party"] = "inv pls",
    ["dame lider"] = "lead pls",
    ["puedo ir"] = "can i come",
    ["hay lugar"] = "any spot",
    ["donde esta"] = "where is",
    ["alguien sabe"] = "anyone know",
    ["alguien tiene"] = "anyone have",
    ["lo necesito"] = "need",
    ["lo quiero"] = "need",
    ["puedo tirar need"] = "can i need",
    ["puedo tirar codicia"] = "can i greed",
    ["paso de este item"] = "pass",
    ["paso"] = "pass",
    ["alguien lo quiere"] = "anyone need this",
    ["cuanto cuesta"] = "how much",
    ["compro"] = "wtb",
    ["vendo"] = "wts",
    ["cambio"] = "wtt",
    ["sanador"] = "healer",
    ["curador"] = "healer",
    ["tanque"] = "tank",
}
addonTable.COLLOQUIAL_OUTGOING = COLLOQUIAL_OUTGOING

local ReverseDict = {}    -- traducción -> término original
local ReverseByFirst = {} -- primera palabra -> { traducciones de varias palabras }
local builtVersion        -- versión del diccionario con la que se construyó

local function Build()
    wipe(ReverseDict)
    wipe(ReverseByFirst)

    -- Ojo: el número de palabras cambia de sentido respecto al motor normal. Un
    -- término de una palabra puede traducirse por varias ("wipe" -> "Muerte
    -- total") y al revés, así que aquí manda la traducción, no el original.
    local function add(translation, source)
        local key = string_lower(translation)
        local current = ReverseDict[key]
        if current then
            -- Varios originales caen en la misma traducción ("tank" y "tanks" ->
            -- "Tanque"). pairs() no tiene orden estable, así que sin un criterio
            -- explícito /wt en devolvería uno u otro según la sesión: gana el
            -- más corto y, a igualdad, el primero alfabéticamente.
            if #current < #source or (#current == #source and current <= source) then return end
            ReverseDict[key] = source -- la clave ya está en su bucket, solo cambia el destino
            return
        end

        ReverseDict[key] = source
        if string_find(key, " ", 1, true) then
            local first = string_match(key, WORD)
            if first then
                local bucket = ReverseByFirst[first]
                if not bucket then
                    bucket = {}
                    ReverseByFirst[first] = bucket
                end
                bucket[#bucket + 1] = key
            end
        end
    end

    for source, translation in pairs(MasterDict) do
        add(translation, source)
        local unacc = StripAccents(translation)
        if unacc ~= translation then add(unacc, source) end
    end
    for source, translation in pairs(MultiWordPatterns) do
        add(translation, source)
        local unacc = StripAccents(translation)
        if unacc ~= translation then add(unacc, source) end
    end

    -- Registrar frases coloquiales de alto uso
    for phrase, enTerm in pairs(COLLOQUIAL_OUTGOING) do
        add(phrase, enTerm)
        local unacc = StripAccents(phrase)
        if unacc ~= phrase then add(unacc, enTerm) end
    end

    for _, bucket in pairs(ReverseByFirst) do
        table_sort(bucket, function(a, b) return #a > #b end)
    end

    builtVersion = addonTable.dictVersion
end

function addonTable.TranslateOutgoing(text)
    if builtVersion ~= addonTable.dictVersion then Build() end

    local changed = false
    -- Un enlace con el nombre cambiado no se puede enviar.
    local links = {}
    text = addonTable.HideLinks(text, links)
    local textLower = string_lower(text)
    local seen = {}

    for word in string_gmatch(textLower, WORD) do
        local bucket = ReverseByFirst[word]
        if bucket and not seen[word] then
            seen[word] = true
            for _, phrase in ipairs(bucket) do
                if string_find(textLower, phrase, 1, true) then
                    local source = ReverseDict[phrase]
                    local replaced
                    text, replaced = string_gsub(text, addonTable.CaseInsensitivePattern(phrase),
                        function() return source end)
                    if replaced > 0 then
                        changed = true
                        textLower = string_lower(text)
                    end
                end
            end
        end
    end

    text = string_gsub(text, "(" .. WORD .. ")", function(word)
        local wLower = string_lower(word)
        local source = ReverseDict[wLower] or ReverseDict[StripAccents(wLower)]
        if not source then return word end
        changed = true
        return source
    end)

    return addonTable.RestoreLinks(text, links), changed
end
