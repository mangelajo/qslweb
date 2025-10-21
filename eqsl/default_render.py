"""
Default QSL card render code.

This module provides a default implementation for rendering QSL cards that can be
used as the python_render_code field in CardTemplate.

Based on the original implementation from https://github.com/0x9900/QSL/
"""

# This is the default render code that can be copied into CardTemplate.python_render_code
DEFAULT_RENDER_CODE = '''
def render(card_template, qso):
    """
    Generate a QSL card image for a given QSO.

    Args:
        card_template: CardTemplate instance with the base image
        qso: QSO instance with contact details

    Returns:
        PIL Image object
    """
    from PIL import Image, ImageDraw, ImageFont
    from datetime import datetime

    # Configuration
    NEW_WIDTH = 1024
    OVERLAY_COLOR = (0x44, 0x79, 0x99, 190)  # Semi-transparent blue
    OVERLAY_BORDER = (0x44, 0x79, 0x99)      # Border color
    TEXT_COLOR = (0xFF, 0xFF, 0xFF)          # White text
    FOOTER_COLOR = (0x70, 0x70, 0xA0)        # Gray footer

    # Helper function to draw rectangle with border
    def draw_rectangle(draw, coord, color, width=1, fill=None):
        if fill:
            draw.rectangle(coord, outline=color, fill=fill)
        draw.rectangle(coord, outline=color, width=width)

    # Load and prepare base image
    # card_template.image.name returns full path (via CardTemplateProxy in sandbox)
    img = Image.open(card_template.image.name)
    img = img.convert("RGBA")

    # Validate minimum size
    if img.size[0] < NEW_WIDTH and img.size[1] < 576:
        raise ValueError("Card resolution should be at least 1024x576")

    # Load fonts (using system defaults since custom fonts aren't accessible)
    try:
        # Try to use a monospace font if available
        font_call = ImageFont.truetype("/System/Library/Fonts/Courier.ttc", 24)
        font_text = ImageFont.truetype("/System/Library/Fonts/Courier.ttc", 16)
        font_foot = ImageFont.truetype("/System/Library/Fonts/Courier.ttc", 14)
    except OSError:
        # Fall back to default font
        font_call = ImageFont.load_default()
        font_text = ImageFont.load_default()
        font_foot = ImageFont.load_default()

    # Resize image to standard width while maintaining aspect ratio
    h_size, v_size = img.size
    ratio = NEW_WIDTH / h_size
    vsize = int(v_size * ratio)
    img = img.resize((NEW_WIDTH, vsize), Image.Resampling.LANCZOS)

    # Create overlay for text
    overlay = Image.new('RGBA', img.size)
    draw = ImageDraw.Draw(overlay)

    # Draw semi-transparent rectangle for text area
    draw_rectangle(
        draw,
        ((112, vsize-230), (912, vsize-20)),
        color=OVERLAY_BORDER,
        width=3,
        fill=OVERLAY_COLOR
    )

    # Draw text on overlay
    textbox = ImageDraw.Draw(overlay)
    date = datetime.fromtimestamp(qso.timestamp.timestamp()).strftime("%A %B %d, %Y at %H:%M UTC")

    # Calculate positions
    y_pos = vsize - 220
    x_pos = 132

    # Main header: To/From callsigns
    textbox.text(
        (x_pos + 10, y_pos),
        f"To: {qso.call}  From: {qso.my_call}",
        font=font_call,
        fill=TEXT_COLOR
    )

    # QSO details line 1: Mode, Band, RST
    textstr = (
        f'Mode: {qso.mode} • Band: {qso.band} • '
        f'RST Send: {qso.rst_sent} • RST Received: {qso.rst_rcvd}'
    )
    textbox.text((x_pos, y_pos + 40), textstr, font=font_text, fill=TEXT_COLOR)

    # QSO details line 2: Date
    textbox.text((x_pos, y_pos + 65), f'Date: {date}', font=font_text, fill=TEXT_COLOR)

    # QSO details line 3: Rig and Power
    textbox.text(
        (x_pos, y_pos + 90),
        f'Rig: {qso.my_rig} • Power: {int(qso.tx_pwr)} Watt',
        font=font_text,
        fill=TEXT_COLOR
    )

    # QSO details line 4: Grid square
    textbox.text(
        (x_pos, y_pos + 115),
        f'Grid: {qso.my_gridsquare}',
        font=font_text,
        fill=TEXT_COLOR
    )

    # QSO details line 5: SOTA or POTA reference if present
    if qso.sota_ref:
        textbox.text(
            (x_pos, y_pos + 140),
            f'SOTA: Summit Reference ({qso.sota_ref})',
            font=font_text,
            fill=TEXT_COLOR
        )
    elif qso.pota_ref:
        textbox.text(
            (x_pos, y_pos + 140),
            f'POTA: Park Reference ({qso.pota_ref})',
            font=font_text,
            fill=TEXT_COLOR
        )

    # Footer with operator name if available
    signature = f"73 de {qso.my_call}"
    if qso.name:
        signature = f"{qso.name} - {signature}"
    textbox.text((x_pos, y_pos + 165), signature, font=font_foot, fill=TEXT_COLOR)

    # Composite overlay onto base image
    img = Image.alpha_composite(img, overlay)

    # Convert to RGB for final output
    img = img.convert("RGB")

    return img
'''


def get_default_render_code():
    """
    Get the default render code as a string.

    Returns:
        str: Python code for the render function
    """
    return DEFAULT_RENDER_CODE.strip()


def create_simple_render_code():
    """
    Get a simpler render code example for basic use cases.

    Returns:
        str: Python code for a simple render function
    """
    return '''
def render(card_template, qso):
    """
    Simple QSL card renderer - draws text directly on the card.

    Args:
        card_template: CardTemplate instance
        qso: QSO instance

    Returns:
        PIL Image
    """
    from PIL import Image, ImageDraw, ImageFont
    from datetime import datetime

    # Load the base image
    # card_template.image.name returns full path (via CardTemplateProxy in sandbox)
    img = Image.open(card_template.image.name).copy()
    draw = ImageDraw.Draw(img)

    # Try to load a system font, fall back to default if not available
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Courier.ttc", 36)
        font_medium = ImageFont.truetype("/System/Library/Fonts/Courier.ttc", 24)
    except OSError:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()

    # Draw QSO information
    y_offset = 100
    x_offset = 100
    text_color = (0, 0, 0)  # Black

    # Callsign
    draw.text(
        (x_offset, y_offset),
        f"To: {qso.call}",
        fill=text_color,
        font=font_large
    )

    # Date and time
    date_str = qso.timestamp.strftime("%Y-%m-%d %H:%M UTC")
    draw.text(
        (x_offset, y_offset + 60),
        f"Date: {date_str}",
        fill=text_color,
        font=font_medium
    )

    # Frequency and mode
    draw.text(
        (x_offset, y_offset + 100),
        f"{qso.frequency} MHz - {qso.mode}",
        fill=text_color,
        font=font_medium
    )

    # RST
    draw.text(
        (x_offset, y_offset + 140),
        f"RST: {qso.rst_sent}",
        fill=text_color,
        font=font_medium
    )

    # From callsign
    draw.text(
        (x_offset, y_offset + 180),
        f"73 de {qso.my_call}",
        fill=text_color,
        font=font_medium
    )

    return img
'''.strip()
