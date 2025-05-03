from flask import Flask, request, jsonify
from flask_cors import CORS
import datetime
import re
import calendar

app = Flask(__name__)
CORS(app)  # Allow requests from Flutter

def get_last_day_of_month(year, month):
    return calendar.monthrange(year, month)[1]

def extract_details(barcode_data):
    barcode_data = barcode_data.strip()
    expiry_date = None
    product_name = "Unknown Product"
    batch_no = "Unknown Batch"

    # Try labeled extraction first
    name_match = re.search(r"Product\s*Name\s*[:\-]\s*(.+)", barcode_data, re.IGNORECASE)
    if name_match:
        product_name = name_match.group(1).split("\n")[0].strip()

    batch_match = re.search(r"(Batch\s*No|Lot|Batch)[:\-]?\s*([A-Z]*\d+)", barcode_data, re.IGNORECASE)
    if batch_match:
        batch_no = batch_match.group(2).strip()

    # Date format patterns
    date_patterns = [
        (r"\b(\d{2})(\d{2})(\d{4})\b", "ddmmyyyy"),        # DDMMYYYY
        (r"\b(\d{4})[-/](\d{2})[-/](\d{2})\b", "yyyymmdd"), # YYYY-MM-DD or YYYY/MM/DD
        (r"\b(\d{2})[-/](\d{2})[-/](\d{4})\b", "ddmmyyyy"), # DD/MM/YYYY or DD-MM-YYYY
        (r"\b(\d{2})[-/](\d{4})\b", "mmyyyy"),              # MM/YYYY or MM-YYYY
        (r"\b([A-Za-z]{3})\s*(\d{4})\b", "mmmyyyy"),        # Jan 2025
        (r"\b(\d{4})\b", "yyyy"),                           # Year only
        (r"\b(\d{2})(\d{2})\b", "yymm")                     # YYMM
    ]

    month_abbr = {month: index for index, month in enumerate(calendar.month_abbr) if month}

    for pattern, format_type in date_patterns:
        match = re.search(pattern, barcode_data)
        if match:
            try:
                if format_type == "ddmmyyyy":
                    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                elif format_type == "yyyymmdd":
                    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                elif format_type == "mmyyyy":
                    month, year = int(match.group(1)), int(match.group(2))
                    day = get_last_day_of_month(year, month)
                elif format_type == "mmmyyyy":
                    month_str = match.group(1).title()
                    month = month_abbr.get(month_str[:3])
                    year = int(match.group(2))
                    if not month:
                        continue
                    day = get_last_day_of_month(year, month)
                elif format_type == "yyyy":
                    year = int(match.group(1))
                    month = 12
                    day = 31
                elif format_type == "yymm":
                    year = 2000 + int(match.group(1))
                    month = int(match.group(2))
                    day = get_last_day_of_month(year, month)

                expiry_date = datetime.datetime(year, month, day).strftime("%Y-%m-%d")
                break
            except ValueError:
                continue

    # Fallback for product name if labeled field not found
    if product_name == "Unknown Product":
        cutoff_keywords = []
        if batch_match:
            cutoff_keywords.append(batch_match.group(0))
        if 'match' in locals() and match:
            cutoff_keywords.append(match.group(0))

        cutoff_index = len(barcode_data)
        for kw in cutoff_keywords:
            idx = barcode_data.find(kw)
            if idx != -1 and idx < cutoff_index:
                cutoff_index = idx

        product_guess = barcode_data[:cutoff_index].strip()
        if product_guess:
            product_name = product_guess

    return product_name, batch_no, expiry_date

def check_expiry(expiry_date):
    if not expiry_date:
        return "Unknown", "⚠️ Expiry date not found."

    today = datetime.datetime.now()
    try:
        expiry = datetime.datetime.strptime(expiry_date, "%Y-%m-%d")
    except ValueError as e:
        return "Unknown", "⚠️ Invalid expiry date format."

    if expiry < today:
        return "Expired", f"❌ ALERT: This product is EXPIRED! Expiry Date: {expiry_date}"
    elif (expiry - today).days < 7:
        return "Nearing Expiry", f"⚠️ WARNING: This product is NEARING EXPIRY! Expiry Date: {expiry_date}"
    else:
        return "Valid", "✅ This product is still valid."

@app.route('/scan', methods=['POST'])
def scan_barcode():
    data = request.json
    barcode_data = data.get("barcode", "")

    if not barcode_data:
        return jsonify({"error": "No barcode data provided"}), 400

    product_name, batch_no, expiry_date = extract_details(barcode_data)
    status, warning_message = check_expiry(expiry_date)

    return jsonify({
        "product_name": product_name,
        "batch_no": batch_no,
        "expiry_date": expiry_date,
        "status": status,
        "warning_message": warning_message
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
