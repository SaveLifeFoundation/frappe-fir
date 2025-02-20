import frappe
import base64
import json
import os
import asyncio
import logging
from pyzerox import zerox
from openai import OpenAI

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)


async def process_ocr(file_path, doc_id):
    """
    Process OCR using ZeroX and extract structured data using OpenAI.
    """
    try:
        # Extract text using ZeroX OCR
        result = await zerox(file_path=file_path, model="gpt-4o")
        md_content = '\n\n'.join(x.content for x in result.pages)

        # Upload the extracted content as a markdown file in Frappe
        file_url = upload_markdown_file(md_content, doc_id)

        # Process extracted text with OpenAI
        json_output = await extract_structured_data(md_content)

        # Save structured data into the FIR doctype
        save_fir_data(json_output, doc_id, file_url)

    except Exception as e:
        logging.error(f"Error in process_ocr: {str(e)}")
        frappe.log_error(f"Error in process_ocr: {str(e)}", "OCR Processing Error")


def upload_markdown_file(md_content, doc_id):
    """
    Upload extracted text as a markdown file to Frappe's File Doctype.
    """
    try:
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": f"{doc_id}.md",
            "is_private": 1,  # Set to 1 for private files
            "content": md_content,
        })
        file_doc.insert()
        return file_doc.file_url  # Return the uploaded file URL
    except Exception as e:
        logging.error(f"Error uploading markdown file: {str(e)}")
        frappe.log_error(f"Error uploading markdown file: {str(e)}", "File Upload Error")
        return None


async def extract_structured_data(md_content):
    """
    Use OpenAI to process and extract structured JSON data from the extracted Markdown content.
    """
    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        prompt = f"""
        Given the following accident report in Markdown format, extract the missing details and format them into a structured JSON response.

        **Instructions:**
        - Translate non-English text to English.
        - Extract explicit values from the Markdown where available.
        - Infer missing details using logical reasoning.
        - Format all responses as JSON.

         **Required Fields:**
        - FIR Number
        - Section
        - Accident Date (DD-MM-YYYY)
        - Month
        - Year
        - Accident Time (HH:MM)
        - Accident Time Zone (3 hr)
        - Jurisdiction of Police Station
        - District
        - Name of Crash Location
        - Road Name
        - Latitude Longitude
        - Road Feature
        - Number of Fatalities
        - Number of Grievously Injured persons
        - Number of people with Minor Injury
        - Total number of Injuries
        - Number of Motor Vehicles involved
        - Number of Non-motorised Vehicles involved
        - Number of Pedestrians Involved
        - Crash Between
        - Crash Configuration
        - Vehicle 1
        - Highest Injury in Vehicle 1
        - Vehicle 2
        - Highest Injury in Vehicle 2
        - Vehicle 3
        - Highest Injury in Vehicle 3
        - Crash Contributing Factor
        - Injury Contributing Factor
        - FIR Summary
        - nearest location in a district in India so I can easily reverse geocode the lat-long.

        **Markdown Report:**
        {md_content}

        **Expected Output in JSON format:**
        {{
            "fir_no": "", "section": "", "accident_date": "", "month": "", "year": "", "time": "",
            "accident_time_zone": "", "police_jurisdiction": "", "district": "", "crash_location": "",
            "road_name": "", "lat_long": "", "road_feature": "", "no_of_fatalities": "",
            "no_of_grievously_injured": "", "no_of_minor_injury": "", "no_of_total_injuries": "",
            "no_of_motor_vehicles_involved": "", "no_of_non_motor_involved": "", "no_of_pedestrians": "",
            "crash_between": "", "crash_configuration": "", "vehicle_1": "", "higest_injury_in_vehicle_1": "",
            "vehicle_2": "", "higest_injury_in_vehicle_2": "", "vehicle_3": "", "higest_injury_in_vehicle_3": "",
            "crash_contributing_factor": "", "injury_contributing_factor": "", "fir_summary": "", "nearest_location": ""
        }}
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert accident data analyst."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )

        inferred_data = response.choices[0].message.content.strip()
        return json.loads(inferred_data)  # Convert response to JSON

    except Exception as e:
        logging.error(f"Error in OpenAI processing: {str(e)}")
        frappe.log_error(f"Error in OpenAI processing: {str(e)}", "OpenAI Extraction Error")
        return {}


def save_fir_data(json_output, doc_id, file_url):
    """
    Save the extracted structured data to the FIR doctype in Frappe.
    """
    try:
        doc = frappe.get_doc('FIR', doc_id)

        # Assign values dynamically instead of hardcoding fields
        for key, value in json_output.items():
            if hasattr(doc, key):
                setattr(doc, key, value)

        maps_url = f"""https://www.google.com/maps/search/?api=1&query={json_output["nearest_location"]}"""

        # Save the markdown file URL in the FIR document
        doc.nearest_location = f"""<a href="{maps_url}" target="_blank">View Location</a>"""
        doc.md_content = file_url
        doc.save()
        frappe.db.commit()

        logging.info(f"FIR data successfully saved for document: {doc_id}")

    except Exception as e:
        logging.error(f"Error saving FIR data: {str(e)}")
        frappe.log_error(f"Error saving FIR data: {str(e)}", "FIR Data Save Error")


@frappe.whitelist()
def extract_text(file_url, doc_id):
    """
    Fetch the file, run OCR processing, and save structured data in Frappe.
    """
    try:
        # Retrieve file path from Frappe File Doctype
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        file_path = frappe.get_site_path("private", "files", file_doc.file_name)

        # Run the OCR processing asynchronously
        asyncio.run(process_ocr(file_path, doc_id))

        return {"message": "Text extracted and saved successfully!"}

    except Exception as e:
        logging.error(f"Error in extract_text: {str(e)}")
        frappe.log_error(f"Error in extract_text: {str(e)}", "OCR Extraction Error")
        return {"error": str(e)}
