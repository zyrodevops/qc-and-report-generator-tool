"""
Reading the shipment documents: B/L, sea waybill, air waybill, invoice,
packing list and temperature recorder.

Computer-made PDFs carry their text and where each word sits, so they are
read here without AI: a value is taken from the printed box its label is in,
or found by its shape (container and seal numbers, dates, temperatures). A
scanned page carries no text and is reported as such rather than guessed at.
Whatever is read is shown to the surveyor to confirm before it goes anywhere.
"""
