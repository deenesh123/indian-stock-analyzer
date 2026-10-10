# StockVista Pro — Indian Stock Market Analyzer

Login · Admin free forever · User free trial then paywall · Modern UI

## Features

- **Login / Register** with secure password hashing
- **Admin** — always free, can manage users & settings
- **Users** — free trial (default 7 days), then payment unlock
- Live NSE/BSE dashboard, trending screens, research, best stocks
- Option chain, watchlist, portfolio, custom screener, price alerts
- **Settings** (admin): trial days, price, payment link, mark users paid

## Default login

| Username | Password | Role |
|----------|----------|------|
| admin    | admin123 | Admin (change after first login) |

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Cloud

1. Push this repo to GitHub (public)
2. Go to https://share.streamlit.io → New app
3. Select repo, main file = `app.py` → Deploy

## Admin workflow after a user pays

1. Sign in as **admin**
2. Open **Settings → Users**
3. Select the user → **Mark PAID**

## Project structure

```
├── app.py              # Main app (auth + all modules)
├── auth.py             # Login, trial, users, settings helpers
├── requirements.txt
├── README.md
├── LICENSE
├── .gitignore
└── user_data/          # Auto-created (users, settings, watchlist…) — not in git
```

## Disclaimer

Educational use only. Not investment advice.
