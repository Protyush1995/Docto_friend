import json
import os
import re
import io
from io import BytesIO
from PIL import Image
import base64
import qrcode
from base64 import b64encode
from bson.binary import Binary
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Union
from .db_operations import DatabaseOperations
import pandas as pd
import tkinter as tk
from tkinter import filedialog


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

base = Path(__file__).parent
med_env = (base / ".env.medicine").resolve()
med_db = DatabaseOperations(env_file=str(med_env))


def append_medicine_record():
    root = tk.Tk()
    root.withdraw()

    print("Select the first CSV file...")
    csv_file = filedialog.askopenfilename(title="Select first CSV file", filetypes=[("CSV files", "*.csv")])

    df = pd.read_csv(csv_file)
    records = df.to_dict(orient="records")

    result = med_db.insert_record(user_document=records,bulk=True)
    print(f"Inserted {len(records)} records into MongoDB")
    collection = med_db.collection

  




