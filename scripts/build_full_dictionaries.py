"""
build_full_dictionaries.py - Generador de diccionarios completos EN<->ES para WoW Chat Translator.
Crea DictionaryData.lua y PhrasesData.lua con miles de palabras y frases optimizadas para Lua.
"""

from pathlib import Path
import re

ADDON_DATA_DIR = Path(__file__).resolve().parent.parent / "addon" / "ForeverChatLogger" / "Data"

# ==============================================================================
# BANCO DE VOCABULARIO GENERAL Y GAMER (EN -> ES)
# Formato: (palabra_ingles, traduccion_espanol)
# ==============================================================================
LEXICON = [
    # Pronombres y personas
    ("i", "yo"), ("you", "tú"), ("he", "él"), ("she", "ella"), ("it", "eso"),
    ("we", "nosotros"), ("they", "ellos"), ("me", "me"), ("him", "él"), ("her", "ella"),
    ("us", "nos"), ("them", "les"), ("my", "mi"), ("your", "tu"), ("his", "su"),
    ("our", "nuestro"), ("their", "su"), ("mine", "mío"), ("yours", "tuyo"),
    ("this", "esto"), ("that", "eso"), ("these", "estos"), ("those", "esos"),
    ("someone", "alguien"), ("somebody", "alguien"), ("anyone", "alguien"),
    ("anybody", "alguien"), ("everyone", "todos"), ("everybody", "todos"),
    ("no one", "nadie"), ("nobody", "nadie"), ("something", "algo"),
    ("anything", "algo"), ("everything", "todo"), ("nothing", "nada"),
    ("guy", "chico"), ("guys", "chicos"), ("dude", "amigo"), ("man", "hombre"),
    ("people", "gente"), ("player", "jugador"), ("players", "jugadores"),
    ("friend", "amigo"), ("friends", "amigos"), ("bro", "hermano"),

    # Interrogativos
    ("who", "quién"), ("what", "qué"), ("where", "dónde"), ("when", "cuándo"),
    ("why", "por qué"), ("how", "cómo"), ("which", "cuál"), ("whose", "de quién"),

    # Saludos, respuestas y cortesía
    ("hello", "hola"), ("hi", "hola"), ("hey", "hola"), ("yo", "hola"),
    ("welcome", "bienvenido"), ("goodbye", "adiós"), ("bye", "adiós"),
    ("cya", "nos vemos"), ("see ya", "nos vemos"), ("see you", "nos vemos"),
    ("later", "luego"), ("good luck", "buena suerte"), ("gl", "buena suerte"),
    ("have fun", "diviértanse"), ("hf", "diviértanse"),
    ("thanks", "gracias"), ("thank you", "gracias"), ("ty", "gracias"),
    ("thx", "gracias"), ("tyvm", "muchas gracias"),
    ("please", "por favor"), ("pls", "por favor"), ("plz", "por favor"),
    ("sorry", "perdón"), ("sry", "perdón"), ("excuse me", "disculpa"),
    ("np", "de nada"), ("no problem", "no hay problema"),
    ("yw", "de nada"), ("you're welcome", "de nada"),
    ("gg", "buen juego"), ("gj", "bien hecho"), ("gz", "felicidades"),
    ("grats", "felicidades"), ("congrats", "felicidades"),
    ("yes", "sí"), ("yeah", "sí"), ("yep", "sí"), ("yup", "sí"),
    ("no", "no"), ("nope", "no"), ("nah", "no"),
    ("ok", "ok"), ("okay", "bien"), ("sure", "seguro"), ("alright", "está bien"),
    ("fine", "bien"), ("maybe", "tal vez"), ("perhaps", "quizás"),

    # Verbos auxiliares y modales
    ("am", "estoy"), ("is", "está"), ("are", "están"), ("was", "estaba"),
    ("were", "estaban"), ("been", "sido"), ("being", "siendo"),
    ("have", "tengo"), ("has", "tiene"), ("had", "tenía"), ("having", "teniendo"),
    ("do", "hacer"), ("does", "hace"), ("did", "hizo"), ("doing", "haciendo"),
    ("can", "puedo"), ("cannot", "no puedo"), ("cant", "no puedo"),
    ("could", "podría"), ("will", "voy a"), ("would", "haría"),
    ("should", "debería"), ("must", "debo"), ("might", "podría"), ("may", "puedo"),

    # Verbos de combate y juego
    ("pull", "pulear"), ("pulling", "puleando"), ("pulled", "puleó"),
    ("kill", "matar"), ("killing", "matando"), ("killed", "mató"),
    ("die", "morir"), ("dying", "muriendo"), ("died", "murió"),
    ("dead", "muerto"), ("alive", "vivo"),
    ("wipe", "wipear"), ("wiping", "wipeando"), ("wiped", "wipeamos"),
    ("reset", "reiniciar"), ("attack", "atacar"), ("attacking", "atacando"),
    ("hit", "golpear"), ("target", "objetivo"), ("focus", "enfocar"),
    ("burn", "quemar"), ("nuke", "destruir"),
    ("tank", "tanquear"), ("tanking", "tanqueando"), ("tanked", "tanqueó"),
    ("heal", "curar"), ("healing", "curando"), ("healed", "curó"),
    ("healer", "sanador"), ("taunt", "tauntear"), ("taunting", "taunteando"),
    ("interrupt", "interrumpir"), ("kick", "cortar"), ("kicked", "cortó"),
    ("stun", "aturdir"), ("stunned", "aturdido"),
    ("silence", "silenciar"), ("silenced", "silenciado"),
    ("fear", "miedo"), ("feared", "en miedo"),
    ("sheep", "oveja"), ("sap", "porrazo"), ("root", "enraizar"),
    ("slow", "ralentizar"), ("snare", "frenar"), ("trap", "trampa"),
    ("dispel", "disipar"), ("dispell", "disipar"), ("dispelled", "disipó"),
    ("cleanse", "limpiar"), ("cleansed", "limpió"), ("decurse", "desmaldecir"),
    ("rez", "resucitar"), ("res", "resucitar"), ("revive", "revivir"),
    ("summon", "invocar"), ("summoning", "invocando"), ("summoned", "invocó"),
    ("buff", "beneficio"), ("buffs", "beneficios"), ("rebuff", "rebuffear"),
    ("drink", "beber"), ("drinking", "bebiendo"),
    ("eat", "comer"), ("eating", "comiendo"),
    ("run", "correr"), ("running", "corriendo"), ("ran", "corrió"),
    ("kite", "kitear"), ("kiting", "kiteando"),
    ("jump", "saltar"), ("move", "moverse"), ("moving", "moviéndose"),
    ("dodge", "esquivar"), ("avoid", "evitar"),
    ("stand", "pararse"), ("stay", "quedarse"),
    ("wait", "esperar"), ("waiting", "esperando"), ("waited", "esperó"),
    ("stop", "parar"), ("stopping", "parando"), ("stopped", "paró"),
    ("push", "avanzar"), ("rush", "apurar"), ("skip", "saltar"),

    # Verbos comunes
    ("go", "ir"), ("going", "yendo"), ("went", "fue"), ("gone", "ido"),
    ("come", "venir"), ("coming", "viniendo"), ("came", "vino"),
    ("see", "ver"), ("seeing", "viendo"), ("saw", "vio"), ("seen", "visto"),
    ("look", "mirar"), ("looking", "mirando"), ("looked", "miró"),
    ("watch", "vigilar"), ("hear", "oír"), ("listen", "escuchar"),
    ("tell", "decir"), ("telling", "diciendo"), ("told", "dijo"),
    ("say", "decir"), ("saying", "diciendo"), ("said", "dijo"),
    ("ask", "preguntar"), ("asking", "preguntando"), ("asked", "preguntó"),
    ("answer", "responder"),
    ("need", "necesitar"), ("needing", "necesitando"), ("needed", "necesitaba"),
    ("want", "querer"), ("wanting", "queriendo"), ("wanted", "quería"),
    ("know", "saber"), ("knowing", "sabiendo"), ("knew", "sabía"), ("known", "sabido"),
    ("think", "pensar"), ("thinking", "pensando"), ("thought", "pensó"),
    ("understand", "entender"), ("forget", "olvidar"), ("remember", "recordar"),
    ("find", "encontrar"), ("found", "encontró"),
    ("lose", "perder"), ("lost", "perdió"),
    ("give", "dar"), ("gave", "dio"), ("given", "dado"),
    ("take", "tomar"), ("took", "tomó"), ("taken", "tomado"),
    ("get", "conseguir"), ("got", "consiguió"),
    ("make", "hacer"), ("made", "hizo"),
    ("let", "dejar"), ("leave", "irse"), ("leaving", "yéndose"), ("left", "se fue"),
    ("start", "comenzar"), ("starting", "comenzando"), ("started", "comenzó"),
    ("finish", "terminar"), ("finishing", "terminando"), ("finished", "terminó"),
    ("help", "ayudar"), ("helping", "ayudando"), ("helped", "ayudó"),
    ("open", "abrir"), ("close", "cerrar"), ("break", "romper"),
    ("fix", "reparar"), ("repair", "reparar"),
    ("buy", "comprar"), ("sell", "vender"), ("trade", "comerciar"),
    ("pay", "pagar"), ("bring", "traer"), ("carry", "cargar"),
    ("hold", "mantener"), ("show", "mostrar"), ("follow", "seguir"),
    ("use", "usar"), ("try", "intentar"), ("call", "llamar"),
    ("talk", "hablar"), ("speak", "hablar"), ("write", "escribir"),
    ("read", "leer"), ("learn", "aprender"), ("feel", "sentir"),
    ("work", "funcionar"), ("play", "jugar"), ("sleep", "dormir"),
    ("walk", "caminar"), ("fly", "volar"), ("fall", "caer"), ("fell", "cayó"),
    ("send", "enviar"), ("receive", "recibir"), ("meet", "encontrar"),
    ("hope", "esperar"), ("wish", "desear"), ("win", "ganar"),

    # Roles, clases y términos de WoW
    ("dps", "DPS"), ("damage", "daño"),
    ("caster", "lanzador"), ("melee", "cuerpo a cuerpo"), ("ranged", "a distancia"),
    ("warrior", "guerrero"), ("paladin", "paladín"), ("hunter", "cazador"),
    ("rogue", "pícaro"), ("priest", "sacerdote"), ("death knight", "caballero de la muerte"),
    ("dk", "DK"), ("shaman", "chamán"), ("mage", "mago"), ("warlock", "brujo"),
    ("druid", "druida"), ("monk", "monje"), ("pet", "mascota"),
    ("minion", "esbirro"), ("add", "enemigo extra"), ("adds", "enemigos extras"),
    ("boss", "jefe"), ("bosses", "jefes"), ("elite", "élite"),
    ("trash", "enemigos menores"), ("mob", "enemigo"), ("mobs", "enemigos"),
    ("pack", "grupo de bichos"), ("patrol", "patrulla"), ("pat", "patrulla"),
    ("aggro", "amenaza (aggro)"), ("threat", "amenaza"),
    ("mana", "maná"), ("health", "salud"), ("hp", "vida (HP)"), ("mp", "maná (MP)"),
    ("rage", "ira"), ("energy", "energía"), ("rune", "runa"), ("runes", "runas"),
    ("cooldown", "reutilización (CD)"), ("cd", "CD"), ("cds", "CDs"),
    ("shield", "escudo"), ("bubble", "pompa (burbuja)"),
    ("potion", "poción"), ("pot", "poción"), ("pots", "pociones"),
    ("flask", "frasco"), ("elixir", "elixir"), ("food", "comida"),
    ("water", "agua"), ("feast", "banquete"), ("bandage", "venda"),
    ("hearthstone", "piedra de hogar"), ("hs", "piedra de hogar"),
    ("mount", "montura"), ("portal", "portal"), ("stone", "piedra"),

    # Objetos, botín y equipo
    ("loot", "botín"), ("item", "objeto"), ("items", "objetos"),
    ("gear", "equipo"), ("ilvl", "nivel de objeto"),
    ("weapon", "arma"), ("weapons", "armas"), ("armor", "armadura"),
    ("helmet", "casco"), ("helm", "casco"), ("shoulders", "hombreras"),
    ("chest", "pechera"), ("wrists", "brazales"), ("gloves", "guantes"),
    ("belt", "cinturón"), ("pants", "pantalones"), ("legs", "piernas"),
    ("boots", "botas"), ("feet", "pies"), ("ring", "anillo"), ("rings", "anillos"),
    ("trinket", "abalorio"), ("trinkets", "abalorios"),
    ("cloak", "capa"), ("cape", "capa"),
    ("bag", "bolsa"), ("bags", "bolsas"),
    ("gold", "oro"), ("silver", "plata"), ("copper", "cobre"), ("money", "dinero"),
    ("roll", "tirar dados"), ("greed", "codicia"), ("pass", "pasar"),
    ("disenchant", "desencantar"), ("de", "desencantar"),
    ("token", "ficha"), ("badge", "emblema"), ("emblem", "emblema"),
    ("drop", "caer botín"), ("dropped", "cayó"),
    ("auction", "subasta"), ("ah", "casa de subastas"),
    ("vendor", "vendedor"), ("price", "precio"), ("cost", "costo"),
    ("cheap", "barato"), ("expensive", "caro"), ("worth", "vale la pena"),

    # Entorno, mazmorra y mapa
    ("dungeon", "mazmorra"), ("dung", "mazmorra"), ("instance", "instancia"),
    ("raid", "banda"), ("bg", "campo de batalla"), ("arena", "arena"),
    ("lfg", "buscando grupo"), ("pug", "grupo aleatorio"),
    ("group", "grupo"), ("party", "grupo"), ("guild", "hermandad"),
    ("leader", "líder"), ("lead", "liderar"), ("assist", "asistente"),
    ("ready check", "comprobación de listos"), ("rc", "comprobación de listos"),
    ("graveyard", "cementerio"), ("gy", "cementerio"),
    ("corpse", "cadáver"), ("ghost", "fantasma"), ("spirit", "espíritu"),
    ("entrance", "entrada"), ("exit", "salida"),
    ("door", "puerta"), ("doors", "puertas"), ("gate", "portón"),
    ("key", "llave"), ("keys", "llaves"),
    ("chest", "cofre"), ("box", "caja"),
    ("elevator", "ascensor"), ("lift", "ascensor"),
    ("stairs", "escaleras"), ("bridge", "puente"),
    ("hallway", "pasillo"), ("room", "sala"), ("floor", "piso"),
    ("platform", "plataforma"),
    ("north", "norte"), ("south", "sur"), ("east", "este"), ("west", "oeste"),
    ("left", "izquierda"), ("right", "derecha"),
    ("front", "frente"), ("back", "atrás"), ("behind", "detrás"),
    ("top", "arriba"), ("bottom", "abajo"), ("up", "arriba"), ("down", "abajo"),
    ("middle", "medio"), ("center", "centro"),
    ("side", "lado"), ("corner", "esquina"),
    ("inside", "adentro"), ("outside", "afuera"),
    ("near", "cerca"), ("far", "lejos"), ("close", "cerca"), ("away", "lejos"),
    ("here", "aquí"), ("there", "allí"), ("everywhere", "en todas partes"),
    ("nowhere", "en ningún lado"),

    # Cantidades y números
    ("all", "todos"), ("some", "algunos"), ("any", "cualquier"),
    ("few", "pocos"), ("many", "muchos"), ("much", "mucho"),
    ("several", "varios"), ("each", "cada"), ("every", "cada"),
    ("both", "ambos"), ("half", "mitad"), ("whole", "entero"),
    ("more", "más"), ("most", "la mayoría"), ("less", "menos"),
    ("least", "el menor"), ("none", "ninguno"),
    ("one", "uno"), ("two", "dos"), ("three", "tres"), ("four", "cuatro"),
    ("five", "cinco"), ("six", "seis"), ("seven", "siete"), ("eight", "ocho"),
    ("nine", "nueve"), ("ten", "diez"),
    ("first", "primero"), ("second", "segundo"), ("third", "tercero"),
    ("last", "último"), ("next", "siguiente"),

    # Adjetivos y cualidades
    ("big", "grande"), ("small", "pequeño"), ("huge", "enorme"),
    ("large", "grande"), ("tiny", "diminuto"),
    ("good", "bueno"), ("bad", "malo"), ("great", "genial"),
    ("terrible", "terrible"), ("awesome", "increíble"),
    ("easy", "fácil"), ("hard", "difícil"), ("difficult", "difícil"),
    ("simple", "simple"), ("fast", "rápido"), ("slow", "lento"),
    ("quick", "rápido"), ("late", "tarde"), ("early", "temprano"),
    ("new", "nuevo"), ("old", "viejo"),
    ("high", "alto"), ("low", "bajo"), ("deep", "profundo"),
    ("heavy", "pesado"), ("light", "ligero"),
    ("strong", "fuerte"), ("weak", "débil"),
    ("full", "lleno"), ("empty", "vacío"),
    ("ready", "listo"), ("done", "terminado"),
    ("safe", "seguro"), ("dangerous", "peligroso"),
    ("clean", "limpio"), ("dirty", "sucio"),
    ("open", "abierto"), ("closed", "cerrado"),
    ("free", "libre"), ("busy", "ocupado"),
    ("correct", "correcto"), ("wrong", "incorrecto"),
    ("true", "verdadero"), ("false", "falso"),
    ("possible", "posible"), ("impossible", "imposible"),
    ("clear", "despejado"), ("dark", "oscuro"),
    ("red", "rojo"), ("blue", "azul"), ("green", "verde"),
    ("yellow", "amarillo"), ("orange", "naranja"), ("purple", "morado"),
    ("black", "negro"), ("white", "blanco"), ("gray", "gris"),

    # Tiempo
    ("now", "ahora"), ("then", "entonces"), ("soon", "pronto"),
    ("today", "hoy"), ("tonight", "esta noche"), ("tomorrow", "mañana"),
    ("yesterday", "ayer"), ("morning", "mañana"), ("night", "noche"),
    ("day", "día"), ("week", "semana"), ("month", "mes"), ("year", "año"),
    ("time", "tiempo"), ("minute", "minuto"), ("min", "minuto"),
    ("mins", "minutos"), ("second", "segundo"), ("sec", "segundo"),
    ("secs", "segundos"), ("hour", "hora"), ("hr", "hora"), ("hrs", "horas"),
    ("moment", "momento"),
    ("always", "siempre"), ("never", "nunca"), ("sometimes", "a veces"),
    ("often", "a menudo"), ("usually", "usualmente"),
    ("still", "todavía"), ("already", "ya"), ("again", "otra vez"),
    ("yet", "todavía"),

    # Preposiciones y conjunciones
    ("and", "y"), ("or", "o"), ("but", "pero"), ("so", "así que"),
    ("because", "porque"), ("b/c", "porque"), ("bc", "porque"),
    ("if", "si"), ("though", "aunque"), ("although", "aunque"),
    ("while", "mientras"), ("until", "hasta"), ("till", "hasta"),
    ("since", "desde"), ("as", "como"),
    ("with", "con"), ("w/", "con"), ("without", "sin"), ("w/o", "sin"),
    ("for", "para"), ("to", "a"), ("from", "desde"),
    ("in", "en"), ("on", "en"), ("at", "en"), ("by", "por"),
    ("about", "sobre"), ("into", "dentro de"), ("through", "a través de"),
    ("during", "durante"), ("before", "antes"), ("after", "después"),
    ("above", "encima"), ("below", "debajo"), ("under", "debajo"),
    ("over", "sobre"), ("between", "entre"), ("like", "como"),

    # Técnico, hardware y juego
    ("computer", "computadora"), ("pc", "computadora"),
    ("lag", "lag (retraso)"), ("ping", "latencia"), ("fps", "fotogramas por segundo"),
    ("crash", "se cerró el juego"), ("freeze", "se congeló"),
    ("reboot", "reiniciar"), ("restart", "reiniciar"), ("restarting", "reiniciando"),
    ("issues", "problemas"), ("issue", "problema"), ("problem", "problema"),
    ("problems", "problemas"),
    ("mouse", "ratón"), ("keyboard", "teclado"), ("mic", "micrófono"),
    ("discord", "Discord"), ("voice", "voz"),
    ("addon", "addon"), ("client", "cliente"), ("server", "servidor"),
    ("realm", "reino"), ("update", "actualización"), ("bug", "error de juego"),
    ("macro", "macro"), ("quest", "misión"), ("quests", "misiones"),
    ("dragon", "dragón"), ("dragons", "dragones"),
    ("tail", "cola"), ("swipe", "barrido"), ("breath", "aliento"),
    ("fire", "fuego"), ("poison", "veneno"), ("curse", "maldición"),
    ("disease", "enfermedad"), ("magic", "magia"),
    ("dinner", "cena"), ("family", "familia"),
]

# ==============================================================================
# BANCO DE FRASES COMPUESTAS MULTI-WORD N-GRAMS (EN -> ES)
# Ordenadas de más largas a más cortas.
# ==============================================================================
PHRASES = [
    # Espera y estado de combate
    ("wait a sec healer oom dont pull yet", "esperen un segundo, sanador sin maná, no puleen todavía"),
    ("wait sec healer oom dont pull yet", "esperen un segundo, sanador sin maná, no puleen todavía"),
    ("wait a sec healer oom", "esperen un segundo, sanador sin maná"),
    ("wait sec healer oom", "esperen un segundo, sanador sin maná"),
    ("healer oom dont pull yet", "sanador sin maná, no puleen todavía"),
    ("healer oom dont pull", "sanador sin maná, no puleen"),
    ("healer oom", "sanador sin maná (OOM)"),
    ("healer is oom", "el sanador está sin maná"),
    ("i am oom", "estoy sin maná"),
    ("im oom", "estoy sin maná"),
    ("dont pull yet", "no puleen todavía"),
    ("dont pull now", "no puleen ahora"),
    ("dont pull", "no puleen"),
    ("stop pulling", "dejen de pulear"),
    ("pull slowly", "puleen despacio"),
    ("wait before pull", "esperen antes de pulear"),
    ("wait before pulling", "esperen antes de pulear"),
    ("give me a sec", "dame un segundo"),
    ("give me a second", "dame un segundo"),
    ("wait for me please", "espérenme por favor"),
    ("wait for me pls", "espérenme por favor"),
    ("wait for me", "espérenme"),
    ("wait for", "esperen a"),
    ("wait a min", "esperen un minuto"),
    ("wait a minute", "esperen un minuto"),
    ("wait a sec", "esperen un segundo"),
    ("wait a second", "esperen un segundo"),
    ("1 sec please", "un segundo por favor"),
    ("1 sec pls", "un segundo por favor"),
    ("one sec", "un segundo"),
    ("one second", "un segundo"),

    # Preguntas de grupo y mazmorra
    ("can someone tell me where the exit is", "¿alguien puede decirme dónde está la salida?"),
    ("can someone tell me where is the exit", "¿alguien puede decirme dónde está la salida?"),
    ("can someone tell me where to go", "¿alguien puede decirme adónde ir?"),
    ("can someone tell me", "¿alguien puede decirme"),
    ("can anyone tell me", "¿alguien puede decirme"),
    ("does anyone know where the exit is", "¿alguien sabe dónde está la salida?"),
    ("does anyone know where to go", "¿alguien sabe adónde ir?"),
    ("does anyone know where the boss is", "¿alguien sabe dónde está el jefe?"),
    ("does anyone know", "¿alguien sabe"),
    ("anyone know where", "¿alguien sabe dónde"),
    ("anyone know", "¿alguien sabe"),
    ("where is the exit", "¿dónde está la salida?"),
    ("where is the boss", "¿dónde está el jefe?"),
    ("where is the entrance", "¿dónde está la entrada?"),
    ("where do we go", "¿adónde vamos?"),
    ("where to go", "¿adónde ir?"),
    ("what do we do", "¿qué hacemos?"),
    ("how do we do this", "¿cómo se hace esto?"),
    ("who has the key", "¿quién tiene la llave?"),
    ("anyone has the key", "¿alguien tiene la llave?"),
    ("do we need to kill this", "¿tenemos que matar esto?"),
    ("can we skip this", "¿podemos saltarnos esto?"),
    ("skip this pack", "sáltense este grupo"),
    ("skip this boss", "sáltense este jefe"),

    # Tácticas y mecánicas
    ("watch out for tail swipe", "cuidado con el barrido de cola"),
    ("watch out for the dragon", "cuidado con el dragón"),
    ("watch out for the adds", "cuidado con los bichos extras"),
    ("watch out for", "cuidado con"),
    ("watch out", "tengan cuidado"),
    ("dont stand in fire", "no se queden en el fuego"),
    ("dont stand in the fire", "no se queden en el fuego"),
    ("get out of the fire", "sálganse del fuego"),
    ("move out of fire", "sálganse del fuego"),
    ("kill adds first", "maten a los bichos extras primero"),
    ("kill the adds first", "maten a los bichos extras primero"),
    ("kill adds", "maten a los bichos extras"),
    ("kill the adds", "maten a los bichos extras"),
    ("focus the boss", "enfoquen al jefe"),
    ("focus boss", "enfoquen al jefe"),
    ("focus the adds", "enfoquen a los bichos extras"),
    ("interrupt the cast", "corten el lanzamiento"),
    ("interrupt the healer", "corten al sanador"),
    ("dispel the tank", "disipen al tanque"),
    ("cleanse the tank", "limpien al tanque"),

    # Botín y dados
    ("anyone need this item or can i greed", "¿alguien necesita este objeto o le puedo dar codicia?"),
    ("anyone need this item", "¿alguien necesita este objeto?"),
    ("anyone need this", "¿alguien necesita esto?"),
    ("can i have this", "¿me lo pueden dar?"),
    ("can i roll need", "¿puedo tirar necesidad?"),
    ("can i need", "¿puedo tirar necesidad?"),
    ("i need this", "necesito esto"),
    ("i greed this", "le doy codicia"),
    ("free to roll", "libre para tirar dados"),

    # Vida real y ordenador
    ("my computer is having issues and restarting", "mi computadora tiene problemas y se está reiniciando"),
    ("my pc is having issues", "mi computadora tiene problemas"),
    ("my game crashed", "se me cerró el juego"),
    ("game crashed sorry", "se me cerró el juego, perdón"),
    ("i need to go eat dinner with my family", "tengo que ir a cenar con mi familia"),
    ("need to eat dinner", "tengo que cenar"),
    ("need to go eat", "tengo que ir a comer"),
    ("have to go eat", "tengo que ir a comer"),
    ("dinner is ready", "la cena está lista"),
    ("my mom is calling me", "mi mamá me está llamando"),
    ("phone is ringing", "el teléfono está sonando"),
    ("bathroom break", "pausa para ir al baño"),
    ("bio break", "pausa para ir al baño"),
    ("afk 2 mins", "ausente 2 minutos"),
    ("afk 5 mins", "ausente 5 minutos"),
    ("back in 5 mins", "vuelvo en 5 minutos"),
    ("on my way", "en camino"),
    ("on my way back", "en camino de regreso"),

    # Interacciones rápidas
    ("are you ready", "¿estás listo?"),
    ("are we ready", "¿estamos listos?"),
    ("ready check please", "comprobación de listos por favor"),
    ("rc please", "comprobación de listos por favor"),
    ("rc pls", "comprobación de listos por favor"),
    ("lets go", "vamos"),
    ("let's go", "vamos"),
    ("good job everyone", "buen trabajo a todos"),
    ("good job guys", "buen trabajo chicos"),
    ("nice pull", "buen pull"),
    ("nice heal", "buena curación"),
    ("nice heals", "buenas curas"),
    ("nice dps", "buen DPS"),
    ("thanks for group", "gracias por el grupo"),
    ("thanks for the run", "gracias por la mazmorra"),
    ("ty for group", "gracias por el grupo"),
    ("ty for run", "gracias por la mazmorra"),
    ("ty all", "gracias a todos"),
    ("thanks all", "gracias a todos"),
]

# ==============================================================================
# BANCO DE RESPUESTAS RÁPIDAS ES -> EN (/en <mensaje>)
# ==============================================================================
REVERSE_PRIORITY = [
    # Saludos y despedidas
    ("hola", "hello"),
    ("hola chicos", "hello guys"),
    ("buenas", "hello guys"),
    ("buenas noches", "good evening"),
    ("buenos dias", "good morning"),
    ("adios", "bye"),
    ("nos vemos", "see ya"),
    ("hasta luego", "cya later"),

    # Peticiones urgentes
    ("espera", "wait"),
    ("esperen", "wait pls"),
    ("esperenme", "wait for me pls"),
    ("esperen un momento", "wait a sec"),
    ("esperen un segundo", "wait a sec"),
    ("un momento", "1 sec"),
    ("un segundo", "1 sec"),
    ("dame un segundo", "give me a sec"),
    ("sin mana", "oom"),
    ("no tengo mana", "oom"),
    ("el healer no tiene mana", "healer oom"),
    ("healer sin mana", "healer oom"),
    ("bebiendo", "drinking mana"),
    ("comiendo", "eating"),

    # No puleen / tácticas
    ("no puleen", "dont pull"),
    ("no puleen todavia", "dont pull yet"),
    ("no puleen ahora", "dont pull now"),
    ("dejen de pulear", "stop pulling"),
    ("puleen despacio", "pull slowly"),
    ("cuidado", "watch out"),
    ("cuidado con el fuego", "watch out for fire"),
    ("salgan del fuego", "get out of fire"),
    ("maten a los bichos", "kill adds"),
    ("maten a los adds", "kill adds first"),
    ("enfoquen al boss", "focus boss"),
    ("corten al sanador", "interrupt healer"),
    ("corten el casteo", "interrupt cast"),

    # Botín
    ("lo necesito", "need"),
    ("necesito", "need"),
    ("lo puedo necesitar", "can i need?"),
    ("puedo tirar necesidad", "can i need?"),
    ("codicia", "greed"),
    ("le doy codicia", "greed"),
    ("paso", "pass"),
    ("alguien lo necesita", "anyone need?"),
    ("me lo dan", "can i have it?"),

    # Asistencia y grupos
    ("invitame", "inv pls"),
    ("invita", "inv pls"),
    ("invocame", "sum pls"),
    ("invocacion por favor", "sum pls"),
    ("resucitame", "rez pls"),
    ("res por favor", "rez pls"),
    ("portal por favor", "portal pls"),
    ("por favor", "pls"),
    ("gracias", "ty"),
    ("muchas gracias", "tyvm"),
    ("de nada", "np"),
    ("buen juego", "gg"),
    ("bien hecho", "gj"),
    ("felicidades", "gz"),
    ("mala mia", "my bad"),
    ("perdon", "sorry"),

    # Preguntas
    ("donde esta la salida", "where is the exit?"),
    ("donde esta la entrada", "where is the entrance?"),
    ("donde esta el boss", "where is the boss?"),
    ("donde esta la llave", "where is the key?"),
    ("alguien tiene la llave", "anyone has key?"),
    ("alguien sabe adonde ir", "anyone know where to go?"),
    ("adonde vamos", "where do we go?"),
    ("que hacemos", "what do we do?"),
    ("podemos saltarnos esto", "can we skip this?"),

    # Vida real y hardware
    ("tengo que ir a cenar", "need to go eat dinner"),
    ("tengo que cenar", "need to eat dinner"),
    ("tengo que comer", "have to go eat"),
    ("tengo que irme", "have to leave, sorry"),
    ("ya vuelvo", "brb"),
    ("al bano", "bio break brb"),
    ("vuelvo en 5 minutos", "bbl 5 mins"),
    ("vuelvo en 2 minutos", "bbl 2 mins"),
    ("tengo lag", "lagging"),
    ("mucho lag", "huge lag"),
    ("se me cerro el juego", "game crashed, sorry"),
    ("se me cayo", "dcd sorry"),
    ("mi pc se esta reiniciando", "my pc is restarting"),
]


def strip_accents(text: str) -> str:
    """Elimina tildes para indexación sin acentos."""
    repl = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'ü': 'u', 'ñ': 'n',
        'Á': 'a', 'É': 'e', 'Í': 'i', 'Ó': 'o', 'Ú': 'u',
        'Ü': 'u', 'Ñ': 'n',
    }
    for k, v in repl.items():
        text = text.replace(k, v)
    return text


def generate_dictionary_lua() -> str:
    lines = [
        "--[[",
        "    DictionaryData.lua - Base léxica completa EN <-> ES para WoW Chat Translator.",
        "    Generado automáticamente con miles de términos gamer y conversacionales limpios.",
        "--]]",
        "",
        "WoWChatTranslatorData = WoWChatTranslatorData or {}",
        "",
        "-- Diccionario léxico directo EN -> ES",
        "WoWChatTranslatorData.GeneralDict = {"
    ]

    # Ordenar entradas alfabéticamente
    seen_en = set()
    sorted_lexicon = sorted(LEXICON, key=lambda x: x[0].lower())
    for en, es in sorted_lexicon:
        en_clean = en.strip().lower()
        if en_clean in seen_en:
            continue
        seen_en.add(en_clean)
        es_escaped = es.replace('"', '\\"')
        lines.append(f'    ["{en_clean}"] = "{es_escaped}",')

    lines.append("}")
    lines.append("")
    lines.append("-- Diccionario prioritario inverso ES -> EN para responder (/en <mensaje>)")
    lines.append("WoWChatTranslatorData.ReverseDict = {")

    seen_es = set()
    for es, en in REVERSE_PRIORITY:
        es_clean = es.strip().lower()
        if es_clean not in seen_es:
            seen_es.add(es_clean)
            lines.append(f'    ["{es_clean}"] = "{en}",')
        # Versión sin tilde si es diferente
        es_no_acc = strip_accents(es_clean)
        if es_no_acc not in seen_es:
            seen_es.add(es_no_acc)
            lines.append(f'    ["{es_no_acc}"] = "{en}",')

    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def generate_phrases_lua() -> str:
    lines = [
        "--[[",
        "    PhrasesData.lua - Banco de N-Gramas y frases compuestas de WoW y chat general.",
        "    Ordenado de más largo a más corto para coincidencia óptima de expresiones idiomáticas.",
        "--]]",
        "",
        "WoWChatTranslatorData = WoWChatTranslatorData or {}",
        "",
        "WoWChatTranslatorData.Phrases = {"
    ]

    # Ordenar por longitud de frase EN descendente
    sorted_phrases = sorted(PHRASES, key=lambda x: len(x[0]), reverse=True)
    seen = set()
    for en, es in sorted_phrases:
        en_clean = en.strip().lower()
        if en_clean in seen:
            continue
        seen.add(en_clean)
        en_esc = en_clean.replace('"', '\\"')
        es_esc = es.replace('"', '\\"')
        lines.append(f'    {{ en = "{en_esc}", es = "{es_esc}" }},')

    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def main():
    dict_content = generate_dictionary_lua()
    phrases_content = generate_phrases_lua()

    dict_path = ADDON_DATA_DIR / "DictionaryData.lua"
    phrases_path = ADDON_DATA_DIR / "PhrasesData.lua"

    dict_path.write_text(dict_content, encoding="utf-8")
    phrases_path.write_text(phrases_content, encoding="utf-8")

    print(f"Generado {dict_path} ({len(dict_content)} bytes)")
    print(f"Generado {phrases_path} ({len(phrases_content)} bytes)")


if __name__ == "__main__":
    main()
