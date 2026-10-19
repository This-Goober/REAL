# Introduction

A creator assembling a narrated video coordinates what the narration means,
what the footage contains, which source interval supports each point, and when
images, titles and sound should appear. A misplaced insert may reflect a wrong
description, an unsuitable selection or a correct choice translated into the
wrong time. Repair becomes difficult when these decisions are collapsed into
one generated deliverable.

Consider a violin lesson in which a fingering diagram should appear as the
player explains an octave shift. If the diagram arrives late, the creator needs
to move it to the relevant phrase while keeping the selected footage, caption
style and other placements intact.

Interactive editing systems already connect transcripts to footage
[@truong2016quickcut; @huber2019bscript], describe media in language
[@wang2024lave], and expose persistent production artifacts [@yan2026crayotter].
REAL builds on this direction with an augmentation-oriented stance
[@brynjolfsson2022turing]: the creator remains the author, and intermediate
choices should be available for correction. Its systems question is:
**How can a creator revise an intermediate editing decision while the workflow
preserves that correction through timing and export?**

REAL treats editing as compilation through four readable artifacts. A notebook
expresses narrative intent; a catalogue records media evidence and suggested
uses; a storyboard owns editorial choices; a compiler translates them into an
editable Final Cut Pro project. Models interpret media and requests, while
scripts implement binding rules, timing, revisions and validation. A stable
word anchor can retain a placement's identity when recorded speech replaces
provisional timing; creator ownership marks choices that a rebuild must retain.

Readable plans must survive export, while correctly exported footage may still
fail to communicate the idea. We distinguish structural conformance, media
selection and creator outcomes.

We contribute:

1. A working workflow with explicit media evidence, decision ownership and
   correction rules.
2. Reproducible assembly and local-repair experiments, including frozen
   100-project validation and a retained direct-model comparison.
3. A narrated case showing where structural guarantees stop: correct assets
   still require explicit pause and caption conventions.

These contributions establish technical support for correction. Their effects
on editing quality and creator effort remain to be evaluated.
