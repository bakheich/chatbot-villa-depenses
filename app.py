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
    try:
        with open(EXPENSES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print("Erreur lors du chargement des dépenses :", e)
        return []

# Sauvegarder les dépenses
def save_expenses(expenses):
    try:
        with open(EXPENSES_FILE, 'w', encoding='utf-8') as f:
            json.dump(expenses, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Erreur lors de la sauvegarde :", e)

# Ajouter une dépense
def add_expense(description, amount, category):
    expenses = load_expenses()
    try:
        expense = {
            "date": datetime.now().isoformat(),
            "description": description.strip(),
            "amount": float(amount),
            "category": category.strip() or "Autre"
        }
        expenses.append(expense)
        save_expenses(expenses)
        return expense
    except Exception as e:
        print("Erreur lors de l'ajout de la dépense :", e)
        return None

# Parser le message utilisateur
def parse_expense_message(msg):
    if not msg.lower().startswith("dépense:"):
        return None
    try:
        content = msg[8:].strip()
        parts = [p.strip() for p in content.split("-")]
        if len(parts) < 2:
            return None
        description = parts[0]
        amount = parts[1].replace("fcfa", "").replace("CFA", "").strip()  # On retire FCFA
        category = parts[2] if len(parts) > 2 else "Autre"
        return description, amount, category
    except Exception as e:
        print("Erreur lors du parsing du message :", e)
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
                reply += f"{e['date'][:10]} - {e['description']} - {int(e['amount'])} FCFA ({e['category']})\n"

    elif incoming_msg.lower() == "total":
        total = sum(e['amount'] for e in load_expenses())
        reply = f"Le montant total des dépenses est de **{int(total)} FCFA**."

    elif incoming_msg.lower().startswith("dépense:"):
        parsed = parse_expense_message(incoming_msg)
        if not parsed:
            reply = "Format incorrect. Veuillez utiliser : 'Dépense: [Description] - [Montant] - [Catégorie]'"
        else:
            desc, amt, cat = parsed
            added = add_expense(desc, amt, cat)
            if added:
                reply = f"Dépense enregistrée avec succès !\n{desc} - {int(amt)} FCFA ({cat})"
            else:
                reply = "Erreur lors de l'enregistrement de la dépense."

    else:
        reply = "Commande non reconnue. Essayez 'Bonjour', 'Dépense:...', 'Liste' ou 'Total'."

    msg.body(reply)
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)
