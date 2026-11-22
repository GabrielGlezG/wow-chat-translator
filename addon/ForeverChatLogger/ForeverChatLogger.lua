-- ForeverChatLogger: Mantiene /chatlog siempre activo y fuerza el vaciado en tiempo real para WoW Chat Translator

ForeverChatLoggerDB = ForeverChatLoggerDB or {}
ForeverChatLoggerDB.lastLoaded = date()
ForeverChatLoggerDB.loadCount = (ForeverChatLoggerDB.loadCount or 0) + 1
ForeverChatLoggerDB.flushCount = ForeverChatLoggerDB.flushCount or 0

local function EnsureChatLogging()
    if not LoggingChat() then
        LoggingChat(true)
        ForeverChatLoggerDB.lastToggledOn = date()
    end
end

-- Activar inmediatamente al cargar
EnsureChatLogging()

local frame = CreateFrame("Frame", "ForeverChatLoggerFrame")
frame:RegisterEvent("PLAYER_LOGIN")
frame:RegisterEvent("PLAYER_ENTERING_WORLD")
frame:RegisterEvent("ZONE_CHANGED_NEW_AREA")

local chatEvents = {
    "CHAT_MSG_WHISPER",
    "CHAT_MSG_BN_WHISPER",
    "CHAT_MSG_PARTY",
    "CHAT_MSG_PARTY_LEADER",
    "CHAT_MSG_RAID",
    "CHAT_MSG_RAID_LEADER",
    "CHAT_MSG_RAID_WARNING",
    "CHAT_MSG_GUILD",
    "CHAT_MSG_OFFICER",
    "CHAT_MSG_SAY",
    "CHAT_MSG_YELL",
}
for _, ev in ipairs(chatEvents) do
    frame:RegisterEvent(ev)
end

local isFlushing = false
local flushTimer = 0
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
        -- Fallback multiversión con OnUpdate para clientes WoW 3.3.5a sin C_Timer
        flushTimer = 0.20
        flushStep = 1
        timerFrame:SetScript("OnUpdate", function(self, elapsed)
            flushTimer = flushTimer - elapsed
            if flushTimer <= 0 then
                if flushStep == 1 then
                    LoggingChat(false)
                    flushStep = 2
                    flushTimer = 0.05
                elseif flushStep == 2 then
                    LoggingChat(true)
                    isFlushing = false
                    flushStep = 0
                    self:SetScript("OnUpdate", nil)
                end
            end
        end)
    end
end

local hasAnnounced = false
frame:SetScript("OnEvent", function(self, event, ...)
    if event == "PLAYER_LOGIN" or event == "PLAYER_ENTERING_WORLD" or event == "ZONE_CHANGED_NEW_AREA" then
        EnsureChatLogging()
        if (event == "PLAYER_ENTERING_WORLD" or event == "PLAYER_LOGIN") and not hasAnnounced then
            hasAnnounced = true
            if DEFAULT_CHAT_FRAME then
                DEFAULT_CHAT_FRAME:AddMessage("|cff00e5ff[WoW Chat Translator]|r Addon activo (/chatlog ON). Escribe |cffFFD100/translator|r para ayuda.")
            end
        end
        return
    end

    FlushLogToDisk()
end)

SLASH_FOREVERCHATLOGGER1 = "/chatlogon"
SlashCmdList["FOREVERCHATLOGGER"] = function()
    LoggingChat(true)
    DEFAULT_CHAT_FRAME:AddMessage("|cff00ff00[WoW Chat Translator]|r /chatlog activado.")
end

SLASH_FOREVERCHATFLUSH1 = "/chatflush"
SlashCmdList["FOREVERCHATFLUSH"] = function()
    FlushLogToDisk()
    DEFAULT_CHAT_FRAME:AddMessage("|cff00ff00[WoW Chat Translator]|r Chat log vaciado a disco.")
end

SLASH_WOWCHATTRANSLATOR1 = "/translator"
SLASH_WOWCHATTRANSLATOR2 = "/fcl"
SlashCmdList["WOWCHATTRANSLATOR"] = function(msg)
    local cmd = (msg or ""):lower():match("^%s*(%S*)")
    if cmd == "on" then
        LoggingChat(true)
        DEFAULT_CHAT_FRAME:AddMessage("|cff00ff00[WoW Chat Translator]|r /chatlog forzado a ENCENDIDO.")
    elseif cmd == "off" then
        LoggingChat(false)
        DEFAULT_CHAT_FRAME:AddMessage("|cffff0000[WoW Chat Translator]|r /chatlog APAGADO.")
    elseif cmd == "flush" then
        FlushLogToDisk()
        DEFAULT_CHAT_FRAME:AddMessage("|cff00ff00[WoW Chat Translator]|r Vaciado manual completado.")
    else
        local statusColor = LoggingChat() and "|cff00ff00ACTIVO|r" or "|cffff0000INACTIVO|r"
        DEFAULT_CHAT_FRAME:AddMessage("|cff00e5ff=== WoW Chat Translator (ForeverChatLogger) ===|r")
        DEFAULT_CHAT_FRAME:AddMessage(" Estado del logger: " .. statusColor .. " | Cargas: " .. (ForeverChatLoggerDB.loadCount or 1))
        DEFAULT_CHAT_FRAME:AddMessage(" Vaciados automáticos a disco: " .. (ForeverChatLoggerDB.flushCount or 0))
        DEFAULT_CHAT_FRAME:AddMessage(" Comandos disponibles:")
        DEFAULT_CHAT_FRAME:AddMessage("   |cffFFD100/translator status|r - Muestra este estado")
        DEFAULT_CHAT_FRAME:AddMessage("   |cffFFD100/translator flush|r  - Fuerza vaciado inmediato a disco")
        DEFAULT_CHAT_FRAME:AddMessage("   |cffFFD100/translator on/off|r - Enciende o apaga el logging")
    end
end
