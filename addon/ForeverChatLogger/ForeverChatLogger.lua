--[[
    ForeverChatLogger.lua - Addon oficial de WoW Chat Translator.
    1. Traducción en tiempo real 100% nativa en el chat de WoW (Inglés <-> Español).
    2. Vaciado debounced de /chatlog a disco cada 0.20s para la app de escritorio acompañante.
    Compatible con WoW Forever, WotLK 3.3.5a, Classic y Retail.
]]

ForeverChatLoggerDB = ForeverChatLoggerDB or {}
ForeverChatLoggerDB.lastLoaded = date()
ForeverChatLoggerDB.loadCount = (ForeverChatLoggerDB.loadCount or 0) + 1
ForeverChatLoggerDB.flushCount = ForeverChatLoggerDB.flushCount or 0
if ForeverChatLoggerDB.inlineEnabled == nil then
    ForeverChatLoggerDB.inlineEnabled = true
end

local function EnsureChatLogging()
    if not LoggingChat() then
        LoggingChat(true)
    end
end

local frame = CreateFrame("Frame")
frame:RegisterEvent("PLAYER_LOGIN")
frame:RegisterEvent("PLAYER_ENTERING_WORLD")
frame:RegisterEvent("ZONE_CHANGED_NEW_AREA")
frame:RegisterEvent("CHAT_MSG_PARTY")
frame:RegisterEvent("CHAT_MSG_PARTY_LEADER")
frame:RegisterEvent("CHAT_MSG_RAID")
frame:RegisterEvent("CHAT_MSG_RAID_LEADER")
frame:RegisterEvent("CHAT_MSG_RAID_WARNING")
frame:RegisterEvent("CHAT_MSG_WHISPER")
frame:RegisterEvent("CHAT_MSG_GUILD")
frame:RegisterEvent("CHAT_MSG_OFFICER")
frame:RegisterEvent("CHAT_MSG_SAY")
frame:RegisterEvent("CHAT_MSG_YELL")

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

-- Vaciado suave (debounced) de /chatlog a disco
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

-- Procesa e inyecta la traducción en el chat nativo de WoW
local function HandleIncomingChatMessage(msg, sender)
    if not ForeverChatLoggerDB.inlineEnabled then return end
    if not msg or msg == "" then return end

    -- Ignorar mensajes propios
    local myName = UnitName("player")
    if sender and myName and (sender == myName or sender:find("^" .. myName)) then
        return
    end

    if IsAlreadySpanishOrIgnored(msg) then return end

    if WoWChatTranslatorEngine and WoWChatTranslatorEngine.TranslateEnToEs then
        local translation = WoWChatTranslatorEngine.TranslateEnToEs(msg)
        if translation and translation ~= "" and DEFAULT_CHAT_FRAME then
            DEFAULT_CHAT_FRAME:AddMessage("|cff00e5ff  └── [ES] |r|cfffff0c0" .. translation .. "|r")
        end
    end
end

local hasAnnounced = false
frame:SetScript("OnEvent", function(self, event, ...)
    if event == "PLAYER_LOGIN" or event == "PLAYER_ENTERING_WORLD" or event == "ZONE_CHANGED_NEW_AREA" then
        EnsureChatLogging()
        if (event == "PLAYER_ENTERING_WORLD" or event == "PLAYER_LOGIN") and not hasAnnounced then
            hasAnnounced = true
            if DEFAULT_CHAT_FRAME then
                DEFAULT_CHAT_FRAME:AddMessage("|cff00e5ff[WoW Chat Translator]|r Addon activo. Traducción en chat: |cff00ff00ACTIVADA|r. Escribe |cffFFD100/translator|r o |cffFFD100/en <texto>|r.")
            end
        end
        return
    end

    -- Eventos de chat entrantes
    if event:sub(1, 9) == "CHAT_MSG_" then
        local msg, sender = ...
        HandleIncomingChatMessage(msg, sender)
        FlushLogToDisk()
    end
end)

-- Comandos /translator y /fcl
SLASH_WOWCHATTRANSLATOR1 = "/translator"
SLASH_WOWCHATTRANSLATOR2 = "/fcl"
SlashCmdList["WOWCHATTRANSLATOR"] = function(msg)
    local cmd, arg = (msg or ""):match("^%s*(%S+)%s*(.-)%s*$")
    cmd = (cmd or ""):lower()

    if cmd == "test" then
        DEFAULT_CHAT_FRAME:AddMessage("|cff00e5ff=== Demostración de Traducción In-Game ===|r")
        local testCases = {
            "wait sec, healer oom, dont pull yet",
            "can someone tell me where the exit is?",
            "my computer is having issues and restarting",
            "why did you pull that dragon when the healer was eating?",
            "anyone need this item or can i greed?"
        }
        for _, orig in ipairs(testCases) do
            local tr = WoWChatTranslatorEngine.TranslateEnToEs(orig)
            DEFAULT_CHAT_FRAME:AddMessage("|cffA8C8FF[Inglés]:|r " .. orig)
            DEFAULT_CHAT_FRAME:AddMessage("|cff00e5ff  └── [ES]:|r |cfffff0c0" .. (tr or orig) .. "|r")
        end

    elseif cmd == "inline" then
        local sub = (arg or ""):lower()
        if sub == "on" then
            ForeverChatLoggerDB.inlineEnabled = true
            DEFAULT_CHAT_FRAME:AddMessage("|cff00ff00[WoW Chat Translator]|r Subtítulos de traducción en el chat: ENCENDIDOS.")
        elseif sub == "off" then
            ForeverChatLoggerDB.inlineEnabled = false
            DEFAULT_CHAT_FRAME:AddMessage("|cffff0000[WoW Chat Translator]|r Subtítulos de traducción en el chat: APAGADOS.")
        else
            ForeverChatLoggerDB.inlineEnabled = not ForeverChatLoggerDB.inlineEnabled
            local st = ForeverChatLoggerDB.inlineEnabled and "|cff00ff00ENCENDIDOS|r" or "|cffff0000APAGADOS|r"
            DEFAULT_CHAT_FRAME:AddMessage("|cff00e5ff[WoW Chat Translator]|r Subtítulos de traducción: " .. st)
        end

    elseif cmd == "flush" then
        FlushLogToDisk()
        DEFAULT_CHAT_FRAME:AddMessage("|cff00ff00[WoW Chat Translator]|r Vaciado manual de chat log completado.")

    elseif cmd == "on" then
        LoggingChat(true)
        DEFAULT_CHAT_FRAME:AddMessage("|cff00ff00[WoW Chat Translator]|r /chatlog forzado a ENCENDIDO.")

    elseif cmd == "off" then
        LoggingChat(false)
        DEFAULT_CHAT_FRAME:AddMessage("|cffff0000[WoW Chat Translator]|r /chatlog APAGADO.")

    else
        local statusColor = LoggingChat() and "|cff00ff00ACTIVO|r" or "|cffff0000INACTIVO|r"
        local inlineColor = ForeverChatLoggerDB.inlineEnabled and "|cff00ff00ACTIVO|r" or "|cffff0000INACTIVO|r"
        DEFAULT_CHAT_FRAME:AddMessage("|cff00e5ff=== WoW Chat Translator v1.1.0 ===|r")
        DEFAULT_CHAT_FRAME:AddMessage(" Traductor en chat (Subtítulos): " .. inlineColor)
        DEFAULT_CHAT_FRAME:AddMessage(" Logger a disco (/chatlog): " .. statusColor .. " | Vaciados: " .. (ForeverChatLoggerDB.flushCount or 0))
        DEFAULT_CHAT_FRAME:AddMessage(" Comandos disponibles:")
        DEFAULT_CHAT_FRAME:AddMessage("   |cffFFD100/translator test|r - Prueba de traducción en vivo en el chat")
        DEFAULT_CHAT_FRAME:AddMessage("   |cffFFD100/translator inline on/off|r - Enciende o apaga el subtítulo en el chat")
        DEFAULT_CHAT_FRAME:AddMessage("   |cffFFD100/en <texto>|r o |cffFFD100/ingles <texto>|r - Traduce de español a inglés para responder")
        DEFAULT_CHAT_FRAME:AddMessage("   |cffFFD100/translator flush|r - Fuerza vaciado a disco")
    end
end

-- Comando /en y /ingles para responder en inglés gamer
SLASH_WOWCHATTRANSLATOREN1 = "/en"
SLASH_WOWCHATTRANSLATOREN2 = "/ingles"
SlashCmdList["WOWCHATTRANSLATOREN"] = function(msg)
    if not msg or msg == "" then
        DEFAULT_CHAT_FRAME:AddMessage("|cffFFD100Uso:|r /en <tu mensaje en español>")
        DEFAULT_CHAT_FRAME:AddMessage("Ejemplo: |cfffff0c0/en esperen un momento no puleen todavia|r")
        return
    end

    if WoWChatTranslatorEngine and WoWChatTranslatorEngine.TranslateEsToEn then
        local english = WoWChatTranslatorEngine.TranslateEsToEn(msg)
        
        -- Si hay una caja de chat abierta, colocar el texto traducido para que el jugador lo confirme con Enter
        if ChatFrame1EditBox and ChatFrame1EditBox:IsVisible() then
            ChatFrame1EditBox:SetText(english)
            ChatFrame1EditBox:SetFocus()
        else
            -- Si no está abierta, abrir la caja de texto con el mensaje en inglés listo para enviar
            ChatFrame_OpenChat(english, DEFAULT_CHAT_FRAME)
        end
        DEFAULT_CHAT_FRAME:AddMessage("|cff00e5ff[WoW Chat Translator]|r Traducido al inglés: |cfffff0c0" .. english .. "|r (Pulsa Enter para enviar)")
    end
end
