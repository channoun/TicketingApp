import barcode
from barcode.writer import ImageWriter

def generate_barcode(code):
    with open("barcodes/%s.png"%code.split(" ")[0], "wb") as f:
        mybarcode = barcode.generate("Code39", code.replace("_", " "), writer=ImageWriter(), output=f, writer_options={"font_size": 20})