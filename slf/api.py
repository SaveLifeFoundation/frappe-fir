import frappe
import base64
import json
import os
import asyncio
import logging
import httpx


# Enable debug logging
logging.basicConfig(level=logging.DEBUG)


async def process_ocr(file_path, doc_id):
    """
    Process OCR using Marker OCR and extract structured data using OpenAI.
    """
    try:
        # Extract text using Marker OCR
        async with httpx.AsyncClient(timeout=900) as client:
            with open(file_path, "rb") as f:
                llm_host = frappe.conf.llm_host
                files = {"file": (os.path.basename(file_path), f, "application/pdf")}
                response = await client.post(f"{llm_host}/marker-ocr", files=files, headers={"ngrok-skip-browser-warning": "true"})
                response.raise_for_status()
                ocr_result = response.json()
        
        # Assume Marker OCR returns {"text": "..."} or {"content": "..."}
        md_content = ocr_result.get("text") or ocr_result.get("content")
        if not md_content:
            raise ValueError("No text content returned from Marker OCR.")
        

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
            "file_name": f"{doc_id}.txt",
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
    Use FastAPI (Ollama) to process and extract structured JSON data from the extracted Markdown content.
    """
    try:
        config = frappe.get_doc("Config", "system_prompt")

        prompt = config.system_prompt
        payload = {"query": md_content, "system_prompt": prompt}

        async with httpx.AsyncClient(timeout=900) as client:
            llm_host = frappe.conf.llm_host
            response = await client.post(f"{llm_host}/ollama", json=payload, headers={"ngrok-skip-browser-warning": "true"})
            response.raise_for_status()
            json_output = response.json()
            raw_response = json_output["response"]
            
            if raw_response.startswith(" ```json\n") and raw_response.endswith("```"):
                raw_response = raw_response[len(" ```json\n"):-4].strip()
            return json.loads(raw_response)

    except Exception as e:
        logging.error(f"Error in Ollama processing: {str(e)}")
        frappe.log_error(f"Error in Ollama processing: {str(e)}", "Ollama Extraction Error")
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

        # Save the markdown file URL in the FIR document
       
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
