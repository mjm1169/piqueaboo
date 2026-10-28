# Card text — pills, tags and headlines

Every roster card's three lines, captured from the live page. Edit the text
under each `[id]` and hand the file back; I'll put them into the HTML.

**The tag only appears where you've written a headline.** A card with a
headline of your own shows all three lines; the five without show just the
headline and the sim number, because the generic headline already names the
story and the tag would only repeat it. Write a headline for one of those five
and its tag starts showing automatically.

**Leave the `[id]` lines alone** — that's how I match each one up. `{{team}}`
is filled in live with the club's name, so keep it spelled exactly.

The three lines appear like this:

```
[ Longest winning streak ]     <- PILL, the button on the roster card

A WINNING STREAK FOR ARSENAL   <- TAG, small line atop the opened card
Arsenal win the league         <- HEADLINE
Sim #833,296
```

---

## Pills and tags, by story kind

These are shared, so editing one changes every club listed with it.

### Longest winning streak

*Used by: Arsenal*

[pill.longest-winning-streak]
Longest winning streak

[tag.longest-winning-streak]
A winning streak for {{team}}

### Highest-scoring golden boot

*Used by: Manchester City*

[pill.highest-scoring-golden-boot]
Highest-scoring golden boot

[tag.highest-scoring-golden-boot]
A golden boot for {{team}}

### Worst-ever finish

*Used by: Manchester United*

[pill.worst-ever-finish]
Worst-ever finish

[tag.worst-ever-finish]
A relegation for {{team}}

### Title decided by tiebreak

*Used by: Liverpool, Chelsea, Newcastle United*

[pill.title-decided-by-tiebreak]
Title decided by tiebreak

[tag.title-decided-by-tiebreak]
A tiebreak title for {{team}}

### Most unexpected golden boot

*Used by: Bournemouth*

[pill.most-unexpected-golden-boot]
Most unexpected golden boot

[tag.most-unexpected-golden-boot]
A surprise golden boot for {{team}}

### See a league win

*Used by: Brighton, Brentford, Tottenham, Everton, Fulham*

[pill.see-a-league-win]
See a league win

[tag.see-a-league-win]
A league win for {{team}}

### Lowest goal difference to win it

*Used by: Leeds*

[pill.lowest-goal-difference-to-win-it]
Lowest goal difference to win it

[tag.lowest-goal-difference-to-win-it]
A title on the finest margin for {{team}}

### Big individual haul

*Used by: Crystal Palace*

[pill.big-individual-haul]
Big individual haul

[tag.big-individual-haul]
A big individual haul for {{team}}

### High-scoring game

*Used by: Aston Villa*

[pill.high-scoring-game]
High-scoring game

[tag.high-scoring-game]
A high-scoring game for {{team}}

### Fewest title wins

*Used by: Nottingham Forest*

[pill.fewest-title-wins]
Fewest title wins

[tag.fewest-title-wins]
A rare title for {{team}}

### Best-ever finish

*Used by: Burnley, Sunderland, West Ham, Wolverhampton Wanderers*

[pill.best-ever-finish]
Best-ever finish

[tag.best-ever-finish]
A best-ever finish for {{team}}

---

## Headlines, one per card

These are yours already, except where flagged.

[headline.arsenal]  (Longest winning streak)
Arsenal win the league

*⚠ No headline of your own for Arsenal yet, so this card currently shows two lines — headline and sim number, no tag.*

[headline.manchester-city]  (Highest-scoring golden boot)
Haaland's spectacular season

[headline.manchester-united]  (Worst-ever finish)
A giant gets relegated

[headline.liverpool]  (Title decided by tiebreak)
A close finish

[headline.bournemouth]  (Most unexpected golden boot)
An unexpected Golden Boot

[headline.chelsea]  (Title decided by tiebreak)
An ever closer finish

[headline.brighton]  (See a league win)
The Seagulls soar

[headline.brentford]  (See a league win)
The Bees rack up the points

[headline.leeds]  (Lowest goal difference to win it)
A seemingly impossible victory

[headline.newcastle-united]  (Title decided by tiebreak)
Another narrow victory

[headline.crystal-palace]  (Big individual haul)
Mateta's day out

[headline.aston-villa]  (High-scoring game)
A 15-goal Villa thriller

[headline.tottenham]  (See a league win)
Spurs do more than avoid the drop

[headline.everton]  (See a league win)
20 in a million

[headline.fulham]  (See a league win)
3 in a million

[headline.nottingham-forest]  (Fewest title wins)
1 in a million

[headline.burnley]  (Best-ever finish)
Burnley’s best-ever finish

*⚠ No headline of your own for Burnley yet, so this card currently shows two lines — headline and sim number, no tag.*

[headline.sunderland]  (Best-ever finish)
Sunderland’s best-ever finish

*⚠ No headline of your own for Sunderland yet, so this card currently shows two lines — headline and sim number, no tag.*

[headline.west-ham]  (Best-ever finish)
West Ham’s best-ever finish

*⚠ No headline of your own for West Ham yet, so this card currently shows two lines — headline and sim number, no tag.*

[headline.wolverhampton-wanderers]  (Best-ever finish)
Wolves’ best-ever finish

*⚠ No headline of your own for Wolverhampton Wanderers yet, so this card currently shows two lines — headline and sim number, no tag.*

