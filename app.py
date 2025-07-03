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
        print("[ERREUR] Impossible de lire le fichier :", e)
        return []

# Sauvegarder les dépenses
def save_expenses(expenses):
    try:
        with open(EXPENSES_FILE, 'w', encoding='utf-8') as f:
            json.dump(expenses, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("[ERREUR] Impossible d'écrire dans le fichier :", e)

# Parser le message de dépense
def parse_expense_message(msg):
    if not msg.lower().startswith("dépense:"):
        return None
    try:
        content = msg[8:].strip()
        parts = [p.strip() for p in content.split("-")]
        description = parts[0]
        amount = parts[1].strip()
        category = parts[2] if len(parts) > 2 else "Autre"
        date = parts[3] if len(parts) > 3 else None
        return description, amount, category, date
    except Exception as e:
        print("[ERREUR] Échec du parsing du message :", e)
        return None

# Ajouter une dépense
def add_expense(description, amount, category, date_str=None):
    try:
        if date_str:
            for fmt in ('%Y-%m-%d', '%d %B %Y', '%d/%m/%Y', '%Y/%m/%d'):
                try:
                    date_parsed = datetime.strptime(date_str.strip(), fmt)
                    break
                except ValueError:
                    continue
            else:
                raise ValueError("Format de date non reconnu")
        else:
            date_parsed = datetime.now()

        expense = {
            "date": date_parsed.isoformat(),
            "description": description.strip(),
            "amount": float(amount),
            "category": category.strip() or "Autre"
        }
        expenses = load_expenses()
        expenses.append(expense)
        save_expenses(expenses)
        return expense
    except Exception as e:
        print("[ERREUR] Impossible d'ajouter la dépense :", e)
        return None

# Filtrer les dépenses par période
def filter_expenses_by_period(period: str):
    period = period.strip().lower()
    now = datetime.now()
    expenses = load_expenses()

    filtered = []

    # Rapport semaine
    if period == "semaine":
        start_of_week = now.replace(day=now.day - now.weekday())
        filtered = [e for e in expenses if datetime.fromisoformat(e["date"]) >= start_of_week]

    # Rapport mois
    elif period.startswith("mois"):
        month_str = period[5:].strip()
        if '/' in month_str or '-' in month_str:
            year, month = month_str.replace('/', '-').split('-')
            month_filter = f"{year}-{month.zfill(2)}"
        else:
            month_map = {
                "janvier": "01", "février": "02", "mars": "03", "avril": "04",
                "mai": "05", "juin": "06", "juillet": "07", "août": "08",
                "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12"
            }
            month = month_map.get(month_str.lower(), None)
            if not month:
                return None
            month_filter = f"{now.year}-{month}"
        filtered = [e for e in expenses if e["date"].startswith(month_filter)]

    # Période personnalisée
    elif period.startswith("date"):
        try:
            _, dates = period.split(" ", 1)
            if "à" in dates:
                start_str, end_str = dates.split("à", 1)
                start = datetime.fromisoformat(start_str.strip())
                end = datetime.fromisoformat(end_str.strip())
                filtered = [e for e in expenses if start <= datetime.fromisoformat(e["date"]) <= end]
        except Exception:
            return None

    return filtered

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.values.get('Body', '').strip()

    resp = MessagingResponse()
    msg = resp.message()

    if incoming_msg.lower() in ["bonjour", "hello", "hi"]:
        reply = "Bonjour ! Vous pouvez :\n" \
                "- Envoyer une dépense : 'Dépense: [Description] - [Montant] - [Catégorie]' ou\n" \
                "                         'Dépense: [Description] - [Montant] - [Catégorie] - [Date]'\n" \
                "- Voir vos dépenses : 'Liste'\n" \
                "- Voir le total : 'Total'\n" \
                "- Générer un rapport : 'Rapport mois avril', 'Rapport semaine', 'Rapport date 2025-04-01 à 2025-04-30'"

    elif incoming_msg.lower() == "liste":
        expenses = load_expenses()
        if not expenses:
            reply = "Aucune dépense enregistrée pour le moment."
        else:
            reply = "Voici vos dernières dépenses :\n"
            for e in expenses[-5:]:
                date_fr = datetime.fromisoformat(e['date'][:10]).strftime('%d/%m/%Y')
                reply += f"{date_fr} - {e['description']} - {int(e['amount'])} FCFA ({e['category']})\n"

    elif incoming_msg.lower() == "total":
        total = sum(e['amount'] for e in load_expenses())
        reply = f"Le montant total des dépenses est de **{int(total)} FCFA**."

    elif incoming_msg.lower().startswith("dépense:"):
        parsed = parse_expense_message(incoming_msg)
        if not parsed:
            reply = "Format incorrect. Veuillez utiliser : 'Dépense: [Description] - [Montant] - [Catégorie]' ou\n'Dépense: [Description] - [Montant] - [Catégorie] - [Date]'"
        else:
            desc, amt, cat, dt = parsed
            added = add_expense(desc, amt, cat, dt)
            if added:
                date_str = datetime.fromisoformat(added["date"]).strftime('%d/%m/%Y')
                reply = f"Dépense enregistrée avec succès !\n{desc} - {int(added['amount'])} FCFA ({cat})\n📅 Date : {date_str}"
            else:
                reply = "Erreur lors de l'enregistrement de la dépense."

    elif incoming_msg.lower().startswith("rapport"):
        period = incoming_msg[7:].strip().lower()
        if not period:
            reply = "Veuillez préciser une période. Exemples :\n- 'Rapport mois avril'\n- 'Rapport semaine'\n- 'Rapport date 2025-04-01 à 2025-04-30'"
        else:
            filtered = filter_expenses_by_period(period)
            if not filtered:
                reply = "Aucune dépense trouvée pour cette période."
            else:
                total = sum(e['amount'] for e in filtered)
                reply = f"📊 Rapport pour '{period}'\n\n" \
                        f"Total des dépenses : {int(total)} FCFA\n\n" \
                        f"Dernières dépenses :\n"
                for e in filtered[-5:]:
                    date_fr = datetime.fromisoformat(e['date'][:10]).strftime('%d/%m/%Y')
                    reply += f"{date_fr} - {e['description']} - {int(e['amount'])} FCFA ({e['category']})\n"

    else:
        reply = "Commande non reconnue. Essayez 'Bonjour', 'Dépense:...', 'Liste', 'Total' ou 'Rapport...'."

    msg.body(reply)
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)
