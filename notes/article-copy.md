# Article copy — both articles, in one editable file

Everything below is the reader-facing prose from `articles/pl-xg-simulator.html`
and `articles/due-date.html`. Edit the text freely and hand this file back;
I'll put each block into the right place in the HTML.

**Two things to leave alone:**

1. **The `[id]` line above each block.** That's how I find where the text goes.
   Don't rename or delete them. If you want to cut a block entirely, write
   `(delete)` as its text rather than removing the heading.
2. **Anything in `{{double braces}}`.** Those are numbers computed live from the
   simulation data at page load, so they can never go stale. Move them around in
   a sentence as you like, but keep the spelling exactly. Each one's current
   real value is shown in brackets after the block.

Text in `(round brackets)` that reads like a note to yourself — `xxx`,
`(insert examples here)` — is still outstanding; fill it in or tell me to cut it.

---

# ARTICLE 1 — One in a million Premier Leagues

## Intro

[pl.h1]
One in a million Premier Leagues

[pl.meta]
25 October 2026 · Reading time: 8 mins

*New. 8 mins = the main scroll-through prose (800 words) plus the club card
write-ups (877 words) at ~230wpm, which lands at 7.3 and rounds up given how
much of this piece is scrolling and clicking rather than reading. Say if
you'd rather it read 6 (straight read-through, skipping the cards) or
something else.*

[pl.intro.h2]
What is xG?

[pl.intro.p1]
If you've clicked on this there's a pretty good chance you'll be familiar with the concept of xG anyway, so I'll keep this bit short.

[pl.intro.p2]
Every time a shot is taken in a football game, a probability is calculated that is associated with it. This represents the probability that that shot would result in a goal. A tap-in from a yard out would have a very high xG, close to 1, and a speculative hit from 35 yards out would have a low xG, close to 0.

[pl.intro.p3]
Naturally, there are times when the outcome of a game doesn't go the way the xG would suggest. A team may score from a rare, low quality effort on goal, while their opponents fail to convert any of their more numerous, better chances. You'd expect this sort of thing to even over the course of a season, but have you ever wondered, "What if…?".

[pl.intro.p4]
What if a relegation candidate kept scoring from half-chances all season? Could they win the league?

[pl.intro.p5]
It is an article for the dreamers. Based on the 2025/26 season, supporters of your Wolves, your West Hams and your Burnleys will no doubt have giddy highs at the thought their season could have ended with European football rather than being demoted to the Championship.

[pl.intro.datainfo.summary]
A quick note on the data

[pl.intro.datainfo.li1]
Data is taken from Understat.

[pl.intro.datainfo.li2]
Shots are treated as independent of each other. In real life, game-management would come into play, but for a bit of fun such as this we will suspend disbelief.

[pl.intro.datainfo.li3]
Own goals don't get an xG in Understat, sparing the blushes of millions of players in this article.

[pl.intro.datainfo.li4]
League position tie-breaks are done on goal difference, goals for, head-to-head record, away goals in head-to-head, then a virtual coin toss. (A play-off would have replaced this in real life.)

---

## Section — re-rolling the first game

[pl.game.h2]
What could have been in the first game?

[pl.game.intro]
The first game of the season saw Bournemouth take on Liverpool at Anfield. There were shots aplenty, but how could it have played out differently? Here are all the shots, what happened in the actual game, and what happened in simulation #{{sim_number}}.

*Resolved — currently reads #10,917, and it's a real one. Of the million
simulations, 16 play this match out exactly as shown here, shot for shot, so the
commentary stays true. #10,917 is the lowest of them; #235660 is a Manchester
United title season and #220032 / #485151 are Manchester City ones if you'd
rather it foreshadowed something.*

### Commentary rows in the shot log

These appear as italic asides between the shot rows, each anchored to a specific
shot. The `@ 2' Hugo Ekitike` line says which shot it appears after — keep those
as they are.

[pl.game.kickoff]
Kick off!

[pl.game.comment.2-Hugo Ekitike]
In just the second minute, Ekitike has a speculative shot from outside the box saved. Just a 1% chance of that going in.

[pl.game.comment.5-Antoine Semenyo]
Semenyo has a good chance. He missed in real life, but tucks it away in our simulation.

[pl.game.comment.36-Hugo Ekitike]
Two good chances for both sides. In our simulation, Tavernier puts Bournemouth 0-2 up, while in real life his shot is saved, only for Ekitike to fire Liverpool into a 1-0 lead.

[pl.game.comment.48-Cody Gakpo]
Gakpo converts a 0.10 xG chance to double Liverpool's real-life advantage.

[pl.game.comment.63-Antoine Semenyo]
Semenyo scores a high (0.43 xG) probability chance in both real-life and the simulation.

[pl.game.comment.75-Antoine Semenyo]
And again! Not a great chance, but Semenyo equalises in real-life, and completes a hat-trick in our re-run.

[pl.game.comment.87-Cody Gakpo]
Gakpo grabs a simulated consolation goal.

[pl.game.comment.93-Mohamed Salah]
A grandstand finish in real-life. Liverpool score two late on through Chiesa and Salah to walk out 4-2 winners.

### Closing summary

[pl.game.summary]
The game saw {{home_team}} take {{home_shots}} shots with a combined xG of {{home_xg}}, and {{away_team}} take {{away_shots}}, with an xG of {{away_xg}}. But simulating all the shots again, a very different result could have happened. So what if we did that for the 379 other games in that season?

*Currently reads: Liverpool / 19 shots / 2.33 xG; Bournemouth / 10 shots / 1.57 xG.*

---

## Section — simulating the whole season

[pl.season.h2]
Simulating a season

[pl.season.intro]
Let's go a step further and replay every shot from every game for the entire season. We can see our Liverpool vs. Bournemouth result in gameweek 1, as well as nine other replayed games.

[pl.season.after5]
After 5 games, there are a few surprises at the top of the table with Bournemouth having a 100% record and Leeds in the Champions League spots.

[pl.season.midskip]
A further {{n_gameweeks}} gameweeks pass, taking us to the business end of the season. As the season nears a close, Chelsea move into top spot....

*Currently reads: 28 gameweeks. This is the block the table pauses on while the skipped middle of the season scrolls past.*

[pl.season.midskip.label]
…{{n_gameweeks}} mid-season games later…

*The short label shown on the sticky table itself while the above is on screen.*

[pl.season.exit]
...and after a battle with Manchester City, win the league on the last day of the season, despite losing 4-1 away to Sunderland.

[pl.season.summary]
The same {{total_shots}} shots in the season, each with the same chance of going in (depending how much faith you have in xG) but a very different result. This is the nature of a low-scoring sport like football, games can pivot on just a few things playing out differently. Of the {{n_matches}} games played in the season {{same_scoreline_pct}}% had the same exact scoreline and {{same_result_pct}}% had the same W/D/L outcome.

*Currently reads: 9,524 shots; 380 games; 10.5% same scoreline; 48.9% same result.*

---

## Section — the million-simulation treemap

[pl.treemap.h2]
A million alternate Premier League realities

[pl.treemap.p1]
That was one season. It turned out very differently, but still, a 'big' team won it. So let's go a step further, or rather, 999,999 step further.

[pl.treemap.p2]
Many simulated shots, games and seasons later, here is how the league ended up all 1,000,000 times.

[pl.treemap.p3]
Let's explore the highlights.

[pl.treemap.backbtn]
← Back

---

## Club highlight cards — titles

These are the headlines on each club's story card.

[pl.title.Arsenal]
A 3-way final day fight

[pl.title.Manchester City]
Haaland's spectacular season

[pl.title.Manchester United]
A giant gets relegated

[pl.title.Liverpool]
A close finish

[pl.title.Chelsea]
An ever closer finish

[pl.title.Bournemouth]
An unexpected Golden Boot

[pl.title.Brighton]
The Seagulls soar

[pl.title.Brentford]
The Bees rack up the points

[pl.title.Leeds]
A seemingly impossible victory

[pl.title.Newcastle United]
Another narrow victory

[pl.title.Tottenham]
Spurs do more than avoid the drop

[pl.title.Everton]
20 in a million

[pl.title.Fulham]
3 in a million

[pl.title.Nottingham Forest]
1 in a million

[pl.title.Crystal Palace]
Mateta's day out

[pl.title.Aston Villa]
A 15-goal Villa thriller

The four clubs that never win a title keep an auto-generated title
("Burnley's best-ever finish", etc.) rather than one of their own. Say the word
if you'd like to name those too.

*One thing worth a decision: Wolves' reads "Wolverhampton Wanderers's best-ever
finish" — a doubled possessive, because the club name already ends in an "s".
Tell me how you'd like it and I'll fix it.*

---

## Club highlight cards — the write-ups

[pl.note.Arsenal.before]
Arsenal won {{arsenal_pct}}% of our million simulations including this simulation which went down to the final day. Fighting with Manchester City and Manchester United going into the final gameweek...

*Currently reads: 71.7%. This paragraph sits above the two tables.*

[pl.note.Arsenal.after]
...Arsenal thump Crystal Palace 0-7 away from home to clinch one of their {{arsenal_titles}} titles.

*Currently reads: 716,922. This paragraph sits below the two tables.*

[pl.note.Manchester City]
{{player}} won the Golden Boot (most league goals in the season) award in real-life with {{real_goals}} for the season. In this simulation, City ran out winners thanks to {{sim_goals}} goals from the Norwegian. He had his shooting boots amassing {{hat_tricks}} hat-tricks (including {{four_goal}} four-goal haul and {{five_goal}} five-goal matches). With a shot conversion rate of {{conversion_pct}}% he exceeded his xG by {{xg_excess}}.

*Currently reads: Erling Haaland / 27 real goals / 50 sim goals / 7 hat-tricks / 1 four-goal / 2 five-goal / 40.0% / +21.18. The plurals on "hat-tricks", "haul" and "matches" adjust themselves to the numbers.*

[pl.note.Manchester City.footnote]
Footnote: interestingly, {{team}} suffered a shock relegation in one of our 1 million simulations, despite having better shot quality in most of their games. [See it in the treemap →]

*The bracketed part is a clickable link that zooms the treemap to that exact simulation.*

[pl.note.Manchester United]
Though Man United won {{manutd_pct}}% of the simulations, they did get relegated in {{manutd_relegations}} replays, including this 19th placed finish. Despite winning 4 of their last five games, 39pts wasn't enough to save them

*Currently reads: 3.4% / 70 replays.*

[pl.note.Liverpool]
Liverpool won the title in {{liverpool_pct}}% of simulations, including this particularly tight one. It was a three-way tie at the top. Unable to be separated from Man City on goal difference, head-to-head record was used to split them, giving Liverpool the title.

*Currently reads: 0.9%.*

[pl.note.Chelsea]
Chelsea managed over 3,000 league wins. Perhaps the closest was this one. A three-way tie on points with Man City and Man United, and the same goal difference and goals scored as City, the season went to head-to-head record. Since this was tied on aggregate, away goals was used to split them, handing Chelsea a title.

Footnote: there were simulations closer than this. Two of Arsenals simulated win came as a result of a virtual coin toss. Tied on point, goal difference, goals for, and with unsplitable on head-to-head, they were split randomly. In real life, a play-off would have determined the winner. See it in the treemap.

[pl.note.Bournemouth]
{{team}} won {{title_odds_pct}}% of our simulations (more than perhaps you'd think). One surprise was this simulation, where they didn't win the title but {{player}} took a surprise Golden Boot, with a {{goals}}-goal haul for the season, {{diff}} more than he managed to amass in real-life and outperforming his xG by {{xg_excess}}.

*Currently reads: Bournemouth / 0.8% / Evanilson / 24 goals / 18 more / +12.18.*

[pl.note.Everton]
Everton came out on top 20 times. They won this season by 4 points, despite hitting a rocky patch mid-campaign.

[pl.note.Chelsea.footnote]
Footnote: there were simulations closer than this. Two of Arsenal's simulated wins came as a result of a virtual coin toss. Tied on points, goal difference, goals for, and unsplittable on head-to-head, they were split randomly. In real life, a play-off would have determined the winner. [See it in the treemap →]

*Your wording, with four plain typos fixed in transcription: "Arsenals" →
"Arsenal's", "simulated win" → "simulated wins", "Tied on point" → "Tied on
points", "unsplitable" → "unsplittable". I also dropped a stray "with" from
"and with unsplitable on head-to-head" — say the word and I'll put it back.
Every claim checked against the data: exactly two coin-flip titles, Arsenal
won both, and both were level on points, goal difference and goals for.
The bracketed part is the clickable link (it keeps the arrow and loses the
full stop, matching Manchester City's footnote); it goes to sim #129,326,
Arsenal v Manchester United. The other is #498,845, Arsenal v Liverpool.
Unlike the other notes, the "Two" here is literal rather than read from the
data, since it's written as a word — fine as long as the sims aren't
regenerated.*

[pl.note.Brighton]
Brighton may not have won many of our simulations but they won this iteration comfortably after a remarkable string of results in the first half of the season.

[pl.note.Brentford]
Brentford won 12 in a row after losing their opener in the season, amassing 91pts in this one of their 0.1% of titles.

[pl.note.Leeds]
Leeds' most remarkable simulated league win came when they managed to clinch the title with only 70pts and a negative goal difference. A bunched top five helped them as well as winning by narrow margins. Their average margin of victory was {{avg_win_margin}} goals while their average margin of defeat was {{avg_loss_margin}}.

*Currently reads: 1.4 goals / 3.2.*

[pl.note.Newcastle United]
Another away goals rule win here. This time Newcastle edging out Liverpool.

[pl.note.Tottenham]
Tottenham danced dangerously close to relegation in real-life but ran out as winners on {{tottenham_titles}} occasions here. In real life their GD was {{real_gd}}, against an xGD of {{expected_gd}}.

*Currently reads: 60 occasions / GD -9 / xGD -8.2.*

[pl.note.Fulham]
Fulham took 3 titles. Although they suffered 10 defeats, they took the title from Arsenal here.

[pl.note.Nottingham Forest]
A true one in a million. Nottingham Forest took this close title race with just 70 points.

[pl.note.Crystal Palace]
{{palace_titles}} of our simulations but the highlight here was in a season Manchester City won. At home to Bournemouth, Mateta notched up the biggest individual haul across the 380,000,000 games that were played out. He scored {{mateta_goals}} from {{mateta_shots}} shots.

*Currently reads: 414 / 10 goals / 11 shots. This card also lists every shot in the match underneath.*

[pl.note.Aston Villa]
{{villa_titles}} of the million simulations, but their highlight was this win over eventual champions Arsenal. A 15-goal thriller: Villa led 4-2 at half-time, only for Arsenal to level it at 4-4 through a quickfire Trossard brace, before Villa's late surge — six goals in the final half hour — saw them romp out 10-5 winners.

*Currently reads: 268. Worth knowing: your original note had Villa 5-3 up at half-time before Trossard's brace. I checked this sim's own minute-by-minute scorers and it was 4-2 at the break, with Trossard levelling at 4-4 — so I wrote the real numbers in. Happy to word it differently.*

[pl.note.Burnley]
With an xGD of {{burnley_xgd}}, Burnley were never going to stand much of a chance. The best they did was a 9th placed finish.

*Currently reads: -46.8.*

[pl.note.Sunderland]
Sunderland had a surprisingly good real-life season on their return to the Premier League. Their best simulated finish was when they finished runners up to Manchester City with 74pts (which would have been enough to win in other simulated seasons).

[pl.note.West Ham]
West Ham managed a 2nd place finish here as they were beaten to the title by Arsenal, returning a very respectable 76pts.

[pl.note.Wolverhampton Wanderers]
Wolves finished in the Champions League places in this season with an even goal difference (real-life {{wolves_gd}}; expected {{wolves_xgd}}).

*Currently reads: -41 / -30.3.*

---

## Card buttons and labels

The short label on each club's story button, and the tag line at the top of the
story card it opens.

[pl.tag.fewest_wins]
Fewest title wins

[pl.tag.no_wins]
Best-ever finish

[pl.tag.worst_finish]
Worst-ever finish

[pl.tag.relegation_footnote]
Shock relegation

[pl.tag.golden_boot]
Highest-scoring golden boot

[pl.tag.unexpected_golden_boot]
Most unexpected golden boot

[pl.tag.closest_final_week]
Closest race into the final day

[pl.tag.plain_league_win.pill]
See a league win

[pl.tag.plain_league_win.tag]
A league win for {{team}}

*The standard pair for the five cards whose story is simply "this club won
the league" — Brighton, Brentford, Tottenham, Everton and Fulham. The pill is
the button on the roster card; the tag is the small line above your headline,
which now names the club so the card's three lines say three different things.
"Largest winning margin" (below) is no longer used by any card.*

[pl.tag.biggest_margin]
Largest winning margin

[pl.tag.lowest_gd]
Lowest goal difference to win it

[pl.tag.most_tied_first]
Most teams tied for first

[pl.tag.closest_tiebreak]
Title decided by tiebreak

[pl.tag.high_scoring_game]
High-scoring game

[pl.tag.big_haul]
Big individual haul

---

## Section — simulate one yourself

[pl.sim.runbtn]
▶ Simulate a season

[pl.sim.h3]
From this replay

*This section has no heading or intro copy of its own yet — it jumps straight
from the treemap to the "Simulate a season" button. Worth a line or two if you
want one.*

---

---
---

# ARTICLE 2 — What is a due date?

## Intro

[dd.eyebrow]
A short explainer

[dd.h1]
What is a due date?

[dd.meta]
25 October 2026 · Reading time: 3 mins

*Date filled in. The existing "3 mins" turned out to be right — 698 words of
prose is 3.0 minutes at ~230wpm — so I left the number alone.*

[dd.aboutdata]
About the data. The curve shown is an approximation of the probability of spontaneous labour with a few tweaks and simplifying assumptions made. It's roughly the right shape and good enough for a bit of fun, but obviously not clinical advice.

[dd.intro.p]
I didn't know either. But if you think about it for a moment, you'll probably land close to the real answer.

---

## Part 1 — the due date is a median

[dd.intro.h2]
The due date is a median

[dd.step.intro]
A due date is the date on which the baby is 50% likely to have been born, on or before. In other words, it's the median of the distribution of when spontaneous labour begins.

[dd.step.intro.p2]
The curve on the left shows that distribution. The higher the line is, the greater chance that the baby will be born on that day.

[dd.step.regions]
We can visualise the due date using this probability curve. The blue area on the left represents the 50% chance of the baby arriving on or before the due date, and the pink area on the right is the other 50% (the chance of it arriving after the due date).

[dd.step.line]
The line between them (the vertical line that splits the area into two equal halves) is the due date.

[dd.step.mode]
Interestingly, the due date isn't the single most likely day for the baby to be born. Because of the skewed shape, the peak of the curve (the mode) falls a couple of days after the due date. So if you had to bet on an exact day, place it a couple of days later.

---

## Part 2 — dice and conditional probability

[dd.dice.h2]
A quick detour: conditional probability

[dd.step.dice-intro.p1]
Before we go further, let's talk about conditional probability. That's maths-speak for how your beliefs change once you have more information.

[dd.step.dice-intro.p2]
Imagine a die has been rolled. You haven't seen the result yet, but want to know the median (or due date) of the die.

[dd.step.dice-half]
Each face is equally likely, so there's a 50% chance the roll was at least 4 and, consequently a 50% chance it wasn't.

[dd.step.dice-condition]
Now imagine you're given new information. Someone tells you the roll wasn't a 1 or a 2. Now we can rule those two options out entirely.

[dd.step.dice-newhalf.p1]
With 1 and 2 ruled out, only 3, 4, 5 and 6 remain, each still equally likely. Now it's 3 and 4 that make up the "lower" half. So we know there's a 50% chance the roll was at least 5.

[dd.step.dice-newhalf.p2]
The new information changed our perception of the value of the die and shifted where the halfway point sits.

---

## Part 3 — back to the due date

[dd.return.h2]
Now, back to the due date.

[dd.step.return.p1]
The same logic applies to the pregnancy example. Let's imagine we're ticking along, day by day.

[dd.step.return.p2]
Every day that goes by with no baby means we know a little bit more information about when the baby is due — it must be a day in the future.

[dd.step.today-38.p1]
Say we reach 38 weeks and the baby still hasn't arrived. Just like ruling out the 1 and 2 on the die, we can rule out everything to the left of "today."

[dd.step.today-38.p2]
The halfway point of what's left has shifted slightly later than the original due date.

[dd.step.today-39]
And it keeps moving. If you get to 39 weeks and still no baby, the same thing happens. We can rule out more of the curve, and the new 50% mark drifts later still.

[dd.step.today-41.p1]
If the baby still hasn't arrived by the original due date, the "updated due date" is now several days further into the future.

[dd.step.today-41.p2]
We'll stop there, since realistically, if you've made it to your due date and the baby hasn't come yet, you'll probably have more pressing things on your mind than conditional probability.

---

## Part 4 — summary

[dd.summary.h2]
To summarise

[dd.summary.p1]
If you use the median definition of "due date" throughout a pregnancy and keep recalculating it, it keeps receding. Every day you don't go into labour pushes the "50%-likely date" a little further away.

[dd.summary.p2]
Of course, once the baby arrives, you'll have neither the time, the energy, nor the mental faculty left to think about any of this.

---

## Chart labels

Short on-chart text. Each `{{...}}` is filled in live as the reader scrolls.

[dd.label.due]
Due date · {{weeks}}

[dd.label.mode]
Most likely day · {{weeks}}

[dd.label.today]
Today · {{weeks}}

[dd.label.newdue]
New due date · {{weeks}}

[dd.label.pct]
50%

[dd.axis.x]
Gestational age

[dd.axis.y]
Likelihood of birth

[dd.axis.dice.x]
Die face

[dd.axis.dice.y]
Likelihood

---

# Not included above

Pure interface furniture, left out to keep this readable. Say the word and I'll
pull any of it in too:

- Table column headers (`Pts`, `GD`, `W`, `D`, `L`, `Minute`, `Player`, `xG`…)
- Chart and card labels on the football page: `Real`, `Simulated`, `Shot`,
  `Kick-off`, `Gameweek N`, `Final table`, `Game by game`, `Shots`
- Team names, player names and crest alt text (these come from the data, not
  from copy)
- The site header, nav and footer, which are shared across every page
