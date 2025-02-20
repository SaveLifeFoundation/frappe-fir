// Copyright (c) 2025, Shamoon and contributors
// For license information, please see license.txt

// frappe.ui.form.on("FIR", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on('FIR', {
    refresh: function(frm) {
        if (frm.doc.fir_pdf) {  // Assuming 'md_file_url' holds the PDF URL
            let pdf_url = frm.doc.fir_pdf;
			let md_url = frm.doc.md_content;

            // Only allow PDF files to be embedded
            if (pdf_url.endsWith('.pdf')) {
                frm.fields_dict.pdf_viewer.$wrapper.html(`
                    <iframe src="${pdf_url}" width="100%" height="600px" style="border: none;"></iframe>
                `);
            } else {
                frm.fields_dict.pdf_viewer.$wrapper.html('<p>No PDF available</p>');
            }

			if (md_url.endsWith('.md')) {
                frm.fields_dict.md_viewer.$wrapper.html(`
                    <iframe src="${md_url}" width="100%" height="600px" style="border: none;"></iframe>
                `);
            } else {
                frm.fields_dict.md_viewer.$wrapper.html('<p>No PDF available</p>');
            }

        }

    }
});
