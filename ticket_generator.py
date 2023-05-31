from fpdf import FPDF

def generate_ticket(number, design):
    pdf = FPDF(orientation="P", unit="mm", format=(50.8, 139.7))

    pdf.add_page()
    pdf.image(design, x=0, y=0, w=50.8, h=122)
    pdf.image("barcodes/%s.png"%number, w=50.8, x=0, y=122)
    pdf.output("tickets/%s.pdf"%number, "F")
