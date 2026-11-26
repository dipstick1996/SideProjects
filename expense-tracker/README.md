# Pennywise Expense Tracker

A lightweight desktop app for recording and reviewing everyday expenses. It uses
Python's built-in Tkinter library, so no additional packages are needed.

## Run the app

From this folder, run:

```powershell
python .\expense_tracker.py
```

## Features

- Add expenses with a description, amount, date, category, and payment method.
- Search expenses and filter by category or month.
- Double-click an expense or use **Edit selected** to update it; delete expenses
  when you no longer need them.
- Review spending in the current view, this month's spend, and average expense.
- See category and monthly spending charts update with the current filters.
- Export the current filtered view to a CSV file.
- Keep expenses between sessions; data is saved locally in
  `%APPDATA%\Pennywise\expenses.json` (or your home folder when `%APPDATA%` is
  unavailable).

Amounts are displayed in Indian rupees (INR). Dates use `YYYY-MM-DD`.
