import os
from io import BytesIO
from markdown import markdown
from xhtml2pdf import pisa

from src.config import Config


class PDF:
    def __init__(self):
        config = Config()
        self.pdf_path = config.get_pdfs_dir()

    def markdown_to_pdf(self, markdown_string, project_name) -> str:
        # Define your CSS
        css = """
/* Base Styles */
body {
  font-family: Times New Roman, serif; /* Adjust font family as needed */
  margin: 20px;
  font-size: 16px;
  line-height: 1.5;
  color: #333; /* Text color */
}

/* Headings */
h1 {
  color: navy;
  font-size: 24px;
  margin-bottom: 15px;
  text-align: center; /* Optional: Center align main heading */
}
h2 {
  color: darkblue;
  font-size: 20px;
  margin-bottom: 10px;
}
h3 {
  color: #333;
  font-size: 18px;
  margin-bottom: 5px;
}

/* Links */
a {
  color: #007bff;
  text-decoration: none;
}
a:hover {
  text-decoration: underline;
}

/* Emphasis */
em {
  font-style: italic;
}
strong {
  font-weight: bold;
}

/* Lists */
ul {
  list-style-type: disc;
  margin-left: 20px;
  padding: 0;
}
li {
  margin-bottom: 2px;
}

ol {
  list-style-type: decimal;
  margin-left: 20px;
  padding: 0;
}

/* Tables */
table {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 15px;
}
th, td {
  padding: 5px;
  border: 1px solid #ddd;
}

tr:nth-child(even) { /* Optional: Alternate row background color */
  background-color: #f2f2f2;
}

/* Images */
img {
  max-width: 100%;
  height: auto;
}

/* Code Blocks */
pre {
  background-color: #f5f5f5;
  padding: 10px;
  border-radius: 3px;
}
code {
  font-family: monospace;
}

/* Page Breaks */
@media print {
  .page-break {
    page-break-after: always;
  }
}

        """

        # Convert Markdown to HTML
        html_string = markdown(markdown_string)

        # Add CSS to HTML
        html_with_css_string = f"<style>{css}</style>{html_string}"

        out_file_path = os.path.join(self.pdf_path, f"{project_name}.pdf")
        with open(out_file_path, "wb") as out_file:
            pisa_status = pisa.CreatePDF(html_with_css_string, dest=out_file)

        if pisa_status.err:
            raise Exception("Error generating PDF")

        return out_file_path
