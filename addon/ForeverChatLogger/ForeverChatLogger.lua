--[[
    ForeverChatLogger.lua - Addon oficial de WoW Chat Translator.
    Integración completa con el motor y catálogo lingüístico de Pirson (WoW Translator v2.17).
    1. Traducción en tiempo real 100% nativa en el chat de WoW (Inglés <-> Español).
    2. Motor de plantillas semánticas para oraciones completas y anotaciones de jerga.
    3. Vaciado debounced de /chatlog a disco cada 0.20s para la app de escritorio acompañante.
    Compatible con WoW Forever, WotLK 3.3.5a, Classic y Retail.
]]

local ADDON_NAME, addonTable = ...
addonTable = addonTable or WoWTranslatorNS

-- ==============================================================================
-- VACIADO DE CHATLOG A DISCO (Debounced 0.20s para la app de escritorio)
-- ==============================================================================
local isFlushing = false
local flushStep = 0
local timerFrame = CreateFrame("Frame")

local function FlushLogToDisk()
    if isFlushing then return end
    isFlushing = true

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
addonTable.FlushLogToDisk = FlushLogToDisk

-- ==============================================================================
-- ASEGURAR CHATLOG ENCENDIDO
-- ==============================================================================
local function EnsureChatLogging()
    if not LoggingChat() then
        LoggingChat(true)
    end
end

-- ==============================================================================
-- COMANDOS /en y /ingles PARA RESPONDER EN INGLÉS GAMER
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
    if addonTable.TranslateOutgoing then
        english = addonTable.TranslateOutgoing(msg)
    end

    if chatFrame then
        chatFrame:AddMessage("|cff00e5ff[WoW Chat Translator]|r Traducción EN: |cfffff0c0" .. english .. "|r")
    end

    -- Colocar de forma segura en la caja de texto para que el usuario solo pulse Enter
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

-- ==============================================================================
-- COMANDOS /translator y /fcl (Alias de control)
-- ==============================================================================
SLASH_WOWCHATTRANSLATOR1 = "/translator"
SLASH_WOWCHATTRANSLATOR2 = "/fcl"
SlashCmdList["WOWCHATTRANSLATOR"] = function(msg)
    local cmd, arg = (msg or ""):match("^%s*(%S+)%s*(.-)%s*$")
    cmd = (cmd or ""):lower()
    local chatFrame = SELECTED_CHAT_FRAME or DEFAULT_CHAT_FRAME or ChatFrame1

    if cmd == "test" then
        if SlashCmdList["WOWTRANSLATOR"] then
            SlashCmdList["WOWTRANSLATOR"]("test")
        end
    elseif cmd == "config" or cmd == "options" or cmd == "menu" then
        if SlashCmdList["WOWTRANSLATOR"] then
            SlashCmdList["WOWTRANSLATOR"]("config")
        end
    elseif cmd == "flush" then
        FlushLogToDisk()
        chatFrame:AddMessage("|cff00ff00[WoW Chat Translator]|r Vaciado manual de chat log completado.")
    elseif cmd == "on" then
        if SlashCmdList["WOWTRANSLATOR"] then
            SlashCmdList["WOWTRANSLATOR"]("on")
        end
    elseif cmd == "off" then
        if SlashCmdList["WOWTRANSLATOR"] then
            SlashCmdList["WOWTRANSLATOR"]("off")
        end
    else
        chatFrame:AddMessage("|cff00e5ff=== WoW Chat Translator v2.0.0 ===|r")
        chatFrame:AddMessage(" Motor lingüístico y diccionarios de Pirson integrados con plantillas y jerga.")
        chatFrame:AddMessage(" Comandos disponibles:")
        chatFrame:AddMessage("   |cffFFD100/translator config|r o |cffFFD100/wt config|r - Abre el panel visual de opciones")
        chatFrame:AddMessage("   |cffFFD100/translator test|r - Prueba de traducción en vivo en el chat")
        chatFrame:AddMessage("   |cffFFD100/en <texto>|r - Traduce de español a inglés y lo coloca en la caja de chat")
        chatFrame:AddMessage("   |cffFFD100/translator on / off|r - Activa o desactiva la traducción")
        chatFrame:AddMessage("   |cffFFD100/translator flush|r - Fuerza vaciado a disco")
    end
end

-- ==============================================================================
-- EVENT HOOKS DE ARRANQUE
-- ==============================================================================
local initFrame = CreateFrame("Frame")
initFrame:RegisterEvent("PLAYER_LOGIN")
initFrame:RegisterEvent("PLAYER_ENTERING_WORLD")
local announced = false

initFrame:SetScript("OnEvent", function(self, event)
    EnsureChatLogging()
    if not announced and (event == "PLAYER_LOGIN" or event == "PLAYER_ENTERING_WORLD") then
        announced = true
        local chatFrame = SELECTED_CHAT_FRAME or DEFAULT_CHAT_FRAME or ChatFrame1
        if chatFrame then
            chatFrame:AddMessage("|cff00e5ff[WoW Chat Translator]|r v2.0.0 activo (Motor Pirson integrado). Escribe |cffFFD100/translator|r, |cffFFD100/wt|r o |cffFFD100/en <texto>|r.")
        end
    end
end)
