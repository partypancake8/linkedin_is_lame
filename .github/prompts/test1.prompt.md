Context:
I’m working in a permission-based Easy Apply automation system with explicit
classification → eligibility → resolution → interaction layers.

What I’m attaching:

Screenshot of the UI

Terminal logs showing detection, classification, and pause behavior

Observed behavior:

The system pauses on this field

Current matched key (if any): [paste from log]

Field type: [dropdown / radio / text / checkbox]

Question / label text:

[paste exact question text]


Options (if applicable):

[paste options from log]


What I want:

Mostly automated behavior

No guessing

No weakening of existing safety rules

Decision I want help making:

Is this:

Tier-1 (always safe)?

Tier-2 (usually safe / assumed)?

Never-automate?

If Tier-1 or Tier-2:

Define a named permission

Define an eligibility contract

Define a deterministic resolver

Task:
Write me a Copilot / Claude script that:

Adds support for this field following best practices

Does NOT regress existing behavior

Preserves pause/skip for unsupported cases

Touches the minimum number of files

Before writing the script:

Briefly explain why this should (or should not) be automated

Identify the correct tier

Then provide the full Copilot instruction.