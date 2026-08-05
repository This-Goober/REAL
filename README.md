# REAL
Workflow-designed LLM aid in the process of original video drafting, storyboarding, and especially the daunting task of editing--all while keeping humans in the loop to not diminish human creativity and taste

What this is

The goal is to use an LLM to absorb the steps of video editing that have always been tedious to do by hand — the bookkeeping, the timing arithmetic, the "where exactly does this go" work — and leave the human with the parts that are actually judgment calls.

To figure out which steps those were, we started by breaking down the workflow of making one of these videos end to end: what I actually did, in order, including the parts where I got stuck and the parts I had to redo. My own experience is limited, so I also went through it with the friend who's been making longer videos for much longer, to see which of my problems were mine and which were just what video editing is.

Out of that workflow came a split into three main stages, plus one transitional stage that sits between the first two. Everything here is scoped to the kind of video I was making — roughly a three-minute piece explaining a concept, with demonstrations and memes or diagrams cut in. It isn't meant to be a general-purpose editor.

What this is built around

The specific place my process broke was always the same. Writing the skeleton was easy. Writing the script in my own words was easy, and doing it myself kept the style mine and made sure I covered what I wanted to cover. Recording the audio was easy, and it gave me a length. But once I had a paragraph of script and a duration, all I really had was a blank canvas — I couldn't map the ideas in that paragraph onto specific stretches of time. And because I couldn't do that, I couldn't tell how big any given visual needed to be, and because I couldn't tell that, I couldn't decide what to make in the first place. So I guessed, shot it, and found out afterwards that a section dragged, or sat too long on one image, or landed awkwardly — and re-recorded.

Every module below exists to close some part of that loop.

Module 1 — Mapping

Takes the script and the recorded voiceover and turns them into a timed map: which idea occupies which stretch of the audio, and what kind of visual each stretch needs. The output is an explicit plan — an intro plus roughly three scenes, with a stimulus called for in each — that says what media is needed, how long it has to hold, and where in the timeline it lands.

This is deliberately the cheap stage. It runs on the script and the audio alone, before anything has been shot or downloaded, so being wrong here costs a conversation rather than a re-record. The user stays in the loop throughout — the model proposes the segmentation and the media types, the human corrects them.

Module 1.5 — Gathering the media

The transitional stage, and the one that only works because Module 1 came first. With a plan in hand you now go and record or collect the media knowing three things you never knew before: what it needs to be, how long it needs to run, and where it sits. If the point is that the dissonance in an overtone demo is most obvious around the fifth second, you record knowing that. If a scene calls for a meme, you know which beat it's punctuating before you go looking for one.

This stage also includes a utility for labeling what you've collected — images and video get catalogued into a library with descriptions of what they contain, what they're useful for, and which section they belong to, so that later stages can refer to a clip by name instead of by filename.

Module 2 — Draft assembly

Turns the plan plus the gathered media into a second-by-second layout: effectively a planned slideshow where every asset has a place and a duration. The human's job here is correction rather than construction — the model will have misread which clip illustrates which point, and fixing that is a matter of moving pieces, not building them. This is where most of the iteration happens.

Module 3 — Demo and export

Produces the actual demo, and generates a Final Cut Pro–compatible project file so the whole thing can be opened in real editing software. Producing it is meant to be cheap — on the order of minutes — because the point is that you look at it, react to it, and go back. From there the loop is: play it, make edits in Final Cut, show the model what changed, iterate.

The intent is that Module 3 gets you most of the way there — the scenes, their order, and their pacing already decided — and what's left for the human is second-by-second timing within scenes, not the structure of the video itself.
