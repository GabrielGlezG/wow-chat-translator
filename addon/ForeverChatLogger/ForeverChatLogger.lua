--[[
    ForeverChatLogger.lua - Addon oficial de WoW Chat Translator.
    Integración completa con el motor y catálogo lingüístico de Pirson (WoW Translator v2.17).
    1. Pestaña dedicada "Traductor" integrada en la ventana de chat nativa de WoW.
    2. Traducción limpia de oraciones completas con plantillas y jerga (sin paréntesis molestos).
    3. Respuestas salientes /en y /ingles con traducción inversa a inglés gamer.
    4. Vaciado debounced de /chatlog a disco cada 0.20s para la app de escritorio acompañante.
    Compatible con WoW Forever, WotLK 3.3.5a, Classic y Retail.
]]

local ADDON_NAME, addonTable = ...
addonTable = addonTable or WoWTranslatorNS

-- ==============================================================================
-- 1. PESTAÑA INTEGRADA "TRADUCTOR" EN EL CHAT DE WOW
-- ==============================================================================
local TRANSLATOR_TAB_NAME = "Traductor"

local CHANNEL_COLORS = {
    ["CHAT_MSG_PARTY"]                  = "|cffaaaaff",
    ["CHAT_MSG_PARTY_LEADER"]           = "|cff8888ff",
    ["CHAT_MSG_RAID"]                   = "|cffff7f00",
    ["CHAT_MSG_RAID_LEADER"]            = "|cffff7f00",
    ["CHAT_MSG_RAID_WARNING"]           = "|cffff4800",
    ["CHAT_MSG_INSTANCE_CHAT"]          = "|cffffa040",
    ["CHAT_MSG_INSTANCE_CHAT_LEADER"]   = "|cffffa040",
    ["CHAT_MSG_WHISPER"]                = "|cffff80ff",
    ["CHAT_MSG_WHISPER_INFORM"]         = "|cffff80ff",
    ["CHAT_MSG_BN_WHISPER"]             = "|cff00ffff",
    ["CHAT_MSG_BN_WHISPER_INFORM"]      = "|cff00ffff",
    ["CHAT_MSG_GUILD"]                  = "|cff40ff40",
    ["CHAT_MSG_OFFICER"]                = "|cff40c040",
    ["CHAT_MSG_SAY"]                    = "|cffffffff",
    ["CHAT_MSG_YELL"]                   = "|cffff4040",
    ["CHAT_MSG_EMOTE"]                  = "|cffff8040",
}

local CHANNEL_TAGS = {
    ["CHAT_MSG_PARTY"]                  = "[Grupo]",
    ["CHAT_MSG_PARTY_LEADER"]           = "[Líder Grupo]",
    ["CHAT_MSG_RAID"]                   = "[Banda]",
    ["CHAT_MSG_RAID_LEADER"]            = "[Líder Banda]",
    ["CHAT_MSG_RAID_WARNING"]           = "[Alerta Banda]",
    ["CHAT_MSG_INSTANCE_CHAT"]          = "[Instancia]",
    ["CHAT_MSG_INSTANCE_CHAT_LEADER"]   = "[Líder Instancia]",
    ["CHAT_MSG_WHISPER"]                = "[Susurro de]",
    ["CHAT_MSG_WHISPER_INFORM"]         = "[Para]",
    ["CHAT_MSG_BN_WHISPER"]             = "[BNet de]",
    ["CHAT_MSG_BN_WHISPER_INFORM"]      = "[BNet Para]",
    ["CHAT_MSG_GUILD"]                  = "[Hermandad]",
    ["CHAT_MSG_OFFICER"]                = "[Oficiales]",
    ["CHAT_MSG_SAY"]                    = "[Decir]",
    ["CHAT_MSG_YELL"]                   = "[Grito]",
    ["CHAT_MSG_EMOTE"]                  = "[Emoción]",
}

function addonTable.GetTranslatorChatFrame()
    local numWindows = NUM_CHAT_WINDOWS or 10
    for i = 1, numWindows do
        local name = GetChatWindowInfo(i)
        if name == TRANSLATOR_TAB_NAME then
            return _G["ChatFrame" .. i]
        end
    end
    return nil
end

function addonTable.EnsureTranslatorTab()
    local existing = addonTable.GetTranslatorChatFrame()
    if existing then return existing end

    if FCF_OpenNewWindow then
        local newFrame, name = FCF_OpenNewWindow(TRANSLATOR_TAB_NAME)
        if newFrame then
            -- Quitar todos los grupos de canales por defecto para que la pestaña no reciba spam no traducido
            if ChatFrame_RemoveAllMessageGroups then
                ChatFrame_RemoveAllMessageGroups(newFrame)
            end
            if ChatFrame_RemoveAllChannels then
                ChatFrame_RemoveAllChannels(newFrame)
            end
            -- Mantener la pestaña principal (General) seleccionada por defecto
            if FCF_SelectDockFrame and DEFAULT_CHAT_FRAME then
                FCF_SelectDockFrame(DEFAULT_CHAT_FRAME)
            end
            return newFrame
        end
    end
    return nil
end

function addonTable.SendToTranslatorTab(event, rawText, cleanTranslation, author)
    local frame = addonTable.EnsureTranslatorTab()
    if not frame then return end

    local color = CHANNEL_COLORS[event] or "|cff00e5ff"
    local tag = CHANNEL_TAGS[event] or "[Chat]"
    local senderStr = author and (" [" .. author .. "]: ") or ": "

    local settings = WoWTranslatorDB and WoWTranslatorDB.settings
    local outputText
    if settings and settings.bilingualTab then
        outputText = color .. tag .. senderStr .. "|r" .. rawText .. "\n|cff00e5ff  └── [ES] |r|cfffff0c0" .. cleanTranslation .. "|r"
    else
        outputText = color .. tag .. senderStr .. "|r|cfffff0c0" .. cleanTranslation .. "|r"
    end

    frame:AddMessage(outputText)
end

-- ==============================================================================
-- 2. VACIADO DE CHATLOG A DISCO (Debounced 0.20s para la app de escritorio)
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

local function EnsureChatLogging()
    if not LoggingChat() then
        LoggingChat(true)
    end
end

-- ==============================================================================
-- 3. COMANDOS /en y /ingles PARA RESPONDER EN INGLÉS GAMER
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
-- 4. COMANDOS /translator y /fcl
-- ==============================================================================
SLASH_WOWCHATTRANSLATOR1 = "/translator"
SLASH_WOWCHATTRANSLATOR2 = "/fcl"
SlashCmdList["WOWCHATTRANSLATOR"] = function(msg)
    local cmd, arg = (msg or ""):match("^%s*(%S+)%s*(.-)%s*$")
    cmd = (cmd or ""):lower()
    local chatFrame = SELECTED_CHAT_FRAME or DEFAULT_CHAT_FRAME or ChatFrame1

    if cmd == "tab" then
        local tabFrame = addonTable.GetTranslatorChatFrame()
        if tabFrame and FCF_SelectDockFrame then
            FCF_SelectDockFrame(tabFrame)
            chatFrame:AddMessage("|cff00ff00[WoW Chat Translator]|r Cambiado a la pestaña Traductor.")
        else
            addonTable.EnsureTranslatorTab()
            chatFrame:AddMessage("|cff00e5ff[WoW Chat Translator]|r Pestaña Traductor creada e integrada.")
        end

    elseif cmd == "inline" then
        local sub = (arg or ""):lower()
        local settings = WoWTranslatorDB and WoWTranslatorDB.settings
        if settings then
            if sub == "on" then
                settings.showSubtitlesInMainChat = true
                chatFrame:AddMessage("|cff00ff00[WoW Chat Translator]|r Subtítulos en el chat principal: ENCENDIDOS.")
            elseif sub == "off" then
                settings.showSubtitlesInMainChat = false
                chatFrame:AddMessage("|cffff0000[WoW Chat Translator]|r Subtítulos en el chat principal: APAGADOS (las traducciones se verán solo en la pestaña Traductor).")
            else
                settings.showSubtitlesInMainChat = not settings.showSubtitlesInMainChat
                local st = settings.showSubtitlesInMainChat and "|cff00ff00ENCENDIDOS|r" or "|cffff0000APAGADOS|r"
                chatFrame:AddMessage("|cff00e5ff[WoW Chat Translator]|r Subtítulos en el chat principal: " .. st)
            end
        end

    elseif cmd == "bilingual" then
        local sub = (arg or ""):lower()
        local settings = WoWTranslatorDB and WoWTranslatorDB.settings
        if settings then
            if sub == "on" then
                settings.bilingualTab = true
                chatFrame:AddMessage("|cff00ff00[WoW Chat Translator]|r Modo bilingüe en pestaña Traductor: ENCENDIDO.")
            elseif sub == "off" then
                settings.bilingualTab = false
                chatFrame:AddMessage("|cff00ff00[WoW Chat Translator]|r Modo bilingüe en pestaña Traductor: APAGADO (solo español limpio).")
            else
                settings.bilingualTab = not settings.bilingualTab
                local st = settings.bilingualTab and "|cff00ff00ENCENDIDO|r" or "|cff00ff00APAGADO (solo español limpio)|r"
                chatFrame:AddMessage("|cff00e5ff[WoW Chat Translator]|r Modo bilingüe en pestaña Traductor: " .. st)
            end
        end

    elseif cmd == "test" then
        local testCases = {
            "LFM ICC 25 HC need 2 heal 1 tank",
            "wait sec, healer oom, dont pull yet",
            "can someone tell me where the exit is?",
            "watch out for tail swipe, focus adds",
            "anyone need this item or can i greed?"
        }
        chatFrame:AddMessage("|cff00e5ff=== Demostración de Traducción In-Game ===|r")
        for _, orig in ipairs(testCases) do
            local cleanTr = orig
            if addonTable.TranslateClean then
                local tr, ch = addonTable.TranslateClean(orig)
                if ch then cleanTr = tr end
            end
            chatFrame:AddMessage("|cffA8C8FF[Original]:|r " .. orig)
            chatFrame:AddMessage("|cff00e5ff  └── [ES]:|r |cfffff0c0" .. cleanTr .. "|r")

            -- Enviar también a la pestaña Traductor para probarla
            if addonTable.SendToTranslatorTab then
                addonTable.SendToTranslatorTab("CHAT_MSG_PARTY", orig, cleanTr, "TestPlayer")
            end
        end
        chatFrame:AddMessage("|cff00e5ffPrueba enviada también a la pestaña [Traductor]. Haz clic en ella para verla.|r")

    elseif cmd == "config" or cmd == "options" or cmd == "menu" then
        if SlashCmdList["WOWTRANSLATOR"] then
            SlashCmdList["WOWTRANSLATOR"]("config")
        end

    elseif cmd == "flush" then
        FlushLogToDisk()
        chatFrame:AddMessage("|cff00ff00[WoW Chat Translator]|r Vaciado manual a disco completado.")

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
        chatFrame:AddMessage(" Pestaña integrada [Traductor] activa en tu chat de WoW.")
        chatFrame:AddMessage(" Comandos disponibles:")
        chatFrame:AddMessage("   |cffFFD100/translator tab|r - Cambia de inmediato a la pestaña [Traductor]")
        chatFrame:AddMessage("   |cffFFD100/translator inline on/off|r - Enciende o apaga subtítulos en el chat principal")
        chatFrame:AddMessage("   |cffFFD100/translator bilingual on/off|r - Alterna modo bilingüe en la pestaña Traductor")
        chatFrame:AddMessage("   |cffFFD100/translator test|r - Prueba de traducción en vivo")
        chatFrame:AddMessage("   |cffFFD100/en <texto>|r - Traduce de español a inglés gamer y lo coloca para enviar")
        chatFrame:AddMessage("   |cffFFD100/translator config|r - Abre el panel visual de opciones")
    end
end

-- ==============================================================================
-- 5. EVENT HOOKS DE ARRANQUE Y CREACIÓN DE PESTAÑA
-- ==============================================================================
local initFrame = CreateFrame("Frame")
initFrame:RegisterEvent("PLAYER_LOGIN")
initFrame:RegisterEvent("PLAYER_ENTERING_WORLD")
local announced = false

initFrame:SetScript("OnEvent", function(self, event)
    EnsureChatLogging()
    -- Crear o reconectar la pestaña integrada "Traductor"
    addonTable.EnsureTranslatorTab()

    if not announced and (event == "PLAYER_LOGIN" or event == "PLAYER_ENTERING_WORLD") then
        announced = true
        local chatFrame = SELECTED_CHAT_FRAME or DEFAULT_CHAT_FRAME or ChatFrame1
        if chatFrame then
            chatFrame:AddMessage("|cff00e5ff[WoW Chat Translator]|r Pestaña |cff00ff00[Traductor]|r integrada en tu chat. Escribe |cffFFD100/translator tab|r o |cffFFD100/en <texto>|r.")
        end
    end
end)
