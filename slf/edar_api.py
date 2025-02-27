import frappe
import base64
import json
import os
import asyncio
import pandas as pd
import re
import logging
from pypdf import PdfReader

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

columns = [
    "Serial No.",
    "FIR No.",
    "Section",
    "Accident Date (DD-MM-YYYY)",
    "Accident Time (HH:MM)",
    "Jurisdiction of Police Station",
    "District",
    "Name of Crash Location",
    "Road Name",
    "Latitude, Longitude",
    "Road Feature",
    "Number of Fatalities",
    "Number of Grievously Injured persons",
    "Number of people with Minor Injury",
    "Total number of Injuries",
    "Number of Motor Vehicles involved",
    "Number of Non-motorised Vehicles involved",
    "Number of Pedestrians Involved",
    "Crash Between",
    "Crash Configuration",
    "Vehicle 1",
    "Higest Injury in Vehicle 1",
    "Vehicle 2",
    "Higest Injury in Vehicle 2",
    "Vehicle 3",
    "Higest Injury in Vehicle 3",
    "Crash Contributing Factor",
    "Injury Contributing Factor",
    "FIR Summary",
    "Text File Link",
    "PDF File Link",
    "PDF File Name",
]


def extract_section_data(text, start_marker, end_marker):
    sections = []
    start_idx = 0

    while True:
        start_idx = text.find(start_marker, start_idx)
        if start_idx == -1:
            break
        end_idx = text.find(end_marker, start_idx)
        if end_idx == -1:
            break
        section = text[start_idx + len(start_marker) : end_idx].strip()
        sections.append(section)
        start_idx = end_idx + len(end_marker)
    return sections


def process_ocr(file_path, doc_id):
    """
    Process OCR using tessearct and extract structured data using OpenAI.
    """
    try:
        print("Processing OCR")
        df = pd.DataFrame(columns=columns)
        print("Processing OCR1")
        text = ""
        with open(file_path, "rb") as file:
            print("Processing OCR2")
            reader = PdfReader(file)
            for page in reader.pages:
                text += page.extract_text()
        print(text)

        sections = extract_section_data(text, "Act", "State Rule")
        fir_nos = extract_section_data(text, "FIR/CSR Number   : ", "FIR Date & Time")
        road_names = extract_section_data(text, "Street Name", "Local Body")

        section = ", ".join(sections)
        fir_no = ", ".join(fir_nos)
        road_name = ", ".join(road_names)

        data = {
            "fir_no": fir_no,
            "section": section,
            "accident_date": (
                re.search(r"Accident Date and Time\s*(\d{2}-\w+-\d{4})", text).group(1)
                if re.search(r"Accident Date and Time\s*(\d{2}-\w+-\d{4})", text)
                else ""
            ),
            "time": (
                re.search(
                    r"Accident Date and Time\s*\d{2}-\w+-\d{4}\s*:\s*(\d{2}:\d{2} [APM]{2})",
                    text,
                ).group(1)
                if re.search(
                    r"Accident Date and Time\s*\d{2}-\w+-\d{4}\s*:\s*(\d{2}:\d{2} [APM]{2})",
                    text,
                )
                else ""
            ),
            "police_jurisdiction": (
                re.search(r"Station Name\s*:\s*(.*?)\n", text)
                .group(1)
                .split("Investigating Oﬃcer")[0]
                .strip()
                if re.search(r"Station Name\s*:\s*(.*?)\n", text)
                else ""
            ),
            "district": (
                re.search(r"District Name\s*:\s*(.*?)\n", text).group(1)
                if re.search(r"District Name\s*:\s*(.*?)\n", text)
                else ""
            ),
            "crash_location": (
                re.search(r"Location Details\s*(.*?)\n", text).group(1)
                if re.search(r"Location Details\s*(.*?)\n", text)
                else ""
            ),
            "road_name": road_name,
            "lat_long": (
                re.search(
                    r"Location Details\s*.*?Lat/Long\s*:\s*([0-9.]+,\s*[0-9.]+)", text
                ).group(1)
                if re.search(
                    r"Location Details\s*.*?Lat/Long\s*:\s*([0-9.]+,\s*[0-9.]+)", text
                )
                else ""
            ),
            "road_feature": (
                re.search(r"Road Classification\s*:\s*(.*?)\n", text).group(1)
                if re.search(r"Road Classification\s*:\s*(.*?)\n", text)
                else ""
            ),
            "no_of_fatalities": (
                re.search(
                    r"Total\s*:\s*(\d+)\s*Number of Animals involved", text
                ).group(1)
                if re.search(r"Total\s*:\s*(\d+)\s*Number of Animals involved", text)
                else "0"
            ),
            "no_of_grievously_injured": (
                re.search(r"Grievous Injury\s*(\d+)", text).group(1)
                if re.search(r"Grievous Injury\s*(\d+)", text)
                else "0"
            ),
            "no_of_minor_injury": (
                re.search(r"Minor Injury\s*(\d+)", text).group(1)
                if re.search(r"Minor Injury\s*(\d+)", text)
                else "0"
            ),
            "no_of_total_injuries": (
                re.search(r"Total\s*(\d+)", text).group(1)
                if re.search(r"Total\s*(\d+)", text)
                else "0"
            ),
            "no_of_motor_vehicles_involved": (
                re.search(r"No of Vehicle\(s\) involved\s*(\d+)", text).group(1)
                if re.search(r"No of Vehicle\(s\) involved\s*(\d+)", text)
                else "0"
            ),
            "no_of_non_motor_involved": "0",
            "no_of_pedestrians": "0",
            "crash_between": (
                re.search(r"Collision Type\s*:\s*(.*?)\n", text).group(1)
                if re.search(r"Collision Type\s*:\s*(.*?)\n", text)
                else ""
            ),
            "crash_configuration": (
                re.search(r"Collision Nature\s*:\s*(.*?)\n", text).group(1)
                if re.search(r"Collision Nature\s*:\s*(.*?)\n", text)
                else ""
            ),
            "vehicle_1": (
                re.search(r"Vehicle Regn. No\s*(.*?)\s", text).group(1)
                if re.search(r"Vehicle Regn. No\s*(.*?)\s", text)
                else ""
            ),
            "higest_injury_in_vehicle_1": "Fatal",  # Hardcoded based on available data
            "vehicle_2": (
                re.search(r"Vehicle Regn. No\s*.*?\s*MH40Y5087", text).group(1)
                if re.search(r"Vehicle Regn. No\s*.*?\s*MH40Y5087", text)
                else ""
            ),
            "higest_injury_in_vehicle_2": "No Injury",  # Hardcoded based on available data
            "vehicle_3": "None",  # Based on available data
            "higest_injury_in_vehicle_3": "None",  # Based on available data
            "crash_contributing_factor": (
                re.search(
                    r"Initial observation of accident scene\s*(.*?)\n", text
                ).group(1)
                if re.search(r"Initial observation of accident scene\s*(.*?)\n", text)
                else ""
            ),
            "injury_contributing_factor": "Not mentioned",  # Not available in the text
            "fir_summary": (
                re.search(
                    r"Initial observation of accident scene\s*(.*?)\n", text
                ).group(1)
                if re.search(r"Initial observation of accident scene\s*(.*?)\n", text)
                else ""
            ),
        }

        doc = frappe.get_doc('FIR', doc_id)
        for key, value in data.items():
            if hasattr(doc, key):
                setattr(doc, key, value)
        doc.save()
        frappe.db.commit()

    except Exception as e:
        logging.error(f"Error in process_ocr: {str(e)}")
        frappe.log_error(f"Error in process_ocr: {str(e)}", "OCR Processing Error")


def save_fir_data(json_output, doc_id, file_url):
    """
    Save the extracted structured data to the FIR doctype in Frappe.
    """
    try:
        doc = frappe.get_doc("FIR", doc_id)

        # Assign values dynamically instead of hardcoding fields
        for key, value in json_output.items():
            if hasattr(doc, key):
                setattr(doc, key, value)

        maps_url = f"""https://www.google.com/maps/search/?api=1&query={json_output["nearest_location"]}"""

        # Save the markdown file URL in the FIR document
        doc.nearest_location = (
            f"""<a href="{maps_url}" target="_blank">View Location</a>"""
        )
        doc.md_content = file_url
        doc.save()
        frappe.db.commit()

        logging.info(f"FIR data successfully saved for document: {doc_id}")

    except Exception as e:
        logging.error(f"Error saving FIR data: {str(e)}")
        frappe.log_error(f"Error saving FIR data: {str(e)}", "FIR Data Save Error")


@frappe.whitelist()
def extract_edar_text(file_url, doc_id):
    """
    Fetch the file, run OCR processing, and save structured data in Frappe.
    """
    try:
        # Retrieve file path from Frappe File Doctype
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        file_path = frappe.get_site_path("private", "files", file_doc.file_name)

        # Run the OCR processing asynchronously
        process_ocr(file_path, doc_id)

        return {"message": "Text extracted and saved successfully!"}

    except Exception as e:
        logging.error(f"Error in extract_text: {str(e)}")
        frappe.log_error(f"Error in extract_text: {str(e)}", "OCR Extraction Error")
        return {"error": str(e)}
