"""
Legacy FastAPI inventory API for testing the PyPI advisor.

The app is intentionally ordinary, but its requirements are pinned to old
versions so the advisor has upgrade and vulnerability findings to report.
"""

from io import BytesIO

import httpx
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse
from jinja2 import Template
from PIL import Image
from pydantic import BaseModel


app = FastAPI(title="Legacy Inventory API")


class InventoryItem(BaseModel):
    sku: str
    name: str
    quantity: int
    supplier_url: str | None = None


INVENTORY: list[InventoryItem] = [
    InventoryItem(sku="BK-101", name="Notebook", quantity=42, supplier_url="https://example.com"),
    InventoryItem(sku="PN-204", name="Gel pen", quantity=15, supplier_url="https://example.com"),
]

PAGE_TEMPLATE = Template(
    """
    <!doctype html>
    <html lang="en">
      <head><title>Legacy Inventory API</title></head>
      <body>
        <h1>Legacy Inventory API</h1>
        <ul>
        {% for item in items %}
          <li><strong>{{ item.sku }}</strong>: {{ item.name }} ({{ item.quantity }} available)</li>
        {% endfor %}
        </ul>
      </body>
    </html>
    """
)


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return PAGE_TEMPLATE.render(items=INVENTORY)


@app.get("/items")
def list_items() -> list[InventoryItem]:
    return INVENTORY


@app.post("/items")
def create_item(item: InventoryItem) -> InventoryItem:
    INVENTORY.append(item)
    return item


@app.get("/supplier-status")
def supplier_status(url: str = "https://example.com") -> dict:
    response = httpx.get(url, timeout=5)
    return {"url": url, "status_code": response.status_code}


@app.post("/upload-photo")
async def upload_photo(sku: str = Form(...), photo: UploadFile = File(...)) -> dict:
    image_bytes = await photo.read()
    image = Image.open(BytesIO(image_bytes))
    return {"sku": sku, "filename": photo.filename, "format": image.format, "size": image.size}