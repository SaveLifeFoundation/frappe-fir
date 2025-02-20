frappe.ui.form.on("pdf", {
	upload_pdf: function (frm) {
		console.log("eee");
		// Assuming 'upload_pdfs' is the fieldname of your button
		new frappe.ui.FileUploader({
			multiple: true,
			restrictions: {
				allowed_file_types: ["application/pdf"],
			},
			on_success: function (file_doc) {
				link_files_to_target_doctype(file_doc, frm.doc.name);
			},
		});
	},
});

function link_files_to_target_doctype(file, reference_name) {
	frappe.call({
		method: "frappe.client.insert",
		args: {
			doc: {
				doctype: "FIR",
				fir_pdf: file.file_url,
			},
		},
		callback: function (response) {
			let doc_id = response.message.name;
			frappe.msgprint(`Created a new entry for ${file.file_name} ${doc_id} in FIRs`);
			extract_text_from_file(file.file_url, doc_id);
		},
	});
}

function extract_text_from_file(file_url, doc_id) {
	frappe.call({
		method: "slf.api.extract_text", // This will be your custom Python method
		args: {
			file_url: file_url,
			doc_id: doc_id,
		},
		callback: function (response) {
			frappe.msgprint(`Extracted text saved successfully!`);
		},
	});
}
