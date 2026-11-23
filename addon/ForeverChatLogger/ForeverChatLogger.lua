--[[
    ForeverChatLogger.lua - Addon oficial de WoW Chat Translator.
    1. Traducción en tiempo real 100% nativa en el chat de WoW (Inglés <-> Español).
    2. Vaciado debounced de /chatlog a disco cada 0.20s para la app de escritorio acompañante.
    Compatible con WoW Forever, WotLK 3.3.5a, Classic y Retail.
]]

ForeverChatLoggerDB = ForeverChatLoggerDB or {}
if ForeverChatLoggerDB.inlineEnabled == nil then
    ForeverChatLoggerDB.inlineEnabled = true
end

-- Lista exhaustiva de canales de chat relevantes
local CHAT_EVENTS = {
    "CHAT_MSG_SAY",
    "CHAT_MSG_YELL",
    "CHAT_MSG_WHISPER",
    "CHAT_MSG_PARTY",
    "CHAT_MSG_PARTY_LEADER",
    "CHAT_MSG_RAID",
    "CHAT_MSG_RAID_LEADER",
    "CHAT_MSG_RAID_WARNING",
    "CHAT_MSG_INSTANCE_CHAT",
    "CHAT_MSG_INSTANCE_CHAT_LEADER",
    "CHAT_MSG_GUILD",
    "CHAT_MSG_OFFICER",
}

-- Función para verificar si la traducción inline está activa
local function IsInlineEnabled()
    if ForeverChatLoggerDB and ForeverChatLoggerDB.inlineEnabled == false then
        return false
    end
    return true
end

local function EnsureChatLogging()
    if not LoggingChat() then
        LoggingChat(true)
    end
end

-- Detector de texto que ya está en español o no requiere traducción
local function IsAlreadySpanishOrIgnored(text)
    if not text or text == "" then return true end
    local lower = " " .. text:lower() .. " "

    -- Saludos o palabras inconfundibles de español
    if lower:find(" hola ") or lower:find(" wenas ") or lower:find(" buenas ") or
       lower:find(" gracias ") or lower:find(" terminamos ") or lower:find(" jaja") or
       lower:find(" por favor ") or lower:find(" tengo ") or lower:find(" estoy ") or
       lower:find(" alguien ") or lower:find(" donde ") or lower:find(" ayuda ") or
       lower:find(" quien ") or lower:find(" vamos ") or lower:find(" esperar ") then
        return true
    end

    -- Mensajes de sistema, tiradas de dados o alertas numéricas
    if text:match("^%d+$") or text:match("^%s*Roll%s*%-") or text:match("ha seleccionado") then
        return true
    end

    return false
end

-- ==============================================================================
-- FILTRADO E INYECCIÓN DE TRADUCCIÓN IN-GAME (ChatFrame_AddMessageEventFilter)
-- ==============================================================================
local useFilterAPI = false

local function ChatTranslationFilter(self, event, msg, sender, ...)
    if not IsInlineEnabled() then
        return false, msg, sender, ...
    end
    if not msg or msg == "" then
        return false, msg, sender, ...
    end

    -- Ignorar si ya está en español
    if IsAlreadySpanishOrIgnored(msg) then
        return false, msg, sender, ...
    end

    if WoWChatTranslatorEngine and WoWChatTranslatorEngine.TranslateEnToEs then
        local ok, translation = pcall(WoWChatTranslatorEngine.TranslateEnToEs, msg)
        if ok and translation and translation ~= "" then
            -- Adjuntar subtítulo limpio en cyan/dorado directamente bajo el mensaje
            local decorated = msg .. "\n|cff00e5ff  └── [ES] |r|cfffff0c0" .. translation .. "|r"
            return false, decorated, sender, ...
        end
    end

    return false, msg, sender, ...
end

-- Intentar registrar mediante la API estándar de Blizzard
if ChatFrame_AddMessageEventFilter then
    for _, evt in ipairs(CHAT_EVENTS) do
        local ok = pcall(ChatFrame_AddMessageEventFilter, evt, ChatTranslationFilter)
        if ok then
            useFilterAPI = true
        end
    end
end

-- ==============================================================================
-- VACIADO DE CHATLOG A DISCO (Debounced 0.20s)
-- ==============================================================================
local isFlushing = false
local flushStep = 0
local timerFrame = CreateFrame("Frame")

local function FlushLogToDisk()
    if isFlushing then return end
    isFlushing = true
    ForeverChatLoggerDB.flushCount = (ForeverChatLoggerDB.flushCount or 0) + 1

    if C_Timer and C_Timer.After then
        C_Timer.After(0.20, function()
            LoggingChat(false)
            C_Timer.After(0.05, function()
                LoggingChat(true)
                isFlushing = false
            end)
        end)
    else
        flushStep = 1
        local elapsed = 0
        timerFrame:SetScript("OnUpdate", function(self, dt)
            elapsed = elapsed + dt
            if flushStep == 1 and elapsed >= 0.20 then
                LoggingChat(false)
                flushStep = 2
                elapsed = 0
            elseif flushStep == 2 and elapsed >= 0.05 then
                LoggingChat(true)
                isFlushing = false
                flushStep = 0
                self:SetScript("OnUpdate", nil)
            end
        end)
    end
end

-- Fallback para clientes que no soportan ChatFrame_AddMessageEventFilter
local function HandleIncomingChatMessageFallback(msg, sender)
    if not IsInlineEnabled() then return end
    if not msg or msg == "" then return end
    if IsAlreadySpanishOrIgnored(msg) then return end

    if WoWChatTranslatorEngine and WoWChatTranslatorEngine.TranslateEnToEs then
        local ok, translation = pcall(WoWChatTranslatorEngine.TranslateEnToEs, msg)
        if ok and translation and translation ~= "" then
            local chatFrame = SELECTED_CHAT_FRAME or DEFAULT_CHAT_FRAME
            if chatFrame then
                chatFrame:AddMessage("|cff00e5ff  └── [ES] |r|cfffff0c0" .. translation .. "|r")
            end
        end
    end
end

-- ==============================================================================
-- EVENT FRAME PRINCIPAL
-- ==============================================================================
local frame = CreateFrame("Frame")
frame:RegisterEvent("ADDON_LOADED")
frame:RegisterEvent("PLAYER_LOGIN")
frame:RegisterEvent("PLAYER_ENTERING_WORLD")
frame:RegisterEvent("ZONE_CHANGED_NEW_AREA")

-- Registrar eventos de chat para vaciado a disco (y fallback de traducción si no hay filter API)
for _, evt in ipairs(CHAT_EVENTS) do
    frame:RegisterEvent(evt)
end

local hasAnnounced = false
frame:SetScript("OnEvent", function(self, event, ...)
    if event == "ADDON_LOADED" then
        local addon = ...
        if addon == "ForeverChatLogger" then
            ForeverChatLoggerDB = ForeverChatLoggerDB or {}
            if ForeverChatLoggerDB.inlineEnabled == nil then
                ForeverChatLoggerDB.inlineEnabled = true
            end
            ForeverChatLoggerDB.loadCount = (ForeverChatLoggerDB.loadCount or 0) + 1
            ForeverChatLoggerDB.lastLoaded = date()
        end
        return
    end

    if event == "PLAYER_LOGIN" or event == "PLAYER_ENTERING_WORLD" or event == "ZONE_CHANGED_NEW_AREA" then
        EnsureChatLogging()
        if (event == "PLAYER_ENTERING_WORLD" or event == "PLAYER_LOGIN") and not hasAnnounced then
            hasAnnounced = true
            local targetFrame = SELECTED_CHAT_FRAME or DEFAULT_CHAT_FRAME
            if targetFrame then
                targetFrame:AddMessage("|cff00e5ff[WoW Chat Translator]|r Addon activo. Traducción en chat: |cff00ff00ACTIVADA|r. Escribe |cffFFD100/translator test|r o |cffFFD100/en <texto>|r.")
            end
        end
        return
    end

    -- Eventos de chat entrantes
    if event:sub(1, 9) == "CHAT_MSG_" then
        local msg, sender = ...
        if not useFilterAPI then
            HandleIncomingChatMessageFallback(msg, sender)
        end
        FlushLogToDisk()
    end
end)

-- ==============================================================================
-- COMANDOS SLASH: /translator y /fcl
-- ==============================================================================
SLASH_WOWCHATTRANSLATOR1 = "/translator"
SLASH_WOWCHATTRANSLATOR2 = "/fcl"
SlashCmdList["WOWCHATTRANSLATOR"] = function(msg)
    local cmd, arg = (msg or ""):match("^%s*(%S+)%s*(.-)%s*$")
    cmd = (cmd or ""):lower()
    local chatFrame = SELECTED_CHAT_FRAME or DEFAULT_CHAT_FRAME or ChatFrame1

    if cmd == "test" then
        chatFrame:AddMessage("|cff00e5ff=== Demostración de Traducción In-Game ===|r")
        local testCases = {
            "wait sec, healer oom, dont pull yet",
            "can someone tell me where the exit is?",
            "my computer is having issues and restarting",
            "watch out for tail swipe",
            "anyone need this item or can i greed?"
        }
        for _, orig in ipairs(testCases) do
            local tr = nil
            if WoWChatTranslatorEngine and WoWChatTranslatorEngine.TranslateEnToEs then
                local ok, res = pcall(WoWChatTranslatorEngine.TranslateEnToEs, orig)
                if ok then tr = res end
            end
            chatFrame:AddMessage("|cffA8C8FF[Inglés]:|r " .. orig)
            chatFrame:AddMessage("|cff00e5ff  └── [ES]:|r |cfffff0c0" .. (tr or orig) .. "|r")
        end

    elseif cmd == "inline" then
        local sub = (arg or ""):lower()
        if sub == "on" then
            ForeverChatLoggerDB.inlineEnabled = true
            chatFrame:AddMessage("|cff00ff00[WoW Chat Translator]|r Subtítulos de traducción en el chat: ENCENDIDOS.")
        elseif sub == "off" then
            ForeverChatLoggerDB.inlineEnabled = false
            chatFrame:AddMessage("|cffff0000[WoW Chat Translator]|r Subtítulos de traducción en el chat: APAGADOS.")
        else
            ForeverChatLoggerDB.inlineEnabled = not IsInlineEnabled()
            local st = IsInlineEnabled() and "|cff00ff00ENCENDIDOS|r" or "|cffff0000APAGADOS|r"
            chatFrame:AddMessage("|cff00e5ff[WoW Chat Translator]|r Subtítulos de traducción: " .. st)
        end

    elseif cmd == "flush" then
        FlushLogToDisk()
        chatFrame:AddMessage("|cff00ff00[WoW Chat Translator]|r Vaciado manual de chat log completado.")

    elseif cmd == "on" then
        LoggingChat(true)
        chatFrame:AddMessage("|cff00ff00[WoW Chat Translator]|r /chatlog forzado a ENCENDIDO.")

    elseif cmd == "off" then
        LoggingChat(false)
        chatFrame:AddMessage("|cffff0000[WoW Chat Translator]|r /chatlog APAGADO.")

    else
        local statusColor = LoggingChat() and "|cff00ff00ACTIVO|r" or "|cffff0000INACTIVO|r"
        local inlineColor = IsInlineEnabled() and "|cff00ff00ACTIVO|r" or "|cffff0000INACTIVO|r"
        chatFrame:AddMessage("|cff00e5ff=== WoW Chat Translator v1.1.0 ===|r")
        chatFrame:AddMessage(" Traductor en chat (Subtítulos): " .. inlineColor)
        chatFrame:AddMessage(" Logger a disco (/chatlog): " .. statusColor .. " | Vaciados: " .. (ForeverChatLoggerDB.flushCount or 0))
        chatFrame:AddMessage(" Comandos disponibles:")
        chatFrame:AddMessage("   |cffFFD100/translator test|r - Prueba de traducción en vivo en el chat")
        chatFrame:AddMessage("   |cffFFD100/translator inline on/off|r - Enciende o apaga el subtítulo en el chat")
        chatFrame:AddMessage("   |cffFFD100/en <texto>|r o |cffFFD100/ingles <texto>|r - Traduce de español a inglés para responder")
        chatFrame:AddMessage("   |cffFFD100/translator flush|r - Fuerza vaciado a disco")
    end
end

-- ==============================================================================
-- COMANDO /en y /ingles PARA RESPONDER EN INGLÉS GAMER
-- ==============================================================================
SLASH_WOWCHATTRANSLATOREN1 = "/en"
SLASH_WOWCHATTRANSLATOREN2 = "/ingles"
SlashCmdList["WOWCHATTRANSLATOREN"] = function(msg)
    local chatFrame = SELECTED_CHAT_FRAME or DEFAULT_CHAT_FRAME or ChatFrame1

    if not msg or msg == "" then
        if chatFrame then
            chatFrame:AddMessage("|cff00e5ff[WoW Chat Translator]|r |cffFFD100Uso:|r /en <tu mensaje en español>")
            chatFrame:AddMessage("Ejemplo: |cfffff0c0/en esperen sanador sin mana no puleen todavia|r")
        end
        return
    end

    local english = msg
    if WoWChatTranslatorEngine and WoWChatTranslatorEngine.TranslateEsToEn then
        local ok, result = pcall(WoWChatTranslatorEngine.TranslateEsToEn, msg)
        if ok and result and result ~= "" then
            english = result
        end
    end

    -- 1. Siempre mostrar la traducción resultante en el chat local
    if chatFrame then
        chatFrame:AddMessage("|cff00e5ff[WoW Chat Translator]|r Traducción EN: |cfffff0c0" .. english .. "|r")
    end

    -- 2. Activar la caja de texto con el mensaje en inglés listo para confirmar con Enter
    local editBox = nil
    if ChatEdit_GetActiveWindow then
        editBox = ChatEdit_GetActiveWindow()
    end
    if not editBox and ChatEdit_GetLastActiveWindow then
        editBox = ChatEdit_GetLastActiveWindow()
    end
    if not editBox then
        editBox = ChatFrame1EditBox or ChatFrameEditBox
    end

    if editBox then
        if ChatEdit_ActivateChat then
            pcall(ChatEdit_ActivateChat, editBox)
        else
            pcall(function() editBox:Show() end)
        end
        pcall(function()
            editBox:SetText(english)
            editBox:SetFocus()
            if editBox.HighlightText then
                editBox:HighlightText()
            end
        end)
    elseif ChatFrame_OpenChat then
        pcall(ChatFrame_OpenChat, english, DEFAULT_CHAT_FRAME)
    end
end
