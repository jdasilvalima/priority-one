# PriorityOne demo

The page with fake data. It is static files only: no server, no database and no login, so there is nothing that can stop working. The buttons show a message explaining what they would do in production.

```bash
npm install
npm run dev
```

Then open <http://localhost:5173>.

`public/week.json` holds the whole week. It is generated from the scoring in [`platform/`](../platform), and a test there checks that the two stay identical. To regenerate it, run this from the `platform` folder:

```bash
python scripts/export_week.py
```
