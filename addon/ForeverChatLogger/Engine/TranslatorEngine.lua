--[[
    TranslatorEngine.lua - Motor gramatical de traducción en Lua puro para WoW.
    WoW Chat Translator (ForeverChatLogger)
]]

WoWChatTranslatorEngine = WoWChatTranslatorEngine or {}
local Engine = WoWChatTranslatorEngine

-- Adjetivos comunes para la regla de inversión sintáctica (Adjetivo + Sustantivo -> Sustantivo + Adjetivo)
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

-- Sustantivos comunes receptores de adjetivos
local NOUNS_MAP = {
    ["door"] = "puerta",
    ["doors"] = "puertas",
    ["key"] = "llave",
    ["keys"] = "llaves",
    ["boss"] = "jefe",
    ["mob"] = "enemigo",
    ["mobs"] = "enemigos",
    ["chest"] = "cofre",
    ["box"] = "caja",
    ["exit"] = "salida",
    ["entrance"] = "entrada",
    ["target"] = "objetivo",
    ["dragon"] = "dragón",
    ["portal"] = "portal",
    ["item"] = "objeto",
    ["pack"] = "grupo de mobs",
    ["side"] = "lado",
    ["room"] = "sala"
}

-- Normalización de contracciones informales en inglés
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

-- Plantillas sintácticas de oraciones comunes (Sujeto + Verbo + Complemento)
local SENTENCE_TEMPLATES = {
    -- Preguntas de localización y ayuda
    {
        pat = "^can someone tell me where (.+) is%??$",
        rep = "¿Alguien puede decirme dónde está %1?"
    },
    {
        pat = "^can someone tell me (.+)%??$",
        rep = "¿Alguien puede decirme %1?"
    },
    {
        pat = "^does anyone know where (.+) is%??$",
        rep = "¿Alguien sabe dónde está %1?"
    },
    {
        pat = "^does anyone know (.+)%??$",
        rep = "¿Alguien sabe %1?"
    },
    {
        pat = "^where is (?:the )?(.+)%??$",
        rep = "¿Dónde está %1?"
    },
    {
        pat = "^who has (?:the )?(.+)%??$",
        rep = "¿Quién tiene %1?"
    },
    {
        pat = "^anyone (?:have|has) (?:the )?(.+)%??$",
        rep = "¿Alguien tiene %1?"
    },
    -- Peticiones de tiempo y espera
    {
        pat = "^i need to go eat dinner,? (.+)$",
        rep = "Tengo que ir a cenar, %1"
    },
    {
        pat = "^i need to go eat dinner$",
        rep = "Tengo que ir a cenar"
    },
    {
        pat = "^i have to go,? (.+)$",
        rep = "Me tengo que ir, %1"
    },
    {
        pat = "^i have to go$",
        rep = "Me tengo que ir"
    },
    {
        pat = "^wait for me (?:for )?(.+)$",
        rep = "Espérenme %1"
    },
    {
        pat = "^wait for me$",
        rep = "Espérenme"
    },
    {
        pat = "^wait for (.+)$",
        rep = "Esperen a %1"
    },
    {
        pat = "^can you wait (?:for )?(.+)%??$",
        rep = "¿Pueden esperar %1?"
    },
    -- Problemas técnicos y caídas
    {
        pat = "^my computer is having issues and restarting$",
        rep = "Mi computadora tiene problemas y se está reiniciando"
    },
    {
        pat = "^my pc is restarting$",
        rep = "Mi PC se está reiniciando"
    },
    {
        pat = "^my game crashed and i lost my buff$",
        rep = "Se me cerró el juego y perdí mi buff"
    },
    {
        pat = "^my game crashed (.+)$",
        rep = "Se me cerró el juego (crash) %1"
    },
    {
        pat = "^i got dc,? (.+)$",
        rep = "Me desconecté (DC), %1"
    },
    -- Tácticas y preguntas de combate
    {
        pat = "^why did you pull (.+) when (.+)$",
        rep = "¿Por qué puleaste a %1 cuando %2?"
    },
    {
        pat = "^why did you pull (.+)%??$",
        rep = "¿Por qué puleaste a %1?"
    },
    {
        pat = "^why did (.+) leave (?:the )?(?:group|party)%??$",
        rep = "¿Por qué se fue %1 del grupo?"
    },
    {
        pat = "^why did (.+) leave%??$",
        rep = "¿Por qué se fue %1?"
    },
    {
        pat = "^do we skip (.+)%??$",
        rep = "¿Saltamos a %1?"
    },
    {
        pat = "^kill (.+) first$",
        rep = "Maten a %1 primero"
    },
    {
        pat = "^focus (.+) first$",
        rep = "Enfoquen a %1 primero"
    },
    {
        pat = "^stack on (?:the )?(.+)$",
        rep = "Júntense en %1"
    },
    {
        pat = "^my (.+) is on cd$",
        rep = "Mi %1 está en enfriamiento (CD)"
    }
}

-- Función principal de coincidencia por plantilla sintáctica
function Engine.MatchTemplates(text)
    local lower = text:lower()
    for _, t in ipairs(SENTENCE_TEMPLATES) do
        local m1, m2 = lower:match(t.pat)
        if m1 and m2 then
            -- Traducir las variables capturadas si existen
            local t1 = Engine.TranslateSimplePhrase(m1)
            local t2 = Engine.TranslateSimplePhrase(m2)
            return t.rep:gsub("%%1", t1):gsub("%%2", t2)
        elseif m1 then
            local t1 = Engine.TranslateSimplePhrase(m1)
            return t.rep:gsub("%%1", t1)
        end
    end
    return nil
end

-- Traducción léxica palabra a palabra con reglas de inversión gramatical
function Engine.TranslateSimplePhrase(phrase)
    if not phrase or phrase == "" then return "" end
    local dict = WoWChatTranslatorData.GeneralDict or {}
    local slang = WoWChatTranslatorData.FastSlang or {}
    local dungeons = WoWChatTranslatorData.Dungeons or {}

    -- Tokenizar respetando espacios y puntuación básica
    local words = {}
    for word in phrase:gmatch("[%w']+|?[^%w%s]?") do
        table.insert(words, word)
    end

    local out = {}
    local i = 1
    while i <= #words do
        local w = words[i]
        local w_clean = w:lower():gsub("[%.,%?!']", "")

        -- Regla Sintáctica de Inversión: [Adjetivo] + [Sustantivo] -> [Sustantivo] [Adjetivo]
        -- Ejemplo: "blue key" -> "llave azul"
        local next_w = words[i + 1]
        local next_clean = next_w and next_w:lower():gsub("[%.,%?!']", "") or ""

        if ADJECTIVES_MAP[w_clean] and NOUNS_MAP[next_clean] then
            local adj_tr = ADJECTIVES_MAP[w_clean]
            local noun_tr = NOUNS_MAP[next_clean]
            table.insert(out, noun_tr .. " " .. adj_tr)
            i = i + 2
        else
            -- Búsqueda jerárquica: Dungeons -> Slang -> GeneralDict
            local tr = dungeons[w_clean] or slang[w_clean] or dict[w_clean]
            if tr then
                -- Si tiene opciones múltiples separadas por '/', tomar la primera más natural
                local first_choice = tr:match("^([^/]+)") or tr
                table.insert(out, first_choice:match("^%s*(.-)%s*$"))
            else
                table.insert(out, w)
            end
            i = i + 1
        end
    end

    local result = table.concat(out, " ")
    -- Limpieza de espacios antes de signos de puntuación
    result = result:gsub("%s+([%.,%?!])", "%1")
    return result
end

-- Función principal de traducción EN -> ES
function Engine.TranslateEnToEs(message)
    if not message or message == "" then return message end

    -- Preservar hipervínculos de WoW (|c...|Hitem:...|h[...]|h|r)
    local tokens = {}
    local token_idx = 0
    local protected = message:gsub("(|c%x+|H[^|]+|h%[[^%]]+%]%|h|r)", function(link)
        token_idx = token_idx + 1
        local key = "___WOWTOKEN_" .. token_idx .. "___"
        tokens[key] = link
        return key
    end)

    local clean = protected:match("^%s*(.-)%s*$")
    local lower = clean:lower()

    -- 1. Coincidencia exacta de jerga rápida
    if WoWChatTranslatorData.FastSlang[lower] then
        local res = WoWChatTranslatorData.FastSlang[lower]
        for k, v in pairs(tokens) do res = res:gsub(k, v) end
        return res
    end

    -- 2. Coincidencia de patrones compuestos de jerga
    if WoWChatTranslatorData.SlangPatterns then
        for _, entry in ipairs(WoWChatTranslatorData.SlangPatterns) do
            if lower:match(entry.pat) then
                local res = entry.rep
                for k, v in pairs(tokens) do res = res:gsub(k, v) end
                return res
            end
        end
    end

    -- 3. Normalizar contracciones (don't -> no, i'm -> estoy, etc.)
    local normalized = Engine.NormalizeContractions(clean)

    -- 4. Coincidencia por plantilla sintáctica de oraciones complejas
    local template_match = Engine.MatchTemplates(normalized)
    if template_match then
        for k, v in pairs(tokens) do template_match = template_match:gsub(k, v) end
        -- Capitalizar primera letra
        return template_match:sub(1, 1):upper() .. template_match:sub(2)
    end

    -- 5. Traducción léxico-gramatical general
    local translated = Engine.TranslateSimplePhrase(normalized)
    for k, v in pairs(tokens) do translated = translated:gsub(k, v) end

    -- Si el texto traducido es idéntico al original, no amerita mostrar subtítulo redundante
    if translated:lower() == clean:lower() then
        return nil
    end

    -- Capitalizar primera letra
    return translated:sub(1, 1):upper() .. translated:sub(2)
end

-- Función de traducción inversa ES -> EN para el comando /en <mensaje>
function Engine.TranslateEsToEn(message)
    if not message or message == "" then return message end
    local lower = message:lower():match("^%s*(.-)%s*$")
    local rev = WoWChatTranslatorData.ReverseDict or {}

    -- Coincidencia exacta en diccionario inverso
    if rev[lower] then
        return rev[lower]
    end

    -- Traducción aproximada de frases
    local out = {}
    for word in lower:gmatch("%S+") do
        local clean = word:gsub("[%.,%?!]", "")
        local tr = rev[clean]
        table.insert(out, tr or word)
    end
    return table.concat(out, " ")
end
