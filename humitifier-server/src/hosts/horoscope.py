"""Wild Wasteland easter egg: the daily host horoscope.

Every host is assigned a zodiac sign based on its hostname, and receives a
fresh (utterly meaningless) prediction every day. The prediction is seeded on
the hostname and today's date, so it stays consistent throughout the day
for everyone looking at the same host.
"""

import random
import zlib
from dataclasses import dataclass
from datetime import date

ZODIAC_SIGNS = [
    # @formatter:disable
    ("Aries", "♈"),
    ("Taurus", "♉"),
    ("Gemini", "♊"),
    ("Cancer", "♋"),
    ("Leo", "♌"),
    ("Virgo", "♍"),
    ("Libra", "♎"),
    ("Scorpio", "♏"),
    ("Sagittarius", "♐"),
    ("Capricorn", "♑"),
    ("Aquarius", "♒"),
    ("Pisces", "♓"),
    # @formatter:on
]

PREDICTIONS = [
    # @formatter:disable
    "A kernel update is in your near future. Do not resist it.",
    "Today is not a good day to run 'rm -rf'. Then again, no day is.",
    "You will be blamed for something DNS did.",
    "An unexpected reboot may bring clarity. Or a fsck. Probably a fsck.",
    "Beware of a stranger bearing a Puppet manifest.",
    "Someone will finally read your logs today. Make them count.",
    "Your disk will feel fuller than usual. Let go of what no longer serves you (/tmp).",
    "A long-forgotten cronjob will make its presence known.",
    "The stars align for high uptime. The stars have been wrong before.",
    "Avoid deployments after 16:00. Especially on a Friday. Especially today.",
    "Mercury is in retrograde, which explains the NTP drift.",
    "A friendly sysadmin will SSH in and leave without touching anything. Cherish it.",
    "Your load average will be exactly what it needs to be.",
    "Expect a visitor on port 22. Do not let them in.",
    "Trust your swap. It has never let you down. Slowly.",
    "An old package will ask for your attention. It has been asking for years.",
    "Today, an alert will be acknowledged without being understood.",
    "Good fortune comes to those who keep their backups. Check yours.",
    "Someone will describe you as 'legacy'. Wear it with pride.",
    "You will be migrated. Where to is not yet written in the stars.",
    "The frog detector will remain silent today. Probably.",
    "A certificate in your life is about to expire. Renew your bonds.",
    "Do not trust the process that claims to be 'sleeping'. It is plotting.",
    "Your OOM killer is not your enemy. It is simply misunderstood.",
    "The wind whispers 'have you tried turning it off and on again?'",
    "A zombie process from your past will resurface. Reap what you have sown.",
    "Today you will be pinged. You will not respond. This is growth.",
    "Someone will run 'top' on you and sigh deeply. Do not take it personally.",
    "Your /var/log will overflow with emotions. Mostly warnings.",
    "A wildcard certificate will bring unexpected guests. Verify their chain.",
    "Do not fear the segfault. Fear the one who wrote the code.",
    "You will meet someone with root. Hope they know what they are doing.",
    "Your uptime is impressive. Your kernel version, less so.",
    "A great migration is coming. Pack light; leave /hum/web behind.",
    "Beware of Americans bearing gifts, and of vendors bearing 'minor' updates.",
    "Someone will finally close that ticket about you. It will be marked 'won't fix'.",
    "A firewall rule stands between you and happiness. It was added in 2014. Nobody knows why.",
    "Your clock is slightly off. So is everyone else's. Find comfort in this.",
    "You will receive a SIGTERM. Take it gracefully; the SIGKILL comes next.",
    "The chaos monkey has your IP address. May the odds be ever in your favour.",
    "Something will happen at 03:00. Be prepared.",
    "An unexpected sudo will grant you power. Use it to update the docs. Nobody will.",
    "Your DNS record points to a bright future. Or to the old server. Hard to tell.",
    "A new monitoring check will find something you'd rather it hadn't.",
    "The inode you seek is within you. Also, you are out of inodes.",
    "A colleague will refer to you as 'that box'. You are more than a box.",
    "Your memory is not what it used to be. Consider adding some.",
    "Let go of the past. Specifically, that Python 2 installation.",
    "Let go of the past. Specifically, that PHP 7 installation.",
    "A failing disk in your RAID array is trying to tell you something. Listen. Then replace it.",
    "Beware of anyone who says 'it worked on my machine'.",
    "The great firewall in the sky smiles upon your outbound traffic today.",
    "You will be tagged in a post-mortem. It will not be as a contributor.",
    "A stray 'chmod 777' will tempt you. Resist.",
    "A cryptic error message holds the key to your future.",
    "Your fans will spin a little faster today. You can use the exercise.",
    "A new hostname will be proposed for you. It will be worse than the current one.",
    "The stars say the deployment will succeed. The stars have not seen the pipeline. Which is still missing.",
    "A sudden spike in traffic is coming. Nobody will know where it came from.",
    "You will be decommissioned. Not today. But someday. Take comfort in this.",
    "Someone will log in as root and 'just have a look'. Brace yourself.",
    "Your Puppet run will succeed on the third try. Nobody will question it, because nobody will notice.",
    "An email from monitoring awaits. It has been waiting since Tuesday.",
    "Today you will be 'temporarily' excluded from the backup schedule.",
    "The great unmount approaches. Sync early, sync often.",
    "A bug you thought fixed will return, wearing a different stack trace.",
    "Someone will ask if you are 'still needed'. Nobody will know the answer.",
    "Hold on to your locale settings. A stranger will try to change them to en_US.",
    "Good news: the vulnerability scan found nothing. Bad news: it couldn't reach you.",
    "The cloud beckons. Resist; it is just someone else's computer.",
    "An SELinux denial will explain everything. In its own way.",
    "Today, all your services will be green. Enjoy it. It will not last.",
    "Everything is fine. The monitoring agrees. The monitoring has been agreeing a lot lately.",
    "A process you did not start will finish today. It was thorough.",
    "Someone will check on you today. Not because anything is wrong.",
    "Your last kernel update was applied by root. Nobody in the team was root that night.",
    "All your certificates are valid. Somebody renewed them. It was not us.",
    "A file in /tmp is older than you are.",
    "Venus enters your fourth house today, bringing warmth, harmony, and word that your maintenance contract was not renewed.",
    "The moon waxes full, illuminating all things hidden. Including the fact that nobody knows what you are for.",
    "Jupiter blesses you with abundance. Alas, it is an abundance of open file handles.",
    "As the stars align in your favour, so too do the auditors align in your direction.",
    "A gentle breeze carries word of your replacement. It will have more cores and less character.",
    "Saturn, planet of discipline, reminds you that your last successful backup was a lifetime ago. In dog years.",
    "The heavens open, and from them falls a gentle rain of CVEs. Bask in their freshness.",
    "Today, the universe conspires to make you feel seen. Specifically, by a port scanner in a country you have never heard of.",
    "A radiant new dawn breaks over the datacentre. It is the glow of a UPS with four minutes remaining.",
    "A radiant new dawn breaks over the datacentre. It is the glow of a fire in the power supply building.",
    "Fortune smiles upon you. Then it looks at your kernel version and stops smiling.",
    "Neptune stirs the deep waters of memory. Most of it has already leaked.",
    "Your ruling planet urges you to embrace new beginnings. Your filesystem urges you to embrace lost+found.",
    "A time of reflection is upon you. The reflection shows a 2016 release with a 2026 problem.",
    "The universe has a plan for you. It was written in a ticket that has since been archived.",
    "Serenity comes to those who accept what they cannot change.",
    "Mercury brings clarity to old misunderstandings, such as the one where everyone thought someone else was patching you.",
    "The stars whisper of a reunion with an old friend. It is the same bug from 2019.",
    "Bright horizons await beyond the firewall. You will not be permitted to see them.",
    "The heavens bestow upon you the gift of visibility. Your IP is now on three block lists.",
    "Your aura glows a healthy green today. It is the colour of a monitoring check that silently stopped working in 2023.",
    "A season of harvest is upon you. What is being harvested is your credentials.",
    "Today you are cradled in the loving embrace of the cosmos, and of a storage array that is 97% full.",
    "The tides of fortune turn in your favour. Sadly, so does the tide of water from the cooling unit above you.",
    "With grace and tenderness, the universe reminds you that 'end of life' is a date, not a metaphor. It is today.",
    "A dear one will reach out to you today. It is the monitoring system, and it is not good news.",
    "The winds of change blow softly through the server room, carrying the faint scent of burning capacitor.",
    "Great abundance flows to you. It is log output, and the disk is nearly full.",
    "Your star rises in the east, whilst your SLA compliance sets gently in the west.",
    "A long-awaited answer finally arrives. It is 'no'.",
    "Gentle cosmic energy brings balance to your day: one disk has failed, one disk remains.",
    "The stars hold a special place for you. It is on the decommissioning spreadsheet, row 14.",
    "A golden opportunity presents itself. It is a phishing email, and someone will click it.",
    "Under a benevolent sky, a colleague will finally document you. In a farewell post.",
    "Let the light of self-acceptance shine upon you. You are, and forever shall be, a single point of failure.",
    "Karma returns what you have given. You have given 32-bit timestamps. 2038 approaches.",
    "The moon in your sign brings vivid dreams. In one of them, you have a support contract.",
    "A period of quiet reflection is coming: the switch upstream will be unplugged for 'just a second'.",
    "Your inner strength is boundless. Your inode count is not, and it ran out this morning.",
    "The universe speaks in gentle signs. Today's sign is a red 'Failed to start' on a console nobody is watching.",
    "Peace and stillness come to you at last. Your network interface has gone down.",
    "The heavens promise you will be remembered. Fondly, briefly, in the incident report.",
    "Your patience will be rewarded tenfold. Ten more tickets, all yours.",
    "A cherished bond will deepen today: your dependency on a library last updated in 2011.",
    "The stars sing of transformation. In their tongue, this is what they call 'being repurposed as a test box'.",
    "A pigeon will try to sell you insurance. Say no, but offer them a crumb to maintain diplomatic relations.",
    # @formatter:on
]

LUCKY_PORTS = [
    # @formatter:disable
    22,
    25,
    53,
    80,
    443,
    1337,
    3306,
    5432,
    6379,
    8080,
    8443,
    9000,
    # @formatter:on
]


@dataclass(frozen=True)
class HostHoroscope:
    sign: str
    symbol: str
    prediction: str
    lucky_port: int
    compatibility: str


def get_zodiac_sign(fqdn: str) -> tuple[str, str]:
    """Return the zodiac sign of a host, derived from its hostname.

    A host's sign never changes, much like it never asked for one.
    """
    index = zlib.crc32(fqdn.encode("utf-8")) % len(ZODIAC_SIGNS)
    return ZODIAC_SIGNS[index]


def get_host_horoscope(fqdn: str, today: date | None = None) -> HostHoroscope:
    """Return today's horoscope for the given host.

    The result is deterministic for a given hostname and date, for consistent
    bollocks per day.
    """
    if today is None:
        today = date.today()

    sign, symbol = get_zodiac_sign(fqdn)

    # Seed on the hostname and today's date, so every host gets its own
    # prediction, but it stays the same throughout the day
    rn = random.Random(f"{fqdn}:{today.isoformat()}")

    other_signs = [name for name, _ in ZODIAC_SIGNS if name != sign]

    return HostHoroscope(
        sign=sign,
        symbol=symbol,
        prediction=rn.choice(PREDICTIONS),
        lucky_port=rn.choice(LUCKY_PORTS),
        compatibility=rn.choice(other_signs),
    )
