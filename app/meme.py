from PIL import Image, ImageDraw, ImageFont

def make_meme(img: Image.Image, upper_text: str = "", lower_text: str = "") -> Image.Image:
    """
    Creates an Imgur-style meme from a Pillow image with upper and lower text.
    Text is white, bold, centered, with a black outline.
    """
    # Work on a copy of the image
    image = img.convert("RGB").copy()
    draw = ImageDraw.Draw(image)

    # Pick a font size relative to image width
    font_size = int(image.width / 10)
    try:
        font = ImageFont.truetype("Impact.ttf", font_size)  # Classic meme font
    except:
        font = ImageFont.truetype("arial.ttf", font_size)   # Fallback

    def draw_centered_text(text: str, y: int):
        # Uppercase for meme style
        text = text.upper()

        # Text size
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

    # Upper text
    if upper_text:
        draw_centered_text(upper_text, 10)

    # Lower text
    if lower_text:
        draw_centered_text(lower_text, image.height - font_size - 10)

    return image


if __name__ == "__main__":
    # Example usage
    img = Image.open("example.jpg")  # Replace with your image path
    meme_img = make_meme(img, "Top Text", "Bottom Text")
    meme_img.show()  # Display the meme
    meme_img.save("meme_output.jpg")  # Save the meme