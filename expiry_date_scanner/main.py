import cv2
from pyzbar.pyzbar import decode
import datetime
import re
import calendar
import tkinter as tk
from tkinter import messagebox

def show_alert(message):
    """Display an alert popup."""
    root = tk.Tk()
    root.withdraw()  # Hide main window
    messagebox.showwarning("Expiry Alert", message)
    root.destroy()

def check_expiry(expiry_date):
    """Check expiry status and show alert if needed."""
    today = datetime.datetime.now()
    try:
        expiry = datetime.datetime.strptime(expiry_date, "%Y-%m-%d")
    except ValueError:
        return "⚠️ Invalid Date Format"

    if expiry < today:
        show_alert(f"❌ ALERT: This product is EXPIRED!\nExpiry Date: {expiry_date}")
        return "❌ Expired"
    elif (expiry - today).days < 7:
        show_alert(f"⚠️ WARNING: This product is NEARING EXPIRY!\nExpiry Date: {expiry_date}")
        return "⚠️ Nearing Expiry"
    else:
        return "✅ Valid"

def get_last_day_of_month(year, month):
    """Returns the last day of a given month."""
    return calendar.monthrange(year, month)[1]

def extract_details(barcode_data):
    """Extracts product details (name, batch, expiry date, best before processing)."""
   
    print(f"\n🔍 Raw Scanned Data: {barcode_data}")  # Debugging line
    # Clean barcode data
    barcode_data = barcode_data.strip()

    expiry_date = None
    manufacture_date = None
    best_before_months = None

    # Updated regex patterns to capture more formats
    date_patterns = [
        (r"\b(\d{2})(\d{2})(\d{4})\b", "ddmmyyyy"),  # DDMMYYYY → 23032025
        (r"\b(\d{4})[-/.](\d{2})[-/.](\d{2})\b", "yyyymmdd"),  # YYYY-MM-DD or YYYY.MM.DD → 2025-03-23
        (r"\b(\d{2})[-/.](\d{2})[-/.](\d{4})\b", "ddmmyyyy"),  # DD/MM/YYYY → 23/03/2025
        (r"\b(\d{2})[-/.](\d{4})\b", "mmyyyy"),  # MMYYYY → 032025 (assumes last day of month)
        (r"EXP (\d{2})[-/.](\d{2})\b", "mmyy"),  # EXP MM-YY → EXP 03-25
        (r"BEST BEFORE (\d{2}) MONTHS", "bestbefore")  # BEST BEFORE XX MONTHS
    ]

    for pattern, format_type in date_patterns:
        match = re.search(pattern, barcode_data, re.IGNORECASE)
        if match:
            try:
                if format_type == "ddmmyyyy":
                    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                elif format_type == "yyyymmdd":
                    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                elif format_type == "mmyyyy":
                    month, year = int(match.group(1)), int(match.group(2))
                    day = get_last_day_of_month(year, month)
                elif format_type == "mmyy":  
                    month, year = int(match.group(1)), int(match.group(2)) + 2000  # Convert YY to YYYY
                    day = get_last_day_of_month(year, month)
                elif format_type == "bestbefore":
                    best_before_months = int(match.group(1))
                    continue  

                valid_date = datetime.datetime(year, month, day)
                expiry_date = valid_date.strftime("%Y-%m-%d")
                break  

            except ValueError:
                continue  

    # Extract manufacturing date if "BEST BEFORE XX MONTHS" is found
    if best_before_months:
        manufacture_patterns = [
            (r"MFG (\d{2})[-/.](\d{2})[-/.](\d{4})", "ddmmyyyy"),  # MFG 23/03/2025
            (r"MFG (\d{4})[-/.](\d{2})[-/.](\d{2})", "yyyymmdd"),  # MFG 2025-03-23
            (r"MFG (\d{2})[-/.](\d{4})", "mmyyyy")  # MFG 03/2025
        ]
        
        for pattern, format_type in manufacture_patterns:
            match = re.search(pattern, barcode_data, re.IGNORECASE)
            if match:
                try:
                    if format_type == "ddmmyyyy":
                        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    elif format_type == "yyyymmdd":
                        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    elif format_type == "mmyyyy":
                        month, year = int(match.group(1)), int(match.group(2))
                        day = get_last_day_of_month(year, month)

                    manufacture_date = datetime.datetime(year, month, day)
                    expiry_date = (manufacture_date + datetime.timedelta(days=best_before_months * 30)).strftime("%Y-%m-%d")
                    break

                except ValueError:
                    continue  

    # Extract product name (before numbers)
   # Extract product name from the part **before** the first number
    product_name_match = re.match(r"([A-Za-z\s]+)", barcode_data)
    product_name = product_name_match.group(1).strip() if product_name_match else "Unknown Product"


    # Extract batch number
    batch_match = re.search(r"(B\d+|Lot\d+|Batch\d+|[A-Z]\d+)", barcode_data, re.IGNORECASE)
    batch_no = batch_match.group() if batch_match else "Unknown Batch"

    return product_name, batch_no, expiry_date

def scan_barcode():
    """Scans barcode using webcam."""
    cap = cv2.VideoCapture(0)
    print("\n📸 Scanning for barcodes... Please hold your product steady.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        barcodes = decode(frame)
        for barcode in barcodes:
            barcode_data = barcode.data.decode('utf-8')
            cap.release()
            cv2.destroyAllWindows()
            return barcode_data

        cv2.imshow("🔍 Barcode Scanner", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    return None

if __name__ == "__main__":
    barcode = scan_barcode()

    if barcode:
        product_name, batch_no, expiry_date = extract_details(barcode)

        print("\n🛒 **Product Details**")
        print(f"🔹 Product Name: {product_name}")
        print(f"🔹 Batch Number: {batch_no}")

        if expiry_date:
            expiry_status = check_expiry(expiry_date)
            print(f"🔹 Expiry Date: {expiry_date} ({expiry_status})")
        else:
            print("⚠️ Expiry date not found in barcode.")

    else:
        print("⚠️ No barcode detected. Please try again.")
