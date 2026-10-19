# Related work

**Augmentation and mixed initiative.** REAL follows the longstanding goal of
amplifying human judgment [@engelbart1962augmenting]. Mixed-initiative systems
must decide when to act and when to defer [@horvitz1999mixed]; human-centered AI
combines automation with human control [@shneiderman2020human]. Evaluating an
augmentation claim ultimately requires people working with the system
[@haupt2025centaur]. We test technical preservation here and leave interaction
benefits for a creator study.

**Interactive editing.** DemoCut structures instructional recordings from
lightweight marks [@chi2013democut]. QuickCut connects annotations, transcripts
and frame-level selection [@truong2016quickcut]; B-Script recommends B-roll and
insertion positions within a transcript [@huber2019bscript]. ExpressEdit supports
natural-language and sketch references to temporal, spatial and operational
changes [@tilekbay2024express]. REAL likewise uses language to address editing
choices, emphasizing their persistence across preparation, review, retiming
and export.

**Agent workflows and readable artifacts.** LAVE combines footage descriptions
with agent assistance and direct manipulation [@wang2024lave]. EditDuet uses
Editor and Critic agents to construct and assess sequences
[@sandoval2025editduet]. Crayotter exposes retrieval reports, analyses, blueprints
and tool outputs in long-form production [@yan2026crayotter]. These are close
precedents: staged agents and inspectable plans are not new contributions here.
REAL focuses on who owns a choice, which fields a revision preserves, and
independent checks of its translation into a project file.

Its host uses transformer-based models [@vaswani2017attention], but REAL's
representations are authored interfaces rather than learned latent codes.
Concept bottlenecks make intermediate concepts available for intervention
[@koh2020concept]. Music systems illustrate several ways to keep a person
in control: Piano Genie maps an eight-button performance to piano music
[@donahue2019piano], while Hookpad Aria offers continuations and infilling
inside a lead-sheet editor [@donahue2024aria]. YuE2 uses symbolic planning
before audio generation [@yuan2026yue2]. These interfaces and plans motivate
REAL's editable storyboard; their results do not establish benefits for video
editing. REAL applies this principle to media selection and temporal placement
without training a new model.

**Evaluation boundaries.** Message-driven editing benchmarks test selection and
sequence agreement [@ogata2026medit], whereas QVHighlights supplies annotated
video moments [@lei2021qvhighlights]. Such tasks differ from perceptual video
quality evaluation [@huang2024vbench]. Our controlled benchmark isolates
identity and timing against a team-authored specification. A small retrieval
probe checks a semantic component; neither substitutes for evaluating people
finding and repairing consequential mistakes.
