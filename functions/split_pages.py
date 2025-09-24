import base64
from io import BytesIO
from PIL import Image
import numpy as np

NON_WHITE_PIXEL_THRESHOLD = 225
PAGE_DIVISION = 14
MIN_PIXEL_DENSITY = 0.01


def image_to_base64(img: Image.Image) -> str:
    """Convert PIL Image to base64 string."""
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def base64_to_image(b64_string: str) -> Image.Image:
    """Convert base64 string to PIL Image."""
    return Image.open(BytesIO(base64.b64decode(b64_string)))


def calculate_vertical_density(img, width):
    img_gray = img.convert('L')
    pixels = np.array(img_gray)
    
    strip_width = width // PAGE_DIVISION
    center = width // 2
    strip_start = center - (strip_width // 2)
    strip_end = center + (strip_width // 2)
    
    center_strip = pixels[:, strip_start:strip_end]
    
    non_white = np.count_nonzero(center_strip < NON_WHITE_PIXEL_THRESHOLD)
    total_pixels = center_strip.size
    
    return non_white / total_pixels, strip_start, strip_end


def calculate_horizontal_density(img, height):
    img_gray = img.convert('L')
    pixels = np.array(img_gray)
    
    strip_height = height // PAGE_DIVISION
    center = height // 2
    strip_start = center - (strip_height // 2)
    strip_end = center + (strip_height // 2)
    
    center_strip = pixels[strip_start:strip_end, :]
    
    non_white = np.count_nonzero(center_strip < NON_WHITE_PIXEL_THRESHOLD)
    total_pixels = center_strip.size
    
    return non_white / total_pixels, strip_start, strip_end


def split_base64_png(img_b64: str):
    """
    Split a base64 PNG image into two pages if needed.
    
    Args:
        img_b64 (str): Base64 encoded PNG image
    
    Returns:
        dict with keys:
          - status: "success" / "skipped"
          - message: str
          - images: list of base64 strings (1 if no split, 2 if split success)
    """
    img = base64_to_image(img_b64)
    width, height = img.size

    density, strip_start, strip_end = calculate_vertical_density(img, width)

    if density < MIN_PIXEL_DENSITY:
        split_axis = "vertical"
    else:
        h_density, _, _ = calculate_horizontal_density(img, height)
        split_axis = "horizontal" if h_density < MIN_PIXEL_DENSITY else None

    if split_axis == "vertical":
        left_box = (0, 0, width // 2, height)
        right_box = (width // 2, 0, width, height)
        left_b64 = image_to_base64(img.crop(left_box))
        right_b64 = image_to_base64(img.crop(right_box))
        return {
            'status': 'success',
            'message': 'Vertical split successful',
            'images': [left_b64, right_b64]
        }

    elif split_axis == "horizontal":
        top_box = (0, 0, width, height // 2)
        bottom_box = (0, height // 2, width, height)
        top_b64 = image_to_base64(img.crop(top_box))
        bottom_b64 = image_to_base64(img.crop(bottom_box))
        return {
            'status': 'success',
            'message': 'Horizontal split successful',
            'images': [top_b64, bottom_b64]
        }

    else:
        return {
            'status': 'success',
            'message': 'No split performed',
            'images': [img_b64]
        }

