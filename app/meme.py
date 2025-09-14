from PIL import Image, ImageDraw, ImageFont

def make_meme(img: Image.Image, upper_text: str = "", lower_text: str = "") -> Image.Image:
    """
    Creates an Imgur-style meme from a Pillow image with upper and lower text.
    Text is white, bold, centered, with a black outline.
    Text automatically scales down if too long to fit horizontally.
    """
    # Work on a copy of the image
    image = img.convert("RGB").copy()
    draw = ImageDraw.Draw(image)

    def get_optimal_font_size(text: str, max_width: int, initial_font_size: int) -> tuple[ImageFont.FreeTypeFont, int]:
        """
        Find the optimal font size that fits the text within the given width.
        Returns the font object and the final font size.
        """
        current_font_size = initial_font_size
        min_font_size = 12  # Minimum readable font size
        
        while current_font_size >= min_font_size:
            try:
                font = ImageFont.truetype("Impact.ttf", current_font_size)
            except:
                font = ImageFont.truetype("arial.ttf", current_font_size)
            
            # Check if text fits within max_width
            bbox = draw.textbbox((0, 0), text.upper(), font=font)
            text_width = bbox[2] - bbox[0]
            
            if text_width <= max_width:
                return font, current_font_size
            
            # Reduce font size by 5% each iteration
            current_font_size = int(current_font_size * 0.95)
        
        # If we reach here, use minimum font size
        try:
            font = ImageFont.truetype("Impact.ttf", min_font_size)
        except:
            font = ImageFont.truetype("arial.ttf", min_font_size)
        return font, min_font_size

    def draw_centered_text(text: str, y: int):
        # Uppercase for meme style
        text = text.upper()
        
        # Calculate max width (leave 10% margin on each side)
        max_text_width = int(image.width * 0.8)
        
        # Get initial font size relative to image width
        initial_font_size = int(image.width / 10)
        
        # Get optimal font and size
        font, font_size = get_optimal_font_size(text, max_text_width, initial_font_size)

        # Text size with final font
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Position (centered)
        x = (image.width - text_width) // 2

        # Outline thickness
        outline = max(2, font_size // 20)

        # Draw outline
        for dx in range(-outline, outline + 1):
            for dy in range(-outline, outline + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill="black")

        # Draw main text
        draw.text((x, y), text, font=font, fill="white")
        
        return text_height  # Return height for positioning calculations

    # Upper text
    if upper_text:
        draw_centered_text(upper_text, 10)

    # Lower text
    if lower_text:
        # Calculate position based on a standard font size for consistent spacing
        standard_font_size = int(image.width / 10)
        draw_centered_text(lower_text, image.height - standard_font_size - 10)

    return image


if __name__ == "__main__":
    # Example usage
    img = Image.open("example.jpg")  # Replace with your image path
    meme_img = make_meme(img, "Top Text", "Bottom Text")
    meme_img.show()  # Display the meme
    meme_img.save("meme_output.jpg")  # Save the meme