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
    -- Saludos y fórmulas sociales
    ["hola a todos"] = "hi all",
    ["hola grupo"] = "hi team",
    ["hola raid"] = "hi raid",
    ["hola amigos"] = "hi friends",
    ["hola gente"] = "hi guys",
    ["hola bro"] = "hi bro",
    ["hola"] = "hi",
    ["buenas tardes"] = "good afternoon",
    ["buenos dias"] = "good morning",
    ["buenas noches"] = "good evening",
    ["buenas"] = "hello",
    ["saludos"] = "greetings",
    ["como estan"] = "how are you",
    ["como andan"] = "how are you doing",
    ["como va"] = "how is it going",
    ["todo bien"] = "all good",
    ["adios"] = "bye",
    ["nos vemos"] = "cya",
    ["hasta luego"] = "see you later",
    ["chao"] = "bye",

    -- Cortesía y feedback
    ["buen trabajo a todos"] = "gj all",
    ["buen trabajo"] = "gj",
    ["bien jugado"] = "gg",
    ["buena partida"] = "gg",
    ["muchas gracias a todos"] = "tyvm all",
    ["muchas gracias por el grupo"] = "tyvm for group",
    ["muchas gracias por la party"] = "tyvm for party",
    ["muchas gracias por la ayuda"] = "tyvm for help",
    ["muchas gracias"] = "tyvm",
    ["gracias por el grupo"] = "ty for group",
    ["gracias por la party"] = "ty for party",
    ["gracias por la ayuda"] = "ty for help",
    ["gracias a todos"] = "ty all",
    ["gracias"] = "ty",
    ["de nada"] = "yw",
    ["no te preocupes"] = "np",
    ["no pasa nada"] = "no problem",
    ["sin problema"] = "np",
    ["tranquilo"] = "np",
    ["tranquilos"] = "np",
    ["mala mia"] = "mb",
    ["mi culpa"] = "my bad",
    ["fue mi culpa"] = "my bad",
    ["perdon a todos"] = "sry all",
    ["perdon"] = "sry",
    ["disculpa"] = "sry",
    ["disculpen"] = "sry",
    ["lo siento"] = "sry",
    ["por favor"] = "please",
    ["porfa"] = "pls",
    ["plis"] = "pls",

    -- Estado y peticiones comunes
    ["esperen por favor"] = "wait please",
    ["esperen un segundo"] = "wait sec",
    ["esperen un momento"] = "hold on",
    ["esperen"] = "wait",
    ["espera"] = "wait",
    ["esperame"] = "wait for me",
    ["sin mana"] = "oom",
    ["no tengo mana"] = "oom",
    ["recuperando mana"] = "drinking mana",
    ["bebiendo mana"] = "drinking mana",
    ["bebiendo"] = "drinking",
    ["comiendo"] = "eating",
    ["todos listos"] = "all rdy",
    ["listos para el pull"] = "rdy for pull",
    ["listos"] = "rdy",
    ["listo"] = "rdy",
    ["preparados"] = "rdy",
    ["quien falta"] = "who is missing",
    ["ya vuelvo"] = "brb",
    ["vuelvo enseguida"] = "brb",
    ["vuelvo en 5 min"] = "brb 5 min",
    ["ausente"] = "afk",
    ["en camino"] = "omw",
    ["voy de camino"] = "omw",
    ["voy"] = "omw",
    ["vamos alla"] = "lets go",
    ["vamos"] = "lets go",
    ["dale"] = "go",

    -- Combate y mecánicas
    ["no puleen todavia"] = "dont pull yet",
    ["no puleen"] = "dont pull",
    ["no jalen todavia"] = "dont pull yet",
    ["no jalen"] = "dont pull",
    ["puleen"] = "pull",
    ["jalen"] = "pull",
    ["cuidado con el aggro"] = "watch aggro",
    ["cuidado con"] = "watch out for",
    ["cuidado"] = "watch out",
    ["atentos a"] = "watch out for",
    ["atentos"] = "watch out",
    ["ojo con"] = "watch out for",
    ["sin aggro"] = "no aggro",
    ["foco al jefe"] = "focus boss",
    ["foco a los adds"] = "focus adds",
    ["foco al caster"] = "focus caster",
    ["foco a"] = "focus",
    ["ataquen al jefe"] = "focus boss",
    ["ataquen a los adds"] = "focus adds",
    ["ataquen al"] = "focus",
    ["corten el casteo"] = "kick cast",
    ["corten"] = "kick",
    ["interrumpan el casteo"] = "kick cast",
    ["interrumpan"] = "interrupt",
    ["limpien"] = "dispel",
    ["dispeleen"] = "dispel",
    ["purguen"] = "purge",
    ["corran"] = "run",
    ["salgan de ahi"] = "get out",
    ["salgan del fuego"] = "out of fire",
    ["salgan"] = "get out",
    ["muerte total"] = "wipe",
    ["wipeamos"] = "wipe",
    ["nos morimos"] = "wipe",
    ["resucitenme por favor"] = "rez me pls",
    ["resucitenme"] = "rez me pls",
    ["resuciten"] = "rez pls",
    ["dame rez"] = "rez pls",
    ["dame res"] = "rez pls",
    ["necesito res"] = "need rez",
    ["dame bufo"] = "buff pls",
    ["dame buffs"] = "buffs pls",
    ["bufos por favor"] = "buffs pls",
    ["dame portal"] = "portal pls",
    ["hagan invocacion"] = "summon pls",
    ["dame summon"] = "summon pls",
    ["dame piedra"] = "stone pls",

    -- LFG, loot y hermandad
    ["busco grupo para"] = "lfg",
    ["busco grupo"] = "lfg",
    ["busco party"] = "lfg",
    ["busco mas para"] = "lfm",
    ["busco mas"] = "lfm",
    ["buscamos gente"] = "lfm",
    ["invitame por favor"] = "inv pls",
    ["invitame al grupo"] = "inv to group pls",
    ["invitame a la hermandad"] = "inv to guild pls",
    ["invitame"] = "inv pls",
    ["invita"] = "inv",
    ["dame party"] = "inv pls",
    ["dame lider"] = "lead pls",
    ["puedo ir"] = "can i come",
    ["puedo entrar"] = "can i join",
    ["hay lugar"] = "any spot",
    ["donde esta la entrada"] = "where is entrance",
    ["donde esta"] = "where is",
    ["donde queda"] = "where is",
    ["alguien sabe donde"] = "anyone know where",
    ["alguien sabe"] = "anyone know",
    ["alguien tiene"] = "anyone have",
    ["alguien me ayuda con"] = "anyone help me with",
    ["alguien me ayuda"] = "anyone help me",
    ["alguien me invita a la hermandad"] = "anyone inv me to guild",
    ["alguien me invita al grupo"] = "anyone inv me to group",
    ["alguien me invita"] = "anyone inv me pls",
    ["ayuda por favor"] = "help pls",
    ["ayuda con"] = "help with",
    ["ayuda"] = "help",
    ["lo necesito"] = "need",
    ["lo quiero"] = "need",
    ["puedo tirar need por"] = "can i need for",
    ["puedo tirar need"] = "can i need",
    ["puedo tirar codicia"] = "can i greed",
    ["paso de este item"] = "pass",
    ["paso"] = "pass",
    ["alguien lo quiere"] = "anyone need this",
    ["alguien necesita esto"] = "anyone need this",
    ["alguien lo necesita"] = "anyone need this",
    ["cuanto cuesta"] = "how much",
    ["cuanto pides"] = "how much",
    ["compro"] = "wtb",
    ["vendo"] = "wts",
    ["cambio"] = "wtt",

    -- Roles, clases y términos de WoW
    ["sanador"] = "healer",
    ["curador"] = "healer",
    ["tanque"] = "tank",
    ["daño"] = "dps",
    ["guerrero"] = "warrior",
    ["paladin"] = "paladin",
    ["cazador"] = "hunter",
    ["picaro"] = "rogue",
    ["sacerdote"] = "priest",
    ["chaman"] = "shaman",
    ["mago"] = "mage",
    ["brujo"] = "warlock",
    ["druida"] = "druid",
    ["caballero de la muerte"] = "dk",

    -- Conectores, verbos y palabras cotidianas
    ["hacer una mazmorra"] = "do a dungeon",
    ["hacer mazmorra"] = "do dungeon",
    ["hacer la mision"] = "do the quest",
    ["esta mision"] = "this quest",
    ["esta mazmorra"] = "this dungeon",
    ["este item"] = "this item",
    ["este objeto"] = "this item",
    ["mazmorra"] = "dungeon",
    ["mision"] = "quest",
    ["hermandad"] = "guild",
    ["jefe"] = "boss",
    ["oro"] = "gold",
    ["plata"] = "silver",
    ["cobre"] = "copper",
    ["amigos"] = "friends",
    ["amigo"] = "friend",
    ["gente"] = "people",
    ["equipo"] = "team",
    ["portal"] = "portal",
    ["nivel"] = "level",
    ["vida"] = "hp",
    ["mana"] = "mana",
    ["si"] = "yes",
    ["no"] = "no",
    ["aqui"] = "here",
    ["alla"] = "there",
    ["ahora"] = "now",
    ["despues"] = "later",
    ["donde"] = "where",
    ["quien"] = "who",
    ["cuando"] = "when",
    ["como"] = "how",
    ["cuanto"] = "how much",
    ["por que"] = "why",
    ["porque"] = "because",
    ["para"] = "for",
    ["con"] = "with",
    ["sin"] = "without",
    ["en"] = "in",
    ["de"] = "of",
    ["el"] = "the",
    ["la"] = "the",
    ["los"] = "the",
    ["las"] = "the",
    ["un"] = "a",
    ["una"] = "a",
    ["unos"] = "some",
    ["unas"] = "some",
    ["este"] = "this",
    ["esta"] = "this",
    ["ese"] = "that",
    ["esa"] = "that",
    ["todos"] = "all",
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
