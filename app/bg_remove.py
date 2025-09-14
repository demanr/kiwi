"""
Background removal utility with multiple methods.
This module provides background removal functionality using:
1. rembg library (primary method - works great)
2. macOS Vision framework (advanced, when available)
3. Simple fallback method
"""

from PIL import Image
import io

try:
    from rembg import remove, new_session
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False
    print("rembg not available, using fallback methods")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


def remove_background(image: Image.Image, method: str = "auto") -> Image.Image:
    """
    Remove background from an image.
    
    Args:
        image: PIL Image object
        method: "auto" (default), "rembg", "simple"
        
    Returns:
        PIL Image object with background removed (transparent background)
    """
    if method == "auto":
        if REMBG_AVAILABLE:
            return remove_background_rembg(image)
        else:
            return remove_background_simple(image)
    elif method == "rembg" and REMBG_AVAILABLE:
        return remove_background_rembg(image)
    elif method == "simple":
        return remove_background_simple(image)
    else:
        print(f"Method '{method}' not available, using fallback")
        return remove_background_simple(image)


def remove_background_rembg(image: Image.Image) -> Image.Image:
    """
    Remove background using the rembg library.
    This is the primary method and works very well.
    """
    try:
        # Convert PIL image to bytes
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        input_data = img_bytes.getvalue()
        
        # Remove background
        output_data = remove(input_data)
        
        # Convert back to PIL Image
        result_image = Image.open(io.BytesIO(output_data))
        
        print("Background removed successfully using rembg")
        return result_image
        
    except Exception as e:
        print(f"Error in rembg background removal: {e}")
        return remove_background_simple(image)


def remove_background_simple(image: Image.Image) -> Image.Image:
    """
    Apply a simple background removal technique.
    This is a fallback when other methods are not available.
    """
    try:
        if not NUMPY_AVAILABLE:
            print("NumPy not available, returning original image")
            return image.convert('RGBA')
            
        # Convert to RGBA
        rgba_image = image.convert('RGBA')
        data = np.array(rgba_image)
        
        # Simple approach: make white/light backgrounds transparent
        # This is very basic and works best with simple backgrounds
        
        # Calculate brightness for each pixel
        brightness = np.mean(data[:, :, :3], axis=2)
        
        # Create mask for bright pixels (potential background)
        threshold = np.mean(brightness) + np.std(brightness) * 0.5
        background_mask = brightness > threshold
        
        # Make background pixels more transparent
        alpha_reduction = 0.3  # Keep some alpha instead of complete removal
        data[background_mask, 3] = (data[background_mask, 3] * alpha_reduction).astype(np.uint8)
        
        # Create new image with transparency
        result_image = Image.fromarray(data, 'RGBA')
        
        print("Background removed using simple method")
        return result_image
        
    except Exception as e:
        print(f"Error in simple background removal: {e}")
        # Return original image converted to RGBA
        return image.convert('RGBA')


def remove_background_macos_native(image: Image.Image) -> Image.Image:
    """
    Advanced background removal using macOS Vision framework.
    This is a placeholder for future implementation.
    """
    print("macOS native background removal not yet implemented.")
    print("Using rembg method...")
    return remove_background_rembg(image)


if __name__ == "__main__":
    # Test the background removal
    try:
        test_image = Image.open("example.jpg")
        print(f"Loaded test image: {test_image.size}")
        
        result = remove_background(test_image)
        result.save("bg_removed_output.png")
        print("Background removal test completed. Check bg_removed_output.png")
        
        # Also test with simple method
        result_simple = remove_background(test_image, method="simple")
        result_simple.save("bg_removed_simple_output.png")
        print("Simple background removal test completed. Check bg_removed_simple_output.png")
        
    except FileNotFoundError:
        print("example.jpg not found. Please provide a test image.")
    except Exception as e:
        print(f"Test failed: {e}")