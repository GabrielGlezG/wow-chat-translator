--[[
    TranslatorEngine.lua - Motor optimizado de traducción en Lua puro con coincidencia N-Gram y gramática contextual.
    WoW Chat Translator (ForeverChatLogger)
    Compatible con WoW Forever, WotLK 3.3.5a, Classic y Retail.
]]

WoWChatTranslatorEngine = WoWChatTranslatorEngine or {}
local Engine = WoWChatTranslatorEngine

-- Tabla de tildes para normalización
local ACCENT_MAP = {
    ["á"] = "a", ["é"] = "e", ["í"] = "i", ["ó"] = "o", ["ú"] = "u",
    ["ü"] = "u", ["ñ"] = "n",
    ["Á"] = "a", ["É"] = "e", ["Í"] = "i", ["Ó"] = "o", ["Ú"] = "u",
    ["Ü"] = "u", ["Ñ"] = "n"
}

function Engine.StripAccents(str)
    if not str then return "" end
    local res = str
    for acc, plain in pairs(ACCENT_MAP) do
        res = res:gsub(acc, plain)
    end
    return res
end

-- Adjetivos para inversión sintáctica (Adjetivo + Sustantivo -> Sustantivo + Adjetivo)
local ADJECTIVES_MAP = {
    ["big"] = "grande",
    ["small"] = "pequeño",
    ["huge"] = "enorme",
    ["large"] = "grande",
    ["tiny"] = "diminuto",
    ["red"] = "rojo",
    ["blue"] = "azul",
    ["green"] = "verde",
    ["yellow"] = "amarillo",
    ["black"] = "negro",
    ["white"] = "blanco",
    ["dead"] = "muerto",
    ["alive"] = "vivo",
    ["bad"] = "malo",
    ["good"] = "bueno",
    ["great"] = "genial",
    ["wrong"] = "incorrecto",
    ["right"] = "correcto",
    ["first"] = "primer",
    ["last"] = "último",
    ["next"] = "siguiente",
    ["fast"] = "rápido",
    ["slow"] = "lento",
    ["safe"] = "seguro",
    ["dangerous"] = "peligroso",
    ["clean"] = "limpio",
    ["dirty"] = "sucio",
    ["open"] = "abierto",
    ["closed"] = "cerrado"
}

-- Sustantivos receptores de adjetivos
local NOUNS_MAP = {
    ["door"] = "puerta",
    ["doors"] = "puertas",
    ["key"] = "llave",
    ["keys"] = "llaves",
    ["boss"] = "jefe",
    ["bosses"] = "jefes",
    ["dragon"] = "dragón",
    ["dragons"] = "dragones",
    ["mob"] = "enemigo",
    ["mobs"] = "enemigos",
    ["pack"] = "grupo de bichos",
    ["chest"] = "cofre",
    ["box"] = "caja",
    ["exit"] = "salida",
    ["entrance"] = "entrada",
    ["target"] = "objetivo",
    ["portal"] = "portal",
    ["item"] = "objeto",
    ["items"] = "objetos",
    ["gear"] = "equipo",
    ["weapon"] = "arma",
    ["side"] = "lado",
    ["room"] = "sala",
    ["floor"] = "piso",
    ["bridge"] = "puente",
    ["stairs"] = "escaleras",
    ["adds"] = "bichos extras"
}

-- Normalizador de contracciones y abreviaturas en inglés
function Engine.NormalizeContractions(text)
    if not text then return "" end
    local s = " " .. text:lower() .. " "

    s = s:gsub(" don'?t ", " no ")
    s = s:gsub(" can'?t ", " no puedo ")
    s = s:gsub(" won'?t ", " no voy a ")
    s = s:gsub(" didn'?t ", " no ")
    s = s:gsub(" shouldn'?t ", " no debería ")
    s = s:gsub(" couldn'?t ", " no pude ")
    s = s:gsub(" i'?m ", " estoy ")
    s = s:gsub(" i'?ve ", " he ")
    s = s:gsub(" i'?ll ", " voy a ")
    s = s:gsub(" you'?re ", " estás ")
    s = s:gsub(" u ", " tú ")
    s = s:gsub(" ur ", " tu ")
    s = s:gsub(" r ", " están ")
    s = s:gsub(" plz ", " por favor ")
    s = s:gsub(" pls ", " por favor ")
    s = s:gsub(" thx ", " gracias ")
    s = s:gsub(" ty ", " gracias ")
    s = s:gsub(" w/? ", " con ")
    s = s:gsub(" w/o ", " sin ")
    s = s:gsub(" b/c ", " porque ")
    s = s:gsub(" bc ", " porque ")

    return s:match("^%s*(.-)%s*$")
end

-- Inicialización del índice inverso ES -> EN (ejecutado al cargar)
function Engine.InitializeReverseIndex()
    local rev = WoWChatTranslatorData.ReverseDict or {}
    local dict = WoWChatTranslatorData.GeneralDict or {}
    local phrases = WoWChatTranslatorData.Phrases or {}
    local slang = WoWChatTranslatorData.FastSlang or {}

    -- 1. Invertir diccionario general si no está presente en rev
    for en, es in pairs(dict) do
        local es_clean = es:lower():gsub("[%.,%?!¿¡]", ""):match("^%s*(.-)%s*$")
        if es_clean and not rev[es_clean] then
            rev[es_clean] = en
        end
        local es_no_acc = Engine.StripAccents(es_clean)
        if es_no_acc and not rev[es_no_acc] then
            rev[es_no_acc] = en
        end
    end

    -- 2. Invertir frases compuestas
    for _, p in ipairs(phrases) do
        local es_clean = p.es:lower():gsub("[%.,%?!¿¡]", ""):match("^%s*(.-)%s*$")
        if es_clean and not rev[es_clean] then
            rev[es_clean] = p.en
        end
        local es_no_acc = Engine.StripAccents(es_clean)
        if es_no_acc and not rev[es_no_acc] then
            rev[es_no_acc] = p.en
        end
    end

    -- 3. Invertir jerga rápida
    for en, es in pairs(slang) do
        local es_clean = es:lower():gsub("%s*%(.-%)", ""):gsub("[%.,%?!¿¡]", ""):match("^%s*(.-)%s*$")
        if es_clean and not rev[es_clean] then
            rev[es_clean] = en
        end
        local es_no_acc = Engine.StripAccents(es_clean)
        if es_no_acc and not rev[es_no_acc] then
            rev[es_no_acc] = en
        end
    end

    WoWChatTranslatorData.ReverseDict = rev
end

-- Búsqueda de frase exacta completa
function Engine.MatchPhrases(text)
    if not text then return nil end
    local clean_lower = text:lower():gsub("[%.,%?!¿¡]", ""):match("^%s*(.-)%s*$")
    local phrases = WoWChatTranslatorData.Phrases or {}
    for _, entry in ipairs(phrases) do
        if clean_lower == entry.en then
            return entry.es
        end
    end
    return nil
end
local FindExactPhrase = Engine.MatchPhrases

-- Búsqueda de N-Grams dentro de un grupo de tokens
local function FindSubPhrase(tokens, start_idx, max_len)
    local phrases = WoWChatTranslatorData.Phrases or {}
    local num_tokens = #tokens

    for len = math.min(max_len, num_tokens - start_idx + 1), 2, -1 do
        local words = {}
        for k = 0, len - 1 do
            local w = tokens[start_idx + k]:lower():gsub("[%.,%?!']", "")
            table.insert(words, w)
        end
        local candidate = table.concat(words, " ")

        for _, entry in ipairs(phrases) do
            if candidate == entry.en then
                return entry.es, len
            end
        end
    end

    return nil, 0
end

-- Traducción de tokens con N-Grams e inversión sintáctica
function Engine.TranslateWords(text)
    local dict = WoWChatTranslatorData.GeneralDict or {}
    local slang = WoWChatTranslatorData.FastSlang or {}
    local dungeons = WoWChatTranslatorData.Dungeons or {}

    -- Tokenizar por espacios respetando caracteres
    local raw_tokens = {}
    for token in text:gmatch("%S+") do
        table.insert(raw_tokens, token)
    end

    if #raw_tokens == 0 then return text end

    local out = {}
    local i = 1
    local translated_count = 0

    while i <= #raw_tokens do
        -- 1. Intentar coincidencia N-Gram (hasta 5 palabras consecutivas)
        local phrase_tr, phrase_len = FindSubPhrase(raw_tokens, i, 5)
        if phrase_tr then
            -- Conservar puntuación final del último token del N-Gram
            local last_tok = raw_tokens[i + phrase_len - 1]
            local trailing_punct = last_tok:match("([%.,%?!]+)$") or ""
            table.insert(out, phrase_tr .. trailing_punct)
            i = i + phrase_len
            translated_count = translated_count + 1
        else
            local tok = raw_tokens[i]
            local tok_clean = tok:lower():gsub("[%.,%?!']", "")
            local trailing_punct = tok:match("([%.,%?!]+)$") or ""

            -- 2. Regla de inversión: Adjetivo + Sustantivo -> Sustantivo + Adjetivo
            local next_tok = raw_tokens[i + 1]
            local next_clean = next_tok and next_tok:lower():gsub("[%.,%?!']", "") or ""
            local next_punct = next_tok and next_tok:match("([%.,%?!]+)$") or ""

            if ADJECTIVES_MAP[tok_clean] and NOUNS_MAP[next_clean] then
                local adj_tr = ADJECTIVES_MAP[tok_clean]
                local noun_tr = NOUNS_MAP[next_clean]
                table.insert(out, noun_tr .. " " .. adj_tr .. next_punct)
                i = i + 2
                translated_count = translated_count + 2
            else
                -- 3. Búsqueda directa en diccionarios
                local tr = dungeons[tok_clean] or slang[tok_clean] or dict[tok_clean]
                if tr then
                    table.insert(out, tr .. trailing_punct)
                    translated_count = translated_count + 1
                else
                    table.insert(out, tok)
                end
                i = i + 1
            end
        end
    end

    local result = table.concat(out, " ")
    return result, translated_count
end

-- ==============================================================================
-- FUNCIÓN PRINCIPAL DE TRADUCCIÓN EN -> ES (Incoming)
-- ==============================================================================
function Engine.TranslateEnToEs(message)
    if not message or message == "" then return message end

    -- Preservar hipervínculos de WoW (|c...|Hitem:...|h[...]|h|r)
    local token_map = {}
    local token_idx = 0
    local protected = message:gsub("(|c%x+|H[^|]+|h%[[^%]]+%]%|h|r)", function(link)
        token_idx = token_idx + 1
        local key = "___WOWTOKEN_" .. token_idx .. "___"
        token_map[key] = link
        return key
    end)

    local clean = protected:match("^%s*(.-)%s*$")
    local lower = clean:lower():gsub("[%.,%?!]", "")

    -- 1. Coincidencia rápida en jerga exacta
    local fastSlang = WoWChatTranslatorData.FastSlang or {}
    if fastSlang[lower] then
        local res = fastSlang[lower]
        for k, v in pairs(token_map) do res = res:gsub(k, v) end
        return res
    end

    -- 2. Coincidencia exacta de frase completa
    local exact_phrase = FindExactPhrase(lower)
    if exact_phrase then
        for k, v in pairs(token_map) do exact_phrase = exact_phrase:gsub(k, v) end
        return exact_phrase
    end

    -- 3. Normalizar contracciones
    local normalized = Engine.NormalizeContractions(clean)

    -- 4. Traducción léxica N-Gram con inversión
    local translated, translated_count = Engine.TranslateWords(normalized)
    for k, v in pairs(token_map) do translated = translated:gsub(k, v) end

    -- Si no se tradujo ninguna palabra, no mostrar subtítulo redundante
    if translated_count == 0 or translated:lower() == clean:lower() then
        return nil
    end

    -- Formatear interrogación si era pregunta
    if clean:find("%?$") and not translated:find("^¿") then
        translated = "¿" .. translated
    end

    -- Capitalizar primera letra de forma segura
    local first_byte = translated:byte(1)
    if first_byte and first_byte < 128 then
        translated = translated:sub(1, 1):upper() .. translated:sub(2)
    end

    return translated
end

-- ==============================================================================
-- FUNCIÓN DE TRADUCCIÓN INVERSA ES -> EN (Outgoing /en <mensaje>)
-- ==============================================================================
function Engine.TranslateEsToEn(message)
    if not message or message == "" then return message end

    -- Preservar hipervínculos de WoW
    local token_map = {}
    local token_idx = 0
    local protected = message:gsub("(|c%x+|H[^|]+|h%[[^%]]+%]%|h|r)", function(link)
        token_idx = token_idx + 1
        local key = "___WOWTOKEN_" .. token_idx .. "___"
        token_map[key] = link
        return key
    end)

    local clean = protected:match("^%s*(.-)%s*$")
    local lower = clean:lower()
    local clean_lower = lower:gsub("[%.,%?!¿¡]", ""):match("^%s*(.-)%s*$")
    local clean_no_acc = Engine.StripAccents(clean_lower)
    local rev = WoWChatTranslatorData.ReverseDict or {}

    -- 1. Coincidencia directa de frase completa (con y sin tildes)
    local match = rev[clean_lower] or rev[clean_no_acc]
    if match then
        for k, v in pairs(token_map) do match = match:gsub(k, v) end
        return match
    end

    -- 2. Tokenizar palabras
    local raw_tokens = {}
    for tok in lower:gmatch("%S+") do
        table.insert(raw_tokens, tok)
    end

    local out = {}
    local i = 1
    while i <= #raw_tokens do
        local tok = raw_tokens[i]
        local tok_clean = tok:gsub("[%.,%?!¿¡]", "")
        local tok_no_acc = Engine.StripAccents(tok_clean)
        local trailing_punct = tok:match("([%.,%?!]+)$") or ""

        -- Probar par de palabras consecutivas (2-gram)
        local next_tok = raw_tokens[i + 1]
        local pair_matched = false
        if next_tok then
            local next_clean = next_tok:gsub("[%.,%?!¿¡]", "")
            local pair = tok_clean .. " " .. next_clean
            local pair_no_acc = tok_no_acc .. " " .. Engine.StripAccents(next_clean)
            local next_punct = next_tok:match("([%.,%?!]+)$") or ""

            if rev[pair] or rev[pair_no_acc] then
                local tr_pair = rev[pair] or rev[pair_no_acc]
                table.insert(out, tr_pair .. next_punct)
                i = i + 2
                pair_matched = true
            end
        end

        if not pair_matched then
            local tr = rev[tok_clean] or rev[tok_no_acc]
            if tr then
                table.insert(out, tr .. trailing_punct)
            else
                table.insert(out, tok)
            end
            i = i + 1
        end
    end

    local result = table.concat(out, " ")
    for k, v in pairs(token_map) do result = result:gsub(k, v) end

    -- Formatear interrogación si era pregunta
    if (clean:find("%?$") or clean:find("^¿")) and not result:find("%?$") then
        result = result .. "?"
    end

    return result
end

-- Inicializar índice inverso al cargar el archivo
Engine.InitializeReverseIndex()
