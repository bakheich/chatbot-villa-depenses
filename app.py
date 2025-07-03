from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import json
import os
from datetime import datetime

app = Flask(__name__)

EXPENSES_FILE = 'expenses.json'

# Charger les dépenses
def load_expenses():
    if not os.path.exists(EXPENSES_FILE):
        return []
    with open(EXPENSES_FILE, 'r') as f:
        return json.load(f)

# Sauvegarder les dépenses
def save_expenses(expenses):
    with open(EXPENSES_FILE, 'w') as f:
        json.dump(expenses, f, indent=2)

# Ajouter une dépense
def add_expense(description, amount, category):
    expenses = load_expenses()
    expense = {
        "date": datetime.now().isoformat(),
        "description": description,
        "amount": float(amount),
        "category": category
    }
    expenses.append(expense)
    save_expenses(expenses)
    return expense

# Parser le message utilisateur
def parse_expense_message(msg):
    if not msg.lower().startswith("dépense:"):
        return None
    try:
        parts = msg[8:].split("-")
        description = parts[0].strip()
        amount = parts[1].strip().replace("€", "").replace("eur", "").strip()
        category = parts[2].strip() if len(parts) > 2 else "Autre"
        return description, amount, category
    except Exception:
        return None

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.values.get('Body', '').strip()

    resp = MessagingResponse()
    msg = resp.message()

    if incoming_msg.lower() in ["bonjour", "hello", "hi"]:
        reply = "Bonjour ! Envoyez vos dépenses au format suivant :\n'Dépense: [Description] - [Montant] - [Catégorie]'"

    elif incoming_msg.lower() == "liste":
        expenses = load_expenses()
        if not expenses:
            reply = "Aucune dépense enregistrée pour le moment."
        else:
            reply = "Voici vos dernières dépenses :\n"
            for e in expenses[-5:]:
                reply += f"{e['date'][:10]} - {e['description']} - {e['amount']}€ ({e['category']})\n"

    elif incoming_msg.lower() == "total":
        total = sum(e['amount'] for e in load_expenses())
        reply = f"Le montant total des dépenses est de **{total:.2f}€**."

    elif incoming_msg.lower().startswith("dépense:"):
        parsed = parse_expense_message(incoming_msg)
        if not parsed:
            reply = "Format incorrect. Veuillez utiliser : 'Dépense: [Description] - [Montant] - [Catégorie]'"
        else:
            desc, amt, cat = parsed
            add_expense(desc, amt, cat)
            reply = f"Dépense enregistrée avec succès !\n{desc} - {amt}€ ({cat})"

    else:
        reply = "Commande non reconnue. Essayez 'Bonjour', 'Dépense:...', 'Liste' ou 'Total'."

    msg.body(reply)
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)
