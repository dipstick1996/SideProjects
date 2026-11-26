import csv
import json
import math
import os
import tkinter as tk
from datetime import date, datetime
from tkinter import filedialog, messagebox, ttk
from uuid import uuid4


APP_NAME = "Pennywise"
BG = "#f4f6fb"
CARD = "#ffffff"
INK = "#172033"
MUTED = "#718096"
ACCENT = "#6258e8"
ACCENT_LIGHT = "#eeedff"
GREEN = "#138a68"
RED = "#d94e64"
CATEGORIES = [
    "Food & dining",
    "Transport",
    "Shopping",
    "Bills & utilities",
    "Health",
    "Entertainment",
    "Travel",
    "Education",
    "Other",
]
PAYMENT_METHODS = ["UPI", "Card", "Cash", "Bank transfer", "Other"]


def data_file_path():
    app_data = os.environ.get("APPDATA")
    base_dir = app_data if app_data else os.path.expanduser("~")
    return os.path.join(base_dir, "Pennywise", "expenses.json")


class ExpenseStore:
    def __init__(self, path):
        self.path = path

    def load(self):
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                expenses = json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Could not read saved expenses:\n{error}") from error
        if not isinstance(expenses, list):
            raise RuntimeError("The saved expenses file has an invalid format.")
        validated = []
        seen_ids = set()
        for expense in expenses:
            if not isinstance(expense, dict):
                raise RuntimeError("The saved expenses file contains an invalid entry.")
            try:
                expense_id = expense["id"]
                description = expense["description"]
                amount = float(expense["amount"])
                expense_date = expense["date"]
                category = expense["category"]
                payment = expense.get("payment", "Other")
                datetime.strptime(expense_date, "%Y-%m-%d")
            except (KeyError, TypeError, ValueError) as error:
                raise RuntimeError("The saved expenses file contains an invalid entry.") from error
            if (not isinstance(expense_id, str) or not expense_id or expense_id in seen_ids
                    or not isinstance(description, str) or not description.strip()
                    or not math.isfinite(amount) or amount <= 0
                    or not isinstance(category, str) or not isinstance(payment, str)):
                raise RuntimeError("The saved expenses file contains an invalid entry.")
            seen_ids.add(expense_id)
            validated.append({
                **expense,
                "id": expense_id,
                "description": description,
                "amount": amount,
                "date": expense_date,
                "category": category,
                "payment": payment,
            })
        return validated

    def save(self, expenses):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            temporary_path = self.path + ".tmp"
            with open(temporary_path, "w", encoding="utf-8") as file:
                json.dump(expenses, file, indent=2, ensure_ascii=False)
            os.replace(temporary_path, self.path)
        except OSError as error:
            raise RuntimeError(f"Could not save expenses:\n{error}") from error


class ExpenseTracker:
    def __init__(self, root):
        self.root = root
        self.root.title("Pennywise — Expense Tracker")
        self.root.geometry("1240x900")
        self.root.minsize(1000, 760)
        self.root.configure(bg=BG)
        self.store = ExpenseStore(data_file_path())
        try:
            self.expenses = self.store.load()
        except RuntimeError as error:
            messagebox.showerror("Could not load expenses", str(error))
            self.root.destroy()
            return

        self.search_var = tk.StringVar()
        self.category_filter = tk.StringVar(value="All categories")
        self.month_filter = tk.StringVar(value="All months")
        self.description_var = tk.StringVar()
        self.amount_var = tk.StringVar()
        self.category_var = tk.StringVar(value=CATEGORIES[0])
        self.date_var = tk.StringVar(value=date.today().isoformat())
        self.payment_var = tk.StringVar(value=PAYMENT_METHODS[0])
        self.selected_id = None
        self.category_chart = None
        self.month_chart = None

        self._configure_style()
        self._build_ui()
        self._refresh()

    def _configure_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=CARD, fieldbackground=CARD,
                        foreground=INK, rowheight=36, borderwidth=0,
                        font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background="#f7f8fc",
                        foreground=MUTED, relief="flat",
                        font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", ACCENT_LIGHT)],
                  foreground=[("selected", INK)])
        style.configure("TCombobox", padding=7)

    def _build_ui(self):
        shell = tk.Frame(self.root, bg=BG, padx=26, pady=20)
        shell.pack(fill="both", expand=True)

        header = tk.Frame(shell, bg=BG)
        header.pack(fill="x", pady=(0, 18))
        brand = tk.Frame(header, bg=BG)
        brand.pack(side="left")
        tk.Label(brand, text="P", bg=ACCENT, fg="white",
                 font=("Segoe UI", 15, "bold"), width=2, height=1).pack(side="left", padx=(0, 11))
        title_box = tk.Frame(brand, bg=BG)
        title_box.pack(side="left")
        tk.Label(title_box, text=APP_NAME, bg=BG, fg=INK,
                 font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(title_box, text="Your money, in focus.", bg=BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w")
        tk.Button(header, text="Export CSV", command=self._export_csv,
                  bg=ACCENT, fg="white", activebackground="#5147d0",
                  activeforeground="white", relief="flat", padx=16, pady=9,
                  font=("Segoe UI", 10, "bold"), cursor="hand2").pack(side="right", pady=5)

        self.summary_frame = tk.Frame(shell, bg=BG)
        self.summary_frame.pack(fill="x", pady=(0, 16))
        self.summary_cards = []
        for _ in range(3):
            card = tk.Frame(self.summary_frame, bg=CARD, padx=18, pady=14,
                            highlightbackground="#e8ebf3", highlightthickness=1)
            card.pack(side="left", fill="x", expand=True, padx=(0, 12))
            label = tk.Label(card, bg=CARD, fg=MUTED, font=("Segoe UI", 9))
            label.pack(anchor="w")
            value = tk.Label(card, bg=CARD, fg=INK, font=("Segoe UI", 20, "bold"))
            value.pack(anchor="w", pady=(5, 0))
            self.summary_cards.append((label, value))
        self.summary_cards[-1][0].master.pack_configure(padx=0)

        self._build_entry_form(shell)
        self._build_filters(shell)
        self._build_expense_table(shell)
        self._build_charts(shell)

    def _build_entry_form(self, parent):
        card = tk.Frame(parent, bg=CARD, padx=16, pady=14,
                        highlightbackground="#e8ebf3", highlightthickness=1)
        card.pack(fill="x", pady=(0, 14))
        tk.Label(card, text="Add an expense", bg=CARD, fg=INK,
                 font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=6,
                                                      sticky="w", pady=(0, 10))
        fields = [
            ("Description", self.description_var, 25),
            ("Amount (₹)", self.amount_var, 14),
            ("Date (YYYY-MM-DD)", self.date_var, 15),
        ]
        for column, (label, variable, width) in enumerate(fields):
            field = tk.Frame(card, bg=CARD)
            field.grid(row=1, column=column, sticky="ew", padx=(0, 10))
            tk.Label(field, text=label, bg=CARD, fg=MUTED,
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 5))
            tk.Entry(field, textvariable=variable, width=width, relief="solid",
                     bd=1, highlightthickness=0, font=("Segoe UI", 10)).pack(fill="x", ipady=7)
            card.grid_columnconfigure(column, weight=1)

        for column, (label, variable, choices) in enumerate([
            ("Category", self.category_var, CATEGORIES),
            ("Payment method", self.payment_var, PAYMENT_METHODS),
        ], start=3):
            field = tk.Frame(card, bg=CARD)
            field.grid(row=1, column=column, sticky="ew", padx=(0, 10))
            tk.Label(field, text=label, bg=CARD, fg=MUTED,
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 5))
            ttk.Combobox(field, textvariable=variable, values=choices,
                         state="readonly").pack(fill="x", ipady=4)
            card.grid_columnconfigure(column, weight=1)

        self.add_button = tk.Button(card, text="＋  Add expense", command=self._add_expense,
                                    bg=ACCENT, fg="white", activebackground="#5147d0",
                                    activeforeground="white", relief="flat", padx=13, pady=9,
                                    font=("Segoe UI", 9, "bold"), cursor="hand2")
        self.add_button.grid(row=1, column=5, sticky="sew", padx=(0, 0), pady=(17, 0))

    def _build_filters(self, parent):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(0, 8))
        tk.Label(row, text="TRANSACTIONS", bg=BG, fg=INK,
                 font=("Segoe UI", 12, "bold")).pack(side="left", padx=(0, 14))
        search = tk.Entry(row, textvariable=self.search_var, width=28, relief="solid",
                          bd=1, font=("Segoe UI", 9))
        search.pack(side="left", ipady=6, padx=(0, 8))
        search.insert(0, "Search expenses...")
        search.config(fg=MUTED)
        search.bind("<FocusIn>", self._clear_search_placeholder)
        search.bind("<FocusOut>", self._restore_search_placeholder)
        self.search_var.trace_add("write", lambda *_: self._refresh())
        self.category_combo = ttk.Combobox(row, textvariable=self.category_filter,
                                           values=["All categories"] + CATEGORIES,
                                           state="readonly", width=19)
        self.category_combo.pack(side="left", padx=(0, 8))
        self.category_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh())
        self.month_combo = ttk.Combobox(row, textvariable=self.month_filter,
                                        values=["All months"], state="readonly", width=16)
        self.month_combo.pack(side="left")
        self.month_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh())
        self.result_label = tk.Label(row, text="", bg=BG, fg=MUTED,
                                     font=("Segoe UI", 9))
        self.result_label.pack(side="right")

    def _clear_search_placeholder(self, _event):
        if self.search_var.get() == "Search expenses...":
            self.search_var.set("")
            _event.widget.config(fg=INK)

    def _restore_search_placeholder(self, event):
        if not self.search_var.get().strip():
            self.search_var.set("Search expenses...")
            event.widget.config(fg=MUTED)

    def _build_expense_table(self, parent):
        table_card = tk.Frame(parent, bg=CARD, highlightbackground="#e8ebf3",
                              highlightthickness=1)
        table_card.pack(fill="both", expand=True, pady=(0, 14))
        columns = ("date", "description", "category", "payment", "amount")
        self.tree = ttk.Treeview(table_card, columns=columns, show="headings", height=9)
        headings = {
            "date": ("DATE", 105, "w"),
            "description": ("DESCRIPTION", 300, "w"),
            "category": ("CATEGORY", 170, "w"),
            "payment": ("PAYMENT", 150, "w"),
            "amount": ("AMOUNT", 130, "e"),
        }
        for column, (heading, width, anchor) in headings.items():
            self.tree.heading(column, text=heading)
            self.tree.column(column, width=width, anchor=anchor, stretch=column == "description")
        self.tree.tag_configure("odd", background="#fbfcff")
        self.tree.tag_configure("even", background=CARD)
        scrollbar = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda _event: self._edit_selected())

        actions = tk.Frame(parent, bg=BG)
        actions.pack(fill="x", pady=(0, 13))
        tk.Label(actions, text="Tip: double-click an expense to edit it.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
        tk.Button(actions, text="Delete selected", command=self._delete_selected,
                  bg=BG, fg=RED, activebackground="#fcecef", relief="flat",
                  padx=12, pady=5, font=("Segoe UI", 9, "bold"),
                  cursor="hand2").pack(side="right", padx=(8, 0))
        tk.Button(actions, text="Edit selected", command=self._edit_selected,
                  bg=BG, fg=ACCENT, activebackground=ACCENT_LIGHT, relief="flat",
                  padx=12, pady=5, font=("Segoe UI", 9, "bold"),
                  cursor="hand2").pack(side="right")

    def _build_charts(self, parent):
        chart_row = tk.Frame(parent, bg=BG)
        chart_row.pack(fill="x")
        category_card = tk.Frame(chart_row, bg=CARD, padx=15, pady=12,
                                 highlightbackground="#e8ebf3", highlightthickness=1)
        category_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        monthly_card = tk.Frame(chart_row, bg=CARD, padx=15, pady=12,
                                highlightbackground="#e8ebf3", highlightthickness=1)
        monthly_card.pack(side="left", fill="both", expand=True)
        tk.Label(category_card, text="Spending by category", bg=CARD, fg=INK,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(monthly_card, text="Monthly spending", bg=CARD, fg=INK,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.category_chart = tk.Canvas(category_card, height=185, bg=CARD,
                                        highlightthickness=0)
        self.category_chart.pack(fill="both", expand=True, pady=(6, 0))
        self.month_chart = tk.Canvas(monthly_card, height=185, bg=CARD,
                                     highlightthickness=0)
        self.month_chart.pack(fill="both", expand=True, pady=(6, 0))
        self.category_chart.bind("<Configure>", lambda _event: self._draw_charts())
        self.month_chart.bind("<Configure>", lambda _event: self._draw_charts())

    def _filtered_expenses(self):
        expenses = list(self.expenses)
        query = self.search_var.get().strip().lower()
        if query == "search expenses...":
            query = ""
        if query:
            expenses = [expense for expense in expenses
                        if query in expense.get("description", "").lower()
                        or query in expense.get("category", "").lower()
                        or query in expense.get("payment", "").lower()]
        category = self.category_filter.get()
        if category != "All categories":
            expenses = [expense for expense in expenses if expense.get("category") == category]
        month = self.month_filter.get()
        if month != "All months":
            expenses = [expense for expense in expenses if expense.get("date", "").startswith(month)]
        return sorted(expenses, key=lambda expense: (expense.get("date", ""), expense.get("created_at", "")),
                      reverse=True)

    def _refresh(self):
        if not hasattr(self, "tree"):
            return
        months = sorted({expense.get("date", "")[:7] for expense in self.expenses
                         if len(expense.get("date", "")) >= 7}, reverse=True)
        current_month = self.month_filter.get()
        self.month_combo.configure(values=["All months"] + months)
        if current_month not in ["All months"] + months:
            self.month_filter.set("All months")
        expenses = self._filtered_expenses()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for index, expense in enumerate(expenses):
            self.tree.insert("", "end", iid=expense["id"],
                             values=(expense["date"], expense["description"],
                                     expense["category"], expense.get("payment", "Other"),
                                     self._money(expense["amount"])),
                             tags=("odd" if index % 2 else "even",))
        self.result_label.config(text=f"{len(expenses)} expense{'s' if len(expenses) != 1 else ''}")
        total = sum(float(expense["amount"]) for expense in expenses)
        today_month = date.today().strftime("%Y-%m")
        month_total = sum(float(expense["amount"]) for expense in self.expenses
                          if expense.get("date", "").startswith(today_month))
        average = total / len(expenses) if expenses else 0
        values = [
            ("SPENDING IN VIEW", self._money(total)),
            ("SPENT THIS MONTH", self._money(month_total)),
            ("AVERAGE PER EXPENSE", self._money(average)),
        ]
        for (label, value), (new_label, new_value) in zip(self.summary_cards, values):
            label.config(text=new_label)
            value.config(text=new_value)
        self._draw_charts(expenses)

    @staticmethod
    def _money(amount):
        return f"₹{amount:,.2f}"

    def _draw_charts(self, expenses=None):
        if not self.category_chart or not self.month_chart:
            return
        expenses = self._filtered_expenses() if expenses is None else expenses
        self._draw_category_chart(expenses)
        self._draw_month_chart(expenses)

    def _draw_category_chart(self, expenses):
        canvas = self.category_chart
        canvas.delete("all")
        width = max(canvas.winfo_width(), 360)
        height = max(canvas.winfo_height(), 185)
        totals = {}
        for expense in expenses:
            category = expense.get("category", "Other")
            totals[category] = totals.get(category, 0) + float(expense["amount"])
        if not totals:
            canvas.create_text(width / 2, height / 2, text="Add expenses to see your breakdown",
                               fill=MUTED, font=("Segoe UI", 9))
            return
        palette = ["#6258e8", "#f0a43c", "#24a889", "#ed6683", "#4b8ce2",
                   "#9b6bd3", "#38a7b3", "#d27a4e", "#8293a8"]
        total = sum(totals.values())
        center_x, center_y = min(90, width * 0.26), height / 2
        radius = min(66, height * 0.36)
        start = 0
        for index, (category, amount) in enumerate(sorted(totals.items(),
                                                          key=lambda item: item[1], reverse=True)):
            extent = amount / total * 359.9
            color = palette[index % len(palette)]
            canvas.create_arc(center_x - radius, center_y - radius,
                              center_x + radius, center_y + radius,
                              start=start, extent=extent, fill=color, outline=CARD, width=2)
            start += extent
        canvas.create_oval(center_x - radius * 0.57, center_y - radius * 0.57,
                           center_x + radius * 0.57, center_y + radius * 0.57,
                           fill=CARD, outline=CARD)
        canvas.create_text(center_x, center_y - 6, text=f"{len(totals)}",
                           fill=INK, font=("Segoe UI", 15, "bold"))
        canvas.create_text(center_x, center_y + 13, text="categories",
                           fill=MUTED, font=("Segoe UI", 8))
        legend_x = center_x + radius + 24
        legend_y = max(15, (height - min(len(totals), 5) * 29) / 2)
        for index, (category, amount) in enumerate(sorted(totals.items(),
                                                          key=lambda item: item[1], reverse=True)[:5]):
            y = legend_y + index * 29
            color = palette[index % len(palette)]
            canvas.create_oval(legend_x, y + 3, legend_x + 9, y + 12,
                               fill=color, outline=color)
            label = category if len(category) < 17 else category[:15] + "…"
            canvas.create_text(legend_x + 16, y + 8, text=label,
                               anchor="w", fill=INK, font=("Segoe UI", 8))
            canvas.create_text(width - 14, y + 8, text=self._money(amount),
                               anchor="e", fill=MUTED, font=("Segoe UI", 8))

    def _draw_month_chart(self, expenses):
        canvas = self.month_chart
        canvas.delete("all")
        width = max(canvas.winfo_width(), 360)
        height = max(canvas.winfo_height(), 185)
        totals = {}
        for expense in expenses:
            month = expense.get("date", "")[:7]
            if month:
                totals[month] = totals.get(month, 0) + float(expense["amount"])
        months = sorted(totals)[-6:]
        if not months:
            canvas.create_text(width / 2, height / 2, text="Your monthly trend will appear here",
                               fill=MUTED, font=("Segoe UI", 9))
            return
        left, right, top, bottom = 38, width - 12, 18, height - 31
        max_value = max(totals[month] for month in months) or 1
        chart_height = bottom - top
        canvas.create_line(left, bottom, right, bottom, fill="#e8ebf3")
        slot = (right - left) / len(months)
        bar_width = min(34, slot * 0.54)
        for index, month in enumerate(months):
            x = left + slot * (index + 0.5)
            bar_height = max(4, totals[month] / max_value * (chart_height - 18))
            canvas.create_rectangle(x - bar_width / 2, bottom - bar_height,
                                    x + bar_width / 2, bottom, fill=ACCENT, outline="")
            canvas.create_text(x, bottom + 14, text=datetime.strptime(month, "%Y-%m").strftime("%b"),
                               fill=MUTED, font=("Segoe UI", 8))
            if len(months) <= 4:
                label = f"{totals[month] / 1000:.0f}k" if totals[month] >= 1000 else f"{totals[month]:.0f}"
                canvas.create_text(x, bottom - bar_height - 9, text=label,
                                   fill=MUTED, font=("Segoe UI", 7))

    def _add_expense(self):
        description = self.description_var.get().strip()
        amount_text = self.amount_var.get().strip().replace(",", "")
        expense_date = self.date_var.get().strip()
        if not description:
            messagebox.showwarning("Missing description", "Enter a description for this expense.")
            return
        try:
            amount = float(amount_text)
            if not math.isfinite(amount) or amount <= 0 or round(amount, 2) <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid amount", "Enter a finite amount of at least ₹0.01.")
            return
        try:
            datetime.strptime(expense_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("Invalid date", "Use the date format YYYY-MM-DD.")
            return
        expense = {
            "id": str(uuid4()),
            "description": description,
            "amount": round(amount, 2),
            "category": self.category_var.get(),
            "date": expense_date,
            "payment": self.payment_var.get(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.expenses.append(expense)
        if not self._save():
            self.expenses.remove(expense)
            return
        self.description_var.set("")
        self.amount_var.set("")
        self.date_var.set(date.today().isoformat())
        self._refresh()

    def _save(self):
        try:
            self.store.save(self.expenses)
            return True
        except RuntimeError as error:
            messagebox.showerror("Could not save expense", str(error))
            return False

    def _selected_expense(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Select an expense", "Select an expense from the list first.")
            return None
        expense_id = selection[0]
        return next((expense for expense in self.expenses if expense["id"] == expense_id), None)

    def _edit_selected(self):
        expense = self._selected_expense()
        if expense is None:
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit expense")
        dialog.configure(bg=CARD)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        frame = tk.Frame(dialog, bg=CARD, padx=22, pady=20)
        frame.pack()
        variables = {
            "Description": tk.StringVar(value=expense.get("description", "")),
            "Amount (₹)": tk.StringVar(value=str(expense.get("amount", ""))),
            "Date (YYYY-MM-DD)": tk.StringVar(value=expense.get("date", "")),
            "Category": tk.StringVar(value=expense.get("category", "Other")),
            "Payment method": tk.StringVar(value=expense.get("payment", "Other")),
        }
        for row, (label, variable) in enumerate(variables.items()):
            tk.Label(frame, text=label, bg=CARD, fg=MUTED,
                     font=("Segoe UI", 9, "bold")).grid(row=row, column=0, sticky="w", pady=6)
            if label == "Category":
                widget = ttk.Combobox(frame, textvariable=variable,
                                      values=CATEGORIES, state="readonly", width=25)
            elif label == "Payment method":
                widget = ttk.Combobox(frame, textvariable=variable,
                                      values=PAYMENT_METHODS, state="readonly", width=25)
            else:
                widget = tk.Entry(frame, textvariable=variable, width=28, relief="solid", bd=1)
            widget.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=6, ipady=4)

        def save_changes():
            description = variables["Description"].get().strip()
            try:
                amount = float(variables["Amount (₹)"].get().strip().replace(",", ""))
                if (not math.isfinite(amount) or amount <= 0 or round(amount, 2) <= 0
                        or not description):
                    raise ValueError
                datetime.strptime(variables["Date (YYYY-MM-DD)"].get().strip(), "%Y-%m-%d")
            except ValueError:
                messagebox.showwarning("Check expense details",
                                       "Enter a description, a positive amount, and a valid YYYY-MM-DD date.",
                                       parent=dialog)
                return
            old_expense = dict(expense)
            expense.update({
                "description": description,
                "amount": round(amount, 2),
                "date": variables["Date (YYYY-MM-DD)"].get().strip(),
                "category": variables["Category"].get(),
                "payment": variables["Payment method"].get(),
            })
            if not self._save():
                expense.clear()
                expense.update(old_expense)
                return
            dialog.destroy()
            self._refresh()

        buttons = tk.Frame(frame, bg=CARD)
        buttons.grid(row=len(variables), column=0, columnspan=2, sticky="e", pady=(14, 0))
        tk.Button(buttons, text="Cancel", command=dialog.destroy, relief="flat",
                  bg="#f1f3f8", fg=INK, padx=13, pady=7, cursor="hand2").pack(side="left", padx=5)
        tk.Button(buttons, text="Save changes", command=save_changes, relief="flat",
                  bg=ACCENT, fg="white", padx=13, pady=7, cursor="hand2").pack(side="left")
        dialog.bind("<Return>", lambda _event: save_changes())

    def _delete_selected(self):
        expense = self._selected_expense()
        if expense is None:
            return
        if not messagebox.askyesno("Delete expense",
                                   f"Delete “{expense['description']}” ({self._money(float(expense['amount']))})?"):
            return
        self.expenses.remove(expense)
        if not self._save():
            self.expenses.append(expense)
            return
        self._refresh()

    def _export_csv(self):
        expenses = self._filtered_expenses()
        if not expenses:
            messagebox.showinfo("Nothing to export", "There are no expenses in the current view.")
            return
        path = filedialog.asksaveasfilename(
            title="Export expenses",
            defaultextension=".csv",
            initialfile=f"pennywise-expenses-{date.today().isoformat()}.csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.DictWriter(file, fieldnames=[
                    "date", "description", "amount", "category", "payment"
                ])
                writer.writeheader()
                for expense in expenses:
                    writer.writerow({
                        "date": expense["date"],
                        "description": expense["description"],
                        "amount": f"{float(expense['amount']):.2f}",
                        "category": expense["category"],
                        "payment": expense.get("payment", "Other"),
                    })
        except OSError as error:
            messagebox.showerror("Export failed", f"Could not export the CSV file:\n{error}")
            return
        messagebox.showinfo("Export complete", f"Exported {len(expenses)} expenses to:\n{path}")


def main():
    root = tk.Tk()
    ExpenseTracker(root)
    root.mainloop()


if __name__ == "__main__":
    main()
