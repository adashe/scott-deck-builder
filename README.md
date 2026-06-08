# SCOTT Automation Deck Builder

A web-based pitch deck builder for the SCOTT Automation Division sales team. Reps fill out a form describing their customer's situation, and the app generates a branded PowerPoint deck along with a matching selling script (Word doc).

## What it does

- Builds a customized 25–45 slide pitch deck per customer
- Uses the StoryBrand method to frame the customer as the hero
- Auto-includes national statistics based on value drivers the rep selects (safety, downtime, labor savings, etc.)
- Generates a companion selling script with talking points, objection responses, and discovery questions
- Multiple reps can use it simultaneously

## Architecture

- **Frontend**: Static HTML + JavaScript hosted on Vercel (the form interface)
- **Backend**: A Python serverless function on Vercel that generates the .pptx and .docx files
- **Template**: A pre-built SCOTT-branded source deck at `templates/source_deck.pptx`

## Repository layout

```
.
├── api/
│   └── generate.py          # Vercel serverless function — generates deck + script
├── public/
│   ├── index.html           # The form
│   ├── css/styles.css
│   └── js/form.js
├── templates/
│   └── source_deck.pptx     # Base template — modified per submission
├── lib/                     # Shared Python modules used by api/generate.py
│   ├── deck_builder.py
│   ├── script_builder.py
│   └── stats_library.py
├── requirements.txt         # Python dependencies for Vercel
├── vercel.json              # Vercel deployment config
└── README.md
```

## Deployment

1. Push this repo to GitHub
2. In Vercel, click "New Project" → import this GitHub repo
3. Vercel auto-detects the Python function and the static frontend — no config needed
4. The deployed URL (e.g. `scott-deck-builder.vercel.app`) is what you share with the sales team

## Local development

```bash
pip install -r requirements.txt
vercel dev
```

Then open http://localhost:3000

## Running the form

1. Sales rep visits the deployed URL
2. Fills in customer name, pain point, value drivers, what the project offers, plan, and CTA
3. Selects which sections of the SCOTT capabilities deck to include (sub-slide level control)
4. Picks relevant previous-project case studies
5. Optionally adds custom proposal slides
6. Clicks **Generate** — downloads both files

## License

Proprietary — SCOTT Industrial Systems. Not for redistribution.
