# Agents never use the LinkedIn account

Agents, the Scout and the Watcher reach LinkedIn only as a guest, in a fresh
browser, never with the user's logged-in profile. Only the user's own `engines.play`
runs use the account. LinkedIn's User Agreement and robots.txt forbid automated
access, so the system can't be made compliant, only small. The account is the
only thing that can be banned, while a blocked guest run costs nothing. The daily
guest run also keeps its footprint small: it runs once, at a random time, loads
each page once, makes no retries, and stops at the first sign of a block.
