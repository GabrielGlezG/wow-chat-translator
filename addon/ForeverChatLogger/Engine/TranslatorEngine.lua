--[[
    TranslatorEngine.lua - Motor optimizado de traducción en Lua puro con coincidencia N-Gram.
    WoW Chat Translator (ForeverChatLogger)
]]

WoWChatTranslatorEngine = WoWChatTranslatorEngine or {}
local Engine = WoWChatTranslatorEngine

-- Adjetivos para regla de inversión sintáctica (Adjetivo + Sustantivo -> Sustantivo + Adjetivo)
local ADJECTIVES_MAP = {
    ["big"] = "grande",
    ["small"] = "pequeño",
    ["large"] = "enorme",
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
    ["wrong"] = "incorrecto",
    ["right"] = "correcto",
    ["first"] = "primer",
    ["last"] = "último",
    ["next"] = "siguiente"
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
    ["chest"] = "cofre",
    ["box"] = "caja",
    ["exit"] = "salida",
    ["entrance"] = "entrada",
    ["target"] = "objetivo",
    ["portal"] = "portal",
    ["item"] = "objeto",
    ["pack"] = "pack",
    ["side"] = "lado",
    ["room"] = "sala"
}

-- Normalizador de contracciones
function Engine.NormalizeContractions(text)
    if not text then return "" end
    local s = " " .. text:lower() .. " "
    
    s = s:gsub(" don'?t ", " no ")
    s = s:gsub(" can'?t ", " no puedo ")
    s = s:gsub(" won'?t ", " no voy a ")
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
    
    return s:match("^%s*(.-)%s*$")
end

-- Traducción de frases compuestas (N-Grams)
function Engine.MatchPhrases(text)
    local phrases = WoWChatTranslatorData.Phrases or {}
    local lower = text:lower()
    
    -- Limpieza de signos para coincidencia de frase
    local clean_lower = lower:gsub("[%.,%?!]", ""):match("^%s*(.-)%s*$")

    for _, entry in ipairs(phrases) do
        -- Si coincide exactamente la frase completa
        if clean_lower == entry.en then
            return entry.es
        end
    end

    -- Búsqueda de sub-frases dentro del texto
    local result = lower
    local matched_any = false
    for _, entry in ipairs(phrases) do
        local pat = "%f[%a]" .. entry.en:gsub("([%^%$%(%)%%%.%[%]%*%+%-%?])", "%%%1") .. "%f[%A]"
        if result:find(pat) then
            result = result:gsub(pat, "___PHRASE_" .. entry.es:gsub("%%", "%%%%") .. "___")
            matched_any = true
        end
    end

    if matched_any then
        -- Restaurar las frases traducidas
        result = result:gsub("___PHRASE_(.-)___", "%1")
        return result
    end

    return nil
end

-- Traducción palabra a palabra limpia con inversión gramatical
function Engine.TranslateWords(text)
    local dict = WoWChatTranslatorData.GeneralDict or {}
    local slang = WoWChatTranslatorData.FastSlang or {}
    local dungeons = WoWChatTranslatorData.Dungeons or {}

    -- Tokenizar respetando puntuación
    local tokens = {}
    for token in text:gmatch("[%w']+|?[^%w%s]?") do
        table.insert(tokens, token)
    end

    local out = {}
    local i = 1
    while i <= #tokens do
        local w = tokens[i]
        local w_clean = w:lower():gsub("[%.,%?!']", "")

        -- Regla de inversión: [Adjetivo] + [Sustantivo] -> [Sustantivo] [Adjetivo]
        -- Ejemplo: "blue key" -> "llave azul"
        local next_w = tokens[i + 1]
        local next_clean = next_w and next_w:lower():gsub("[%.,%?!']", "") or ""

        if ADJECTIVES_MAP[w_clean] and NOUNS_MAP[next_clean] then
            local adj_tr = ADJECTIVES_MAP[w_clean]
            local noun_tr = NOUNS_MAP[next_clean]
            table.insert(out, noun_tr .. " " .. adj_tr)
            i = i + 2
        else
            -- Búsqueda jerárquica limpia
            local tr = dungeons[w_clean] or slang[w_clean] or dict[w_clean]
            if tr then
                table.insert(out, tr)
            else
                table.insert(out, w)
            end
            i = i + 1
        end
    end

    local res = table.concat(out, " ")
    -- Limpieza de puntuación
    res = res:gsub("%s+([%.,%?!])", "%1")
    return res
end

-- Función principal de traducción EN -> ES
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
    if WoWChatTranslatorData.FastSlang[lower] then
        local res = WoWChatTranslatorData.FastSlang[lower]
        for k, v in pairs(token_map) do res = res:gsub(k, v) end
        return res
    end

    -- 2. Coincidencia en banco de N-Gramas y frases compuestas
    local phrase_match = Engine.MatchPhrases(clean)
    if phrase_match then
        for k, v in pairs(token_map) do phrase_match = phrase_match:gsub(k, v) end
        -- Añadir signo ¿ si es pregunta
        if clean:find("%?$") or phrase_match:find("^%s*dónde") or phrase_match:find("^%s*quién") or phrase_match:find("^%s*por qué") then
            if not phrase_match:find("^¿") then
                phrase_match = "¿" .. phrase_match
            end
            if not phrase_match:find("%?$") then
                phrase_match = phrase_match .. "?"
            end
        end
        return phrase_match:sub(1, 1):upper() .. phrase_match:sub(2)
    end

    -- 3. Normalizar contracciones
    local normalized = Engine.NormalizeContractions(clean)

    -- 4. Traducción léxica limpia
    local translated = Engine.TranslateWords(normalized)
    for k, v in pairs(token_map) do translated = translated:gsub(k, v) end

    -- Si no cambió nada, no mostrar subtítulo redundante
    if translated:lower() == clean:lower() then
        return nil
    end

    -- Formatear interrogación si corresponde
    if clean:find("%?$") and not translated:find("^¿") then
        translated = "¿" .. translated
    end

    return translated:sub(1, 1):upper() .. translated:sub(2)
end

-- Función de traducción inversa ES -> EN para responder (/en <mensaje>)
function Engine.TranslateEsToEn(message)
    if not message or message == "" then return message end
    local lower = message:lower():match("^%s*(.-)%s*$")
    local clean_lower = lower:gsub("[%.,%?!]", "")
    local rev = WoWChatTranslatorData.ReverseDict or {}

    -- Coincidencia directa de frase
    if rev[clean_lower] then
        return rev[clean_lower]
    end

    -- Traducción aproximada de palabras
    local out = {}
    for word in lower:gmatch("%S+") do
        local clean = word:gsub("[%.,%?!]", "")
        local tr = rev[clean]
        table.insert(out, tr or word)
    end
    return table.concat(out, " ")
end
