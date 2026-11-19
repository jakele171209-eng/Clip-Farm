"""Builds stories/48-hours.json (long-form, 16:9) and stories/48-hours-short.json (vertical cut).

Written as Python so a 10-minute script stays readable: one line per shot.
Run: python stories/build_48_hours.py
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

SOURCES = [
    "UBC (2020), 'UBC research shows hearing persists at end of life' — Blundon, Ward, Gallagher, Scientific Reports; EEG of hospice patients, 5 recorded while unresponsive: https://research.ubc.ca/node/16646",
    "Dawson & Reid (1997), Nature 388:235, via U.S. Air Force Safety Center 'Oh Man, Am I Beat!' (24 h awake ~ 0.10% BAC; 17-19 h ~ 0.05%, Williamson & Feyer 2000): https://www.safety.af.mil/News/Features/Display/Article/434514/oh-man-am-i-beat/",
    "Scotiabank / Maru survey, April 2024: 43% of Canadians say they don't have a will: https://www.newswire.ca/en/releases/archive/April2024/03/c4943.html",
    "Jiang & Carstensen (2023), Frontiers in Psychology, citing Fredrickson & Carstensen (1990) and Fung & Carstensen (2006, SARS Hong Kong and post-9/11): https://frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2022.1075814/pdf",
    "Richardson & Gilovich (2023), Royal Society Open Science, replication: short-term regrets are actions, long-term regrets are inactions: https://ecommons.cornell.edu/entities/publication/0cb2eb5b-f492-43c4-aaf4-513b1db7179a",
    "Dunn, Aknin & Norton (2008), Science, 'Spending money on others promotes happiness' ($5 or $20, spent on others vs self, same day): https://news.harvard.edu/gazette/story/2008/04/money-spent-on-others-can-buy-happiness/",
    "Criminal Code of Canada: 80 mg per 100 mL (0.08%) blood alcohol limit.",
]

HERO = {"who": "hero", "x": 0.32, "mood": "calm"}


def hero(mood, x=0.32, **kw):
    return [{"who": "hero", "x": x, "mood": mood, **kw}]


def duo(mood, other, omood, ox=0.62, hx=0.3):
    return [{"who": "hero", "x": hx, "mood": mood}, {"who": other, "x": ox, "mood": omood}]


S = []  # shots


def shot(text, **kw):
    S.append({"text": text, **kw})


# ---------------------------------------------------------------- cold open
shot("You have forty-eight hours to live.", scene="clinic", cast=duo("shock", "doctor", "flat"), clock="48:00:00",
     impact={"word": "live", "flash": "white", "shake": 0.5}, music="tense")
shot("No pain. No warning signs. You'll feel completely fine, right up until the end.", cast=duo("worried", "doctor", "flat"),
     label={"text": "TIME LEFT: 48 HOURS", "color": "red"})
shot("And in the next two days, you're going to make one mistake that almost everyone makes.", scene="mind", cast=hero("worried", 0.5),
     label={"text": "THE MISTAKE", "color": "red"})
shot("By the end of this video, you'll know what it is. And why science says you'll regret it.", cast=hero("awkward", 0.5))
shot("The clock starts now.", scene="clinic", cast=duo("shock", "doctor", "flat"), clock="47:59:30",
     impact={"word": "now", "flash": "black", "shake": 0.4})

# ---------------------------------------------------------------- chapter 1
shot("Hour zero.", chapter={"num": 1, "title": "THE DIAGNOSIS"}, cast=duo("worried", "doctor", "flat"), clock="47:58:00")
shot("Your heart is pounding. That's adrenaline. Your body thinks something is about to attack you.",
     cast=duo("shock", "doctor", "flat"), label={"text": "ADRENALINE: MAXED", "color": "red"})
shot("But there's nothing to fight. Just a number.", cast=duo("worried", "doctor", "flat"))
shot("So you do what everyone does first. You ask for a second opinion.", cast=duo("awkward", "doctor", "flat"),
     label={"text": "DENIAL: ACTIVATED", "color": "dark"})
shot("Then you google it. Which is a terrible idea.", scene="home_night", cast=hero("worried", 0.4),
     label={"text": "SEARCH RESULTS: 4,000,000", "color": "dark"})
shot("Every page is worse than the last. One forum says you have three hours. Another says you might be a vampire.",
     cast=hero("shock", 0.4), impact={"word": "vampire", "flash": "white", "shake": 0.2})
shot("You close the laptop and book a second appointment.", cast=hero("awkward", 0.4))
shot("The second doctor says the same thing.", scene="clinic", cast=duo("worried", "doctor", "flat"))
shot("So do the third and fourth.", cast=duo("shock", "doctor", "flat"), kicker="HOUR 2", clock="46:10:00")
shot("You just spent two hours proving something you already knew.", scene="street_night", cast=hero("awkward", 0.45),
     label={"text": "2 HOURS: GONE", "color": "red"})

# ---------------------------------------------------------------- chapter 2
shot("Okay. Let's do the math.", chapter={"num": 2, "title": "THE MATH"}, scene="mind", cast=hero("calm", 0.3), clock="45:55:00")
shot("Forty-six hours left. That's two thousand seven hundred and sixty minutes.",
     counter={"from": 0, "to": 2760, "unit": " MIN", "label": "WHAT YOU HAVE LEFT", "shift": False, "y": 440}, cast=hero("calm", 0.18))
shot("Your first idea: never sleep again. Why waste a single minute?", cast=hero("smug", 0.3),
     label={"text": "PLAN A: NO SLEEP", "color": "gold"})
shot("Here's the problem.", cast=hero("calm", 0.3))
shot("After about twenty-four hours awake, your brain works about as well as someone with a blood alcohol level of point one.",
     bars={"title": "HOW IMPAIRED YOU ARE", "rows": [
         {"name": "LEGAL DRIVING LIMIT (CANADA)", "value": 0.08, "unit": "%", "decimals": 2},
         {"name": "YOU, 24 HOURS AWAKE", "value": 0.10, "unit": "%", "decimals": 2, "hl": True}], "y": 280},
     cast=hero("sick", 0.12))
shot("That's over the legal limit. Your last day on Earth, and you'd spend it basically drunk.",
     cast=hero("sick", 0.3), label={"text": "PLAN A: CANCELLED", "color": "red"})
shot("So you'll need sleep. Two short nights, about six hours in total.", cast=hero("calm", 0.3))
shot("That leaves forty hours. And you haven't done anything yet.",
     counter={"from": 46, "to": 40, "unit": " HOURS", "label": "AWAKE TIME LEFT", "y": 440}, cast=hero("worried", 0.18))

# ---------------------------------------------------------------- chapter 3
shot("Hour three.", chapter={"num": 3, "title": "THE BUCKET LIST TRAP"}, scene="home_day", cast=hero("calm", 0.3), clock="45:00:00")
shot("You open your bucket list. Tokyo. The northern lights. Skydiving. A real Italian pizza in Naples.",
     card={"title": "BUCKET LIST", "rows": [["Tokyo", "10 H FLIGHT", "bad"], ["Northern lights", "CLOUDS?", "bad"],
                                            ["Skydiving", "BOOKED UP", "bad"], ["Pizza in Naples", "TOO FAR", "bad"]]},
     cast=hero("happy", 0.25))
shot("Then you check the flights.", cast=hero("calm", 0.25))
shot("From Vancouver, Tokyo is about ten hours in the air. Each way.", cast=hero("worried", 0.25),
     label={"text": "TOKYO: ~10 H EACH WAY", "color": "dark"})
shot("Add the airport, security, and the customs line, and half of your life is spent in a seat with a tiny screen.",
     cast=hero("awkward", 0.25), label={"text": "LIFE LEFT, IN AIRPORTS: 50%", "color": "red"})
shot("You'd die somewhere over the Pacific, watching a movie you didn't even pick.",
     cast=hero("flat", 0.3), impact={"word": "Pacific", "flash": "white", "shake": 0.3})
shot("So the big trips are out. But here's the strange part.", cast=hero("calm", 0.3))
shot("Even if you could teleport to Tokyo, scientists think you probably wouldn't want to go.", cast=hero("shock", 0.3),
     label={"text": "WAIT, WHAT?", "color": "gold"})
shot("Hold that thought. First, there's something boring you have to deal with.", cast=hero("awkward", 0.3))

# ---------------------------------------------------------------- chapter 4
shot("Hour six.", chapter={"num": 4, "title": "THE PAPERWORK"}, scene="home_day", cast=hero("flat", 0.3), clock="42:00:00", music="light")
shot("Do you have a will?", cast=hero("awkward", 0.3), impact={"word": "will", "flash": "white", "shake": 0.2})
shot("If you're Canadian, there's a good chance you don't. In a 2024 survey, forty-three percent said they had no will.",
     bars={"title": "CANADIANS WITH NO WILL (2024)", "rows": [
         {"name": "NO WILL", "value": 43, "unit": "%", "hl": True},
         {"name": "HAVE A WILL", "value": 57, "unit": "%"}], "y": 280}, cast=hero("awkward", 0.12))
shot("Without one, you don't decide who gets your things. Your province's law does.", cast=hero("worried", 0.3),
     label={"text": "YOUR STUFF: DECIDED BY LAW", "color": "red"})
shot("So you write one. Then you hit the real problem: your phone.", cast=hero("calm", 0.3))
shot("Your photos, your messages, every account you own. All locked behind passwords only you know.",
     card={"title": "LOCKED FOREVER", "rows": [["Photos", "12,000+", "bad"], ["Messages", "LOCKED", "bad"],
                                               ["Accounts", "47", "bad"]]}, cast=hero("worried", 0.25))
shot("Apple, Google and Facebook all let you pick a legacy contact. Someone who can get in after you're gone.",
     cast=hero("calm", 0.3), label={"text": "SETTING: LEGACY CONTACT", "color": "gold"})
shot("Which raises a question you weren't ready for.", cast=hero("worried", 0.3))
shot("Who do you trust with everything?", cast=hero("shock", 0.3), impact={"word": "everything", "flash": "white", "shake": 0.3})
shot("You type one name without even thinking.", cast=hero("calm", 0.3))

# ---------------------------------------------------------------- chapter 4b: money
shot("Hour eight.", chapter={"num": 5, "title": "THE MONEY"}, scene="street_night", cast=hero("calm", 0.4), clock="40:00:00")
shot("Next problem: your savings. You can't take it with you. And you can't spend it fast enough.", cast=hero("worried", 0.4))
shot("Your first idea is a shopping spree. A sports car. The biggest TV in the store.", cast=hero("smug", 0.4),
     label={"text": "PLAN: BUY EVERYTHING", "color": "gold"})
shot("But a car you'll drive for one day is just a very expensive rental.", cast=hero("awkward", 0.4),
     label={"text": "PLAN: CANCELLED", "color": "red"})
shot("There's a better idea, from a psychologist right here in Vancouver.", cast=hero("calm", 0.4))
shot("In 2008, psychologists Elizabeth Dunn, Lara Aknin and Michael Norton handed people an envelope of cash in the morning.",
     scene="mind", cast=duo("calm", "scientist", "calm", 0.62, 0.3), label={"text": "THE ENVELOPE EXPERIMENT", "color": "dark"})
shot("Some had to spend it on themselves. Others had to spend it on someone else.", cast=duo("calm", "scientist", "smug", 0.62, 0.3))
shot("By the end of the day, the people who spent it on others were happier.", cast=duo("shock", "scientist", "smug", 0.62, 0.3),
     label={"text": "GIVING > BUYING", "color": "gold"})
shot("And the amount barely mattered. Five dollars worked about as well as twenty.", cast=duo("shock", "scientist", "calm", 0.62, 0.3))
shot("So you skip the car. You pay off your little sister's student loan.", scene="home_day", cast=hero("happy", 0.4))
shot("And you leave the guy at the coffee shop a three hundred dollar tip. He thinks it's a mistake.", cast=hero("happy", 0.4),
     label={"text": "TIP: 300 DOLLARS", "color": "gold"})
shot("It is not a mistake. It's the best thing you've bought in years.", cast=hero("happy", 0.4))

# ---------------------------------------------------------------- chapter 5
shot("Hour ten.", chapter={"num": 6, "title": "THE SWITCH"}, scene="mind", cast=hero("calm", 0.5), clock="38:00:00", music="tense")
shot("Remember the trip you wouldn't want to take? Here's why.", cast=hero("calm", 0.3))
shot("Psychologist Laura Carstensen has spent decades studying what happens when people feel their time is running out.",
     cast=duo("calm", "scientist", "calm", 0.62, 0.3), label={"text": "STANFORD: TIME & EMOTION", "color": "dark"})
shot("Older people tend to choose time with the people they already love over meeting someone new.", cast=duo("calm", "scientist", "smug", 0.62, 0.3))
shot("You might think that's just age. It isn't.", cast=duo("shock", "scientist", "smug", 0.62, 0.3))
shot("When young people are asked to imagine their time is limited, they start choosing exactly like older people do.",
     cast=duo("worried", "scientist", "calm", 0.62, 0.3), label={"text": "LESS TIME = FAMILIAR FACES", "color": "gold"})
shot("Researchers saw it in Hong Kong during the SARS outbreak, and in the US after 9/11.", cast=duo("calm", "scientist", "calm", 0.62, 0.3))
shot("And in the first year of COVID, around two out of three younger adults in one study picked a chat with family over someone new.",
     bars={"title": "WHO WOULD YOU RATHER TALK TO? (2020)", "rows": [
         {"name": "SOMEONE NEW", "value": 34, "unit": "%"},
         {"name": "FAMILY", "value": 66, "unit": "%", "hl": True}], "y": 280}, cast=hero("calm", 0.12))
shot("Your brain flips a switch. New experiences suddenly feel cheap. The people you already have feel priceless.",
     cast=hero("shock", 0.3), impact={"word": "switch", "flash": "white", "shake": 0.3})
shot("That's why Tokyo can wait forever.", cast=hero("calm", 0.3))
shot("You pick up your phone.", scene="home_day", cast=hero("calm", 0.3))

# ---------------------------------------------------------------- chapter 6
shot("Hour twelve.", chapter={"num": 7, "title": "THE CALLS"}, scene="home_day", cast=hero("calm", 0.3), clock="36:00:00", music="light")
shot("The first call is the hardest one. Your mom picks up on the second ring.", cast=duo("worried", "mom", "happy", 0.62))
shot("She thinks you're calling about dinner on Sunday.", cast=duo("awkward", "mom", "happy", 0.62))
shot("You don't tell her right away. You just let her talk about her week, and you listen to every word.",
     cast=duo("calm", "mom", "happy", 0.62), label={"text": "BEST CALL OF YOUR LIFE", "color": "gold"})
shot("Then you tell her.", cast=duo("worried", "mom", "shock", 0.62), impact={"word": "her", "flash": "white", "shake": 0.2})
shot("She is at your door in forty minutes.", cast=duo("worried", "mom", "worried", 0.58), kicker="HOUR 13")
shot("Now, the second call. And this is where the mistake comes in.", scene="mind", cast=hero("worried", 0.5), music="tense")
shot("Remember: almost everyone makes it.", cast=hero("worried", 0.5), label={"text": "THE MISTAKE", "color": "red"})
shot("Cornell psychologist Tom Gilovich studied what people regret.", cast=duo("calm", "scientist", "calm", 0.62, 0.3))
shot("In the short term, we regret the things we did. The embarrassing text. The bad haircut.", cast=duo("awkward", "scientist", "smug", 0.62, 0.3),
     label={"text": "SHORT TERM: WHAT YOU DID", "color": "dark"})
shot("But looking back over a whole life, the regrets that stick are the things we never did.",
     cast=duo("shock", "scientist", "calm", 0.62, 0.3), label={"text": "LONG TERM: WHAT YOU DIDN'T DO", "color": "red"})
shot("The trip you never took. The thing you never said.", cast=duo("worried", "scientist", "calm", 0.62, 0.3))
shot("The mistake is spending your last hours fixing small things you did, instead of doing the big things you never did.",
     cast=hero("shock", 0.5), impact={"word": "never", "flash": "black", "shake": 0.4})
shot("So the second call isn't to your bank.", scene="street_night", cast=hero("calm", 0.4), music="light")
shot("It's to the friend you stopped talking to three years ago. Over something so dumb neither of you remembers it.",
     cast=duo("awkward", "friend", "flat", 0.65, 0.32), kicker="HOUR 15", clock="33:00:00")
shot("You say sorry. He says sorry. Neither of you hangs up for two hours.", cast=duo("happy", "friend", "happy", 0.6, 0.35),
     label={"text": "FRIENDSHIP: RESTORED", "color": "gold"})
shot("Then you make a list of every sentence you've been saving for later. There is no later.",
     card={"title": "THINGS I NEVER SAID", "rows": [["Dad", "I'M PROUD OF YOU", "good"], ["Sis", "YOU WERE RIGHT", "good"],
                                                    ["Teacher", "YOU CHANGED MY LIFE", "good"]]}, scene="home_night",
     cast=hero("calm", 0.25), clock="30:00:00")
shot("You send every one of them.", cast=hero("happy", 0.25), impact={"word": "every", "flash": "white", "shake": 0.2})

# ---------------------------------------------------------------- chapter 7
shot("Hour twenty-four.", chapter={"num": 8, "title": "THE LAST DAY"}, scene="home_day", cast=duo("calm", "mom", "calm", 0.62), clock="24:00:00")
shot("Something weird happens on the last day. Nothing big happens. And it's perfect.", cast=duo("happy", "mom", "happy", 0.62))
shot("Breakfast with your mom. A walk around the block. Bad jokes with your friend.", cast=duo("happy", "friend", "happy", 0.62),
     label={"text": "SIDE QUESTS: COMPLETED", "color": "gold"})
shot("You notice things you walked past for years. The smell of rain. The guy at the coffee shop who always remembers your order.",
     cast=hero("calm", 0.4))
shot("You ask your mom to teach you her soup recipe. The one you always said you'd learn someday.",
     scene="home_day", cast=duo("calm", "mom", "happy", 0.62))
shot("Turns out someday takes forty minutes.", cast=duo("happy", "mom", "happy", 0.62), label={"text": "SOMEDAY: 40 MINUTES", "color": "gold"})
shot("Your friend shows you the dumb video that made you both cry laughing in grade nine. It's still funny.",
     cast=duo("happy", "friend", "happy", 0.62))
shot("You take zero photos. For once, you're not saving anything for later.", cast=hero("calm", 0.4))
shot("It feels like the first day you've actually been awake.", cast=hero("happy", 0.4))
shot("Hour forty-six. You don't want to sleep. Your friend drives you to a rooftop to watch the sunrise.",
     scene="rooftop_dawn", cast=duo("calm", "friend", "calm", 0.6, 0.4), clock="02:00:00", kicker="HOUR 46", music="tense")
shot("Neither of you says much. You don't need to.", cast=duo("calm", "friend", "calm", 0.6, 0.4))

# ---------------------------------------------------------------- chapter 8
shot("Hour forty-eight.", chapter={"num": 9, "title": "THE LAST SOUND"}, scene="home_night", cast=hero("calm", 0.5), clock="00:05:00")
shot("Here's one last thing scientists found.", cast=hero("calm", 0.5))
shot("In 2020, researchers at UBC in Vancouver recorded the brainwaves of patients in hospice care.", scene="clinic",
     cast=duo("calm", "scientist", "calm", 0.62, 0.3), label={"text": "UBC, 2020", "color": "dark"})
shot("Some were so close to death they could no longer respond to anything.", cast=duo("worried", "scientist", "calm", 0.62, 0.3))
shot("But when the researchers played sounds, some of their brains still responded, like a healthy person's. Even hours before death.",
     cast=duo("shock", "scientist", "calm", 0.62, 0.3), impact={"word": "responded", "flash": "white", "shake": 0.3},
     label={"text": "STILL LISTENING", "color": "gold"})
shot("The researchers are careful. They can't know if those patients understood anything.", cast=duo("calm", "scientist", "flat", 0.62, 0.3))
shot("But it means the people you love should keep talking. Right to the end.", scene="home_night", cast=duo("calm", "mom", "worried", 0.62))
shot("So your mom talks. About the day you were born. About Sunday dinner.", cast=duo("calm", "mom", "calm", 0.62), clock="00:00:30")
shot("And maybe, you hear every word.", cast=duo("calm", "mom", "calm", 0.62), clock="00:00:05",
     impact={"word": "word", "flash": "black", "shake": 0.0})

# ---------------------------------------------------------------- twist + CTA
shot("Here's the twist.", scene="mind", cast=hero("calm", 0.5), clock=None, music="light")
shot("Your clock is already running. You just can't see the numbers.", cast=hero("shock", 0.5),
     label={"text": "TIME LEFT: ??:??:??", "color": "red"}, impact={"word": "running", "flash": "white", "shake": 0.3})
shot("Forty-eight hours just makes you do now what you were saving for later.", cast=hero("calm", 0.5))
shot("So, who would you call first? Tell me in the comments.", scene="home_day", cast=hero("happy", 0.4),
     label={"text": "WHO'S YOUR FIRST CALL?", "color": "gold"})
shot("And maybe send this video to them. Today, while there's still a later.", cast=hero("happy", 0.4),
     label={"text": "SEND THIS TO YOUR FIRST CALL", "color": "gold"})

long = {"title": "What if you only had 48 hours to live?", "format": "landscape", "voice": "am_michael", "speed": 1.0,
        "gap": 0.32, "music": "tense", "sources": SOURCES, "shots": S}
(HERE / "48-hours.json").write_text(json.dumps(long, indent=1, ensure_ascii=False))

# ---------------------------------------------------------------- 60-second vertical cut
V = []


def v(text, **kw):
    V.append({"text": text, **kw})


def v_(**kw):
    V.append(kw)


v_(clock='48:00:00', text="You have forty-eight hours to live.", scene="clinic", cast=[{"who": "hero", "x": 0.3, "mood": "shock"}, {"who": "doctor", "x": 0.72, "mood": "flat"}],
  impact={"word": "live", "flash": "white", "shake": 0.5}, label={"text": "TIME LEFT: 48 HOURS", "color": "red"})
v_(clock='47:30:00', text="Plan A: never sleep. Bad plan.", scene="mind", cast=[{"who": "hero", "x": 0.5, "mood": "smug"}], label={"text": "PLAN A: NO SLEEP", "color": "gold"})
v_(clock='46:00:00', text="After 24 hours awake, your brain works like a blood alcohol of point one. Over the legal limit.",
  bars={"title": "HOW IMPAIRED YOU ARE", "rows": [{"name": "LEGAL LIMIT", "value": 0.08, "unit": "%", "decimals": 2},
                                                 {"name": "YOU, 24 H AWAKE", "value": 0.10, "unit": "%", "decimals": 2, "hl": True}]},
  cast=[{"who": "hero", "x": 0.5, "mood": "sick"}])
v_(clock='45:00:00', text="Plan B: Tokyo. Ten hours in the air. Each way. You'd die watching an airplane movie.", scene="home_day",
  cast=[{"who": "hero", "x": 0.5, "mood": "awkward"}], label={"text": "PLAN B: CANCELLED", "color": "red"})
v_(clock='44:00:00', text="But science says you wouldn't want to go anyway.", cast=[{"who": "hero", "x": 0.5, "mood": "shock"}],
  impact={"word": "anyway", "flash": "white", "shake": 0.3})
v_(clock='40:00:00', text="When time feels short, people stop wanting new things. They want the people they already love.", scene="mind",
  cast=[{"who": "hero", "x": 0.5, "mood": "calm"}], label={"text": "LESS TIME = FAMILIAR FACES", "color": "gold"})
v_(clock='38:00:00', text="Plan C: buy a sports car. For one day. That's just a very expensive rental.", scene="street_night",
  cast=[{"who": "hero", "x": 0.5, "mood": "smug"}], label={"text": "PLAN C: CANCELLED", "color": "red"})
v_(clock='36:00:00', text="In one famous experiment, people who spent even five dollars on someone else were happier by the end of the day than people who spent it on themselves.",
  scene="mind", cast=[{"who": "hero", "x": 0.5, "mood": "shock"}], label={"text": "GIVING > BUYING", "color": "gold"})
v_(clock='30:00:00', text="And over a lifetime, our biggest regrets are the things we never did. Never said.",
  cast=[{"who": "hero", "x": 0.5, "mood": "worried"}], label={"text": "REGRET #1: WHAT YOU DIDN'T DO", "color": "red"})
v_(clock='20:00:00', text="So you call your mom. You call the friend you stopped talking to. You say everything.", scene="home_night",
  cast=[{"who": "hero", "x": 0.3, "mood": "calm"}, {"who": "mom", "x": 0.72, "mood": "happy"}])
v_(clock='00:00:10', text="Researchers in Vancouver even found that some dying patients' brains still responded to sound, hours before the end. So keep talking.",
  cast=[{"who": "hero", "x": 0.3, "mood": "calm"}, {"who": "mom", "x": 0.72, "mood": "calm"}], label={"text": "STILL LISTENING", "color": "gold"})
v_(clock=None, text="Here's the twist. Your clock is already running. You just can't see the numbers.", scene="mind",
  cast=[{"who": "hero", "x": 0.5, "mood": "shock"}], label={"text": "TIME LEFT: ??:??:??", "color": "red"},
  impact={"word": "running", "flash": "white", "shake": 0.3})
v_(clock=None, text="Who would you call first? Send this to them.", scene="home_day", cast=[{"who": "hero", "x": 0.5, "mood": "happy"}],
  label={"text": "SEND THIS TO YOUR FIRST CALL", "color": "gold"})

short = {"title": "What if you only had 48 hours to live? (Short)", "format": "vertical", "voice": "am_michael", "speed": 1.12,
         "gap": 0.1, "music": "tense", "sources": SOURCES, "shots": V}
(HERE / "48-hours-short.json").write_text(json.dumps(short, indent=1, ensure_ascii=False))
print(len(S), "long shots,", sum(len(s["text"].split()) for s in S), "words;", len(V), "short shots,",
      sum(len(s["text"].split()) for s in V), "words")
